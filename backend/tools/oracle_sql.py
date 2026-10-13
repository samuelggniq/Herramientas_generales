"""Herramienta B: Cliente Oracle SQL (modo thin), variables bind, fetchmany por lotes y Favoritas JSON."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, Callable
import uuid

import oracledb
import pandas as pd

from backend.core.config import (
    DEFAULT_FAVORITES_PATH,
    OracleConfig,
    load_oracle_config,
    sanitize_sensitive_text,
)
from backend.core.file_io import export_dataframe
from backend.core.utils import (
    FriendlyAppError,
    atomic_write_json,
    read_json_safe,
)
from backend.core.worker import CancelToken

# Expresiones regulares para limpiar comentarios y literales antes de analizar SQL
_RE_SQL_COMMENTS_AND_LITERALS = re.compile(
    r"('(?:''|[^'])*')|(\"(?:\"\"|[^\"])*\")|(--[^\r\n]*)|(/\*[\s\S]*?\*/)"
)
_RE_BIND_PARAM = re.compile(r"(?<![:\w]):([A-Za-z][A-Za-z0-9_$#]*)")
_MODIFYING_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "MERGE")
_RE_MODIFYING = re.compile(
    r"\b(" + "|".join(_MODIFYING_KEYWORDS) + r")\b",
    flags=re.IGNORECASE,
)


@dataclass
class OracleQueryResult:
    """Resultado de la ejecución de una consulta en Oracle."""

    df: pd.DataFrame
    rows_fetched: int
    columns: list[str]
    execution_message: str
    output_path: str = ""


def strip_sql_comments_and_literals(sql: str) -> str:
    """Reemplaza literales de texto y comentarios por espacios para analizar el SQL de forma segura."""
    if not sql:
        return ""
    return _RE_SQL_COMMENTS_AND_LITERALS.sub(" ", sql)


def extract_bind_params(sql: str) -> list[str]:
    """
    Detecta automáticamente los parámetros nombrados de Oracle (:fecha_inicio, :codigo)
    ignorando aquellos dentro de comillas o comentarios y operadores PL/SQL (:=).
    Conserva el orden de aparición sin duplicados.
    """
    cleaned = strip_sql_comments_and_literals(sql)
    # Neutralizar asignación PL/SQL ':='
    cleaned = cleaned.replace(":=", "  ")
    found: list[str] = []
    seen: set[str] = set()
    for match in _RE_BIND_PARAM.finditer(cleaned):
        name = match.group(1)
        name_lower = name.lower()
        if name_lower not in seen:
            seen.add(name_lower)
            found.append(name)
    return found


def detect_modifying_keywords(sql: str) -> list[str]:
    """
    Detecta si el SQL contiene sentencias de modificación o estructura:
    INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER o MERGE.
    """
    cleaned = strip_sql_comments_and_literals(sql)
    found: list[str] = []
    for match in _RE_MODIFYING.finditer(cleaned):
        kw = match.group(1).upper()
        if kw not in found:
            found.append(kw)
    return found


def normalize_sql_for_execution(sql: str) -> str:
    """Limpia el punto y coma final en consultas SELECT/WITH para evitar ORA-00933 en oracledb."""
    trimmed = sql.strip()
    cleaned_no_comments = strip_sql_comments_and_literals(trimmed).strip().upper()
    if not cleaned_no_comments.startswith(("BEGIN", "DECLARE")):
        while trimmed.endswith(";"):
            trimmed = trimmed[:-1].rstrip()
    return trimmed


def convert_bind_value(param_name: str, raw_value: Any, param_type: str = "texto") -> Any:
    """
    Convierte el valor ingresado por el usuario al tipo nativo de Python para enviar como variable bind.
    Tipos soportados: 'texto', 'numero', 'fecha'.
    """
    if raw_value is None:
        return None
    s_val = str(raw_value).strip()
    if s_val == "":
        return None

    ptype = param_type.lower().strip()
    if ptype in {"numero", "número", "number"}:
        norm_num = s_val.replace(",", ".")
        try:
            if "." in norm_num:
                return float(norm_num)
            return int(norm_num)
        except ValueError as exc:
            raise FriendlyAppError(
                f"El valor '{s_val}' del parámetro ':{param_name}' no es un número válido."
            ) from exc

    if ptype in {"fecha", "date"}:
        if isinstance(raw_value, (datetime, date)):
            return raw_value
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(s_val, fmt)
                if fmt == "%Y-%m-%d %H:%M:%S":
                    return dt
                return dt.date()
            except ValueError:
                continue
        raise FriendlyAppError(
            f"El valor '{s_val}' del parámetro ':{param_name}' no tiene un formato de fecha válido "
            "(usa AAAA-MM-DD o DD/MM/AAAA)."
        )

    return str(raw_value)


def prepare_bind_variables(
    sql: str,
    params_input: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Construye el diccionario de variables bind para pasar a `cursor.execute(sql, bind_vars)`.
    Jamás concatena valores dentro del SQL.
    """
    expected_params = extract_bind_params(sql)
    if not expected_params:
        return {}

    raw_map = params_input or {}
    # Crear índice insensible a mayúsculas
    ci_map = {k.lower(): v for k, v in raw_map.items()}

    bind_dict: dict[str, Any] = {}
    for p_name in expected_params:
        entry = raw_map.get(p_name) or ci_map.get(p_name.lower()) or {}
        if isinstance(entry, dict):
            raw_val = entry.get("value", "")
            p_type = str(entry.get("type", "texto"))
        else:
            raw_val = entry
            p_type = "texto"
        bind_dict[p_name] = convert_bind_value(p_name, raw_val, p_type)

    return bind_dict


def test_oracle_connection(
    config: OracleConfig | None = None,
    connection_factory: Callable[..., Any] | None = None,
) -> tuple[bool, str]:
    """
    Prueba la conexión a Oracle en modo thin usando context manager (abre y cierra de inmediato).
    Sanea cualquier mensaje de error para nunca exponer usuario ni contraseña.
    """
    cfg = config or load_oracle_config()
    if not cfg.is_valid:
        return False, cfg.status_message_es

    conn_fn = connection_factory or oracledb.connect
    try:
        with conn_fn(
            user=cfg.user,
            password=cfg.password,
            dsn=cfg.effective_dsn,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM DUAL")
                cur.fetchone()
        return True, f"Conexión exitosa a Oracle ({cfg.display_host} / {cfg.display_service})."
    except Exception as exc:
        clean_err = sanitize_sensitive_text(str(exc), cfg)
        return False, f"No se pudo conectar a Oracle ({cfg.display_host}): {clean_err}"


test_oracle_connection.__test__ = False  # type: ignore[attr-defined]


def execute_oracle_query(
    sql: str,
    params_input: dict[str, dict[str, Any]] | None = None,
    config: OracleConfig | None = None,
    batch_size: int = 1000,
    connection_factory: Callable[..., Any] | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> OracleQueryResult:
    """
    Ejecuta una consulta SQL en Oracle en modo thin usando variables bind y descarga por lotes
    (`fetchmany`). Abre la conexión al iniciar y la cierra garantizadamente al terminar.
    """
    cfg = config or load_oracle_config()
    if not cfg.is_valid:
        raise FriendlyAppError(cfg.status_message_es)

    clean_sql = normalize_sql_for_execution(sql)
    if not clean_sql:
        raise FriendlyAppError("La consulta SQL está vacía.")

    bind_vars = prepare_bind_variables(clean_sql, params_input)

    if cancel_token:
        cancel_token.raise_if_cancelled()

    if progress_callback:
        progress_callback(10, f"Conectando a Oracle ({cfg.display_host})...")

    conn_fn = connection_factory or oracledb.connect

    try:
        with conn_fn(
            user=cfg.user,
            password=cfg.password,
            dsn=cfg.effective_dsn,
        ) as conn:
            if cancel_token:
                cancel_token.raise_if_cancelled()

            with conn.cursor() as cursor:
                cursor.arraysize = max(100, batch_size)
                if progress_callback:
                    progress_callback(25, "Ejecutando sentencia SQL en el servidor...")

                if bind_vars:
                    cursor.execute(clean_sql, bind_vars)
                else:
                    cursor.execute(clean_sql)

                # Si la consulta no devuelve filas (ej. bloque o DML confirmado)
                if cursor.description is None:
                    rowcount = getattr(cursor, "rowcount", 0) or 0
                    conn.commit()
                    msg = f"Sentencia ejecutada correctamente ({rowcount:,} fila(s) afectadas)."
                    if log_callback:
                        log_callback(msg, "success")
                    return OracleQueryResult(
                        df=pd.DataFrame(),
                        rows_fetched=0,
                        columns=[],
                        execution_message=msg,
                    )

                columns = [str(col_desc[0]) for col_desc in cursor.description]
                all_rows: list[tuple[Any, ...]] = []
                batch_num = 0

                while True:
                    if cancel_token:
                        cancel_token.raise_if_cancelled()

                    batch = cursor.fetchmany(batch_size)
                    if not batch:
                        break

                    all_rows.extend(batch)
                    batch_num += 1
                    if progress_callback:
                        pct = min(90, 30 + min(60, batch_num * 5))
                        progress_callback(pct, f"Descargando lotes: {len(all_rows):,} filas recibidas...")

                df = pd.DataFrame(all_rows, columns=columns) if all_rows else pd.DataFrame(columns=columns)
                msg = f"Consulta finalizada: {len(df):,} fila(s) descargadas ({len(columns)} columnas)."
                if log_callback:
                    log_callback(msg, "success")
                if progress_callback:
                    progress_callback(100, msg)

                return OracleQueryResult(
                    df=df,
                    rows_fetched=len(df),
                    columns=columns,
                    execution_message=msg,
                )
    except FriendlyAppError:
        raise
    except Exception as exc:
        if cancel_token and cancel_token.is_cancelled:
            cancel_token.raise_if_cancelled()
        sanitized = sanitize_sensitive_text(str(exc), cfg)
        raise FriendlyAppError(
            f"Error al ejecutar la consulta en Oracle: {sanitized}",
            sanitized,
        ) from exc


def export_oracle_result(
    df: pd.DataFrame,
    query_name: str = "consulta_oracle",
    output_format: str = "xlsx",
    output_dir: str | Path | None = None,
    csv_delimiter: str = ",",
    csv_encoding: str = "utf-8-sig",
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> Path:
    """Exporta el DataFrame resultado de Oracle a Excel (.xlsx con formato) o CSV."""
    if df is None or (df.empty and len(df.columns) == 0):
        raise FriendlyAppError("No hay resultados de consulta para exportar.")

    out_path = export_dataframe(
        df=df,
        source_path_or_name=query_name or "consulta_oracle",
        suffix_tag="oracle",
        output_format=output_format,
        output_dir=output_dir,
        csv_delimiter=csv_delimiter,
        csv_encoding=csv_encoding,
        sheet_name="Resultado SQL",
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )
    if log_callback:
        log_callback(f"Resultado SQL exportado exitosamente en: {out_path}", "success")
    return out_path


class FavoriteQueriesStore:
    """
    Persistencia segura en JSON para consultas favoritas de Oracle con tipos de parámetro
    e historial de últimos valores usados. Nunca almacena credenciales.
    """

    def __init__(self, json_path: Path | str | None = None) -> None:
        self.path = Path(json_path) if json_path is not None else DEFAULT_FAVORITES_PATH

    def _read_root(self) -> dict[str, Any]:
        raw = read_json_safe(self.path, default={})
        if not isinstance(raw, dict):
            return {"favorites": [], "global_param_history": {}}
        if "favorites" not in raw or not isinstance(raw["favorites"], list):
            raw["favorites"] = []
        if "global_param_history" not in raw or not isinstance(raw["global_param_history"], dict):
            raw["global_param_history"] = {}
        return raw

    def _write_root(self, data: dict[str, Any]) -> None:
        atomic_write_json(self.path, data)

    def list_favorites(self, search_text: str = "") -> list[dict[str, Any]]:
        root = self._read_root()
        favs: list[dict[str, Any]] = root["favorites"]
        q = search_text.strip().lower()
        if not q:
            return favs
        return [
            f
            for f in favs
            if q in str(f.get("name", "")).lower()
            or q in str(f.get("description", "")).lower()
            or q in str(f.get("sql", "")).lower()
        ]

    def get_favorite(self, fav_id: str) -> dict[str, Any] | None:
        root = self._read_root()
        for f in root["favorites"]:
            if f.get("id") == fav_id:
                return f
        return None

    def save_favorite(
        self,
        name: str,
        sql: str,
        description: str = "",
        param_types: dict[str, str] | None = None,
        fav_id: str | None = None,
    ) -> dict[str, Any]:
        clean_name = sanitize_sensitive_text(name.strip())
        clean_sql = sanitize_sensitive_text(sql.strip())
        clean_desc = sanitize_sensitive_text(description.strip())

        if not clean_name:
            raise FriendlyAppError("El nombre de la consulta favorita es obligatorio.")
        if not clean_sql:
            raise FriendlyAppError("El código SQL de la consulta favorita no puede estar vacío.")

        root = self._read_root()
        favs: list[dict[str, Any]] = root["favorites"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if fav_id:
            for item in favs:
                if item.get("id") == fav_id:
                    item["name"] = clean_name
                    item["description"] = clean_desc
                    item["sql"] = clean_sql
                    if param_types is not None:
                        item["param_types"] = dict(param_types)
                    item["updated_at"] = now_str
                    self._write_root(root)
                    return item

        new_item: dict[str, Any] = {
            "id": str(uuid.uuid4())[:8],
            "name": clean_name,
            "description": clean_desc,
            "sql": clean_sql,
            "param_types": dict(param_types or {}),
            "param_history": {},
            "updated_at": now_str,
        }
        favs.append(new_item)
        self._write_root(root)
        return new_item

    def duplicate_favorite(self, fav_id: str) -> dict[str, Any] | None:
        orig = self.get_favorite(fav_id)
        if orig is None:
            return None
        return self.save_favorite(
            name=f"{orig.get('name', 'Consulta')} (Copia)",
            sql=str(orig.get("sql", "")),
            description=str(orig.get("description", "")),
            param_types=dict(orig.get("param_types", {})),
            fav_id=None,
        )

    def delete_favorite(self, fav_id: str) -> bool:
        root = self._read_root()
        before = len(root["favorites"])
        root["favorites"] = [f for f in root["favorites"] if f.get("id") != fav_id]
        if len(root["favorites"]) < before:
            self._write_root(root)
            return True
        return False

    def record_param_usage(
        self,
        params_input: dict[str, dict[str, Any]],
        fav_id: str | None = None,
        max_history: int = 5,
    ) -> None:
        """Guarda los últimos valores utilizados por parámetro como sugerencia para futuras ejecuciones."""
        if not params_input:
            return
        root = self._read_root()
        g_hist: dict[str, list[str]] = root["global_param_history"]

        target_fav: dict[str, Any] | None = None
        if fav_id:
            for item in root["favorites"]:
                if item.get("id") == fav_id:
                    target_fav = item
                    break

        for p_name, p_meta in params_input.items():
            val_str = str(p_meta.get("value", "") if isinstance(p_meta, dict) else p_meta).strip()
            p_type = str(p_meta.get("type", "texto") if isinstance(p_meta, dict) else "texto")
            if not val_str:
                continue

            # Actualizar historial global por nombre de parámetro
            cur_list = [v for v in g_hist.get(p_name, []) if v != val_str]
            cur_list.insert(0, val_str)
            g_hist[p_name] = cur_list[:max_history]

            # Actualizar historial y tipo en la favorita activa si existe
            if target_fav is not None:
                f_hist = target_fav.setdefault("param_history", {})
                f_list = [v for v in f_hist.get(p_name, []) if v != val_str]
                f_list.insert(0, val_str)
                f_hist[p_name] = f_list[:max_history]
                f_types = target_fav.setdefault("param_types", {})
                f_types[p_name] = p_type

        self._write_root(root)

    def get_param_metadata(self, param_names: list[str], fav_id: str | None = None) -> list[dict[str, Any]]:
        """
        Devuelve la lista de descriptores de parámetros para QML con tipo recordado,
        último valor sugerido y lista de sugerencias recientes.
        """
        root = self._read_root()
        g_hist: dict[str, list[str]] = root["global_param_history"]
        fav = self.get_favorite(fav_id) if fav_id else None
        fav_types = (fav or {}).get("param_types", {})
        fav_hist = (fav or {}).get("param_history", {})

        result: list[dict[str, Any]] = []
        for name in param_names:
            suggestions = fav_hist.get(name) or g_hist.get(name) or []
            guessed_type = fav_types.get(name)
            if not guessed_type:
                n_low = name.lower()
                if "fec" in n_low or "date" in n_low or "dia" in n_low:
                    guessed_type = "fecha"
                elif "monto" in n_low or "cant" in n_low or "num" in n_low or "anio" in n_low:
                    guessed_type = "numero"
                else:
                    guessed_type = "texto"

            result.append(
                {
                    "name": name,
                    "type": guessed_type,
                    "defaultValue": suggestions[0] if suggestions else "",
                    "suggestions": suggestions,
                }
            )
        return result
