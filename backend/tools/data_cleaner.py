"""Herramienta 3: Limpiador de datos con reglas seleccionables, vista previa antes/después y perfiles JSON."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable

import pandas as pd

from backend.core.config import DEFAULT_CLEANING_PROFILES_PATH
from backend.core.file_io import (
    clean_file_path,
    export_dataframe,
    read_tabular_file,
)
from backend.core.utils import FriendlyAppError, atomic_write_json, read_json_safe
from backend.core.worker import CancelToken

_PLACEHOLDER_EMPTIES = {"null", "n/a", "na", "-", "--", "none", "nan", "#n/a", "s/d"}
_RE_MULTI_SPACE = re.compile(r"\s{2,}")
_RE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\ufeff]")
_DATE_INPUT_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%y",
    "%m/%d/%Y",
]


@dataclass
class CleaningRulesConfig:
    """Configuración de reglas de limpieza seleccionables por el usuario."""

    target_columns: list[str] = field(default_factory=list)
    trim_spaces: bool = True
    normalize_case: bool = False
    case_mode: str = "upper"  # "upper" | "lower" | "title"
    remove_duplicates: bool = False
    duplicate_columns: list[str] = field(default_factory=list)
    unify_dates: bool = False
    date_output_format: str = "%Y-%m-%d"  # "%Y-%m-%d" | "%d/%m/%Y" | "%Y/%m/%d"
    replace_empties: bool = False
    empty_replacement_mode: str = "na"  # "custom" | "zero" | "na" | "null"
    empty_custom_value: str = ""
    treat_placeholders_as_empty: bool = True
    remove_weird_chars: bool = False
    strip_accents: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_columns": list(self.target_columns),
            "trim_spaces": self.trim_spaces,
            "normalize_case": self.normalize_case,
            "case_mode": self.case_mode,
            "remove_duplicates": self.remove_duplicates,
            "duplicate_columns": list(self.duplicate_columns),
            "unify_dates": self.unify_dates,
            "date_output_format": self.date_output_format,
            "replace_empties": self.replace_empties,
            "empty_replacement_mode": self.empty_replacement_mode,
            "empty_custom_value": self.empty_custom_value,
            "treat_placeholders_as_empty": self.treat_placeholders_as_empty,
            "remove_weird_chars": self.remove_weird_chars,
            "strip_accents": self.strip_accents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CleaningRulesConfig:
        return cls(
            target_columns=[str(c) for c in data.get("target_columns", [])],
            trim_spaces=bool(data.get("trim_spaces", True)),
            normalize_case=bool(data.get("normalize_case", False)),
            case_mode=str(data.get("case_mode", "upper")),
            remove_duplicates=bool(data.get("remove_duplicates", False)),
            duplicate_columns=[str(c) for c in data.get("duplicate_columns", [])],
            unify_dates=bool(data.get("unify_dates", False)),
            date_output_format=str(data.get("date_output_format", "%Y-%m-%d")),
            replace_empties=bool(data.get("replace_empties", False)),
            empty_replacement_mode=str(data.get("empty_replacement_mode", "na")),
            empty_custom_value=str(data.get("empty_custom_value", "")),
            treat_placeholders_as_empty=bool(data.get("treat_placeholders_as_empty", True)),
            remove_weird_chars=bool(data.get("remove_weird_chars", False)),
            strip_accents=bool(data.get("strip_accents", False)),
        )


@dataclass
class RuleImpact:
    """Impacto cuantitativo de una regla de limpieza."""

    rule_name: str
    cells_changed: int = 0
    rows_affected: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruleName": self.rule_name,
            "cellsChanged": self.cells_changed,
            "rowsAffected": self.rows_affected,
        }


@dataclass
class CleaningResult:
    """Resultado de aplicar o previsualizar las reglas de limpieza."""

    cleaned_df: pd.DataFrame
    original_rows: int
    final_rows: int
    rows_removed: int
    total_cells_changed: int
    total_rows_modified: int
    rule_impacts: list[RuleImpact] = field(default_factory=list)
    before_after_preview: dict[str, Any] = field(default_factory=dict)


def _remove_accents_preserve_enie(text: str) -> str:
    """Elimina acentos diacríticos de las vocales."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _clean_weird_string(val: Any, strip_accents: bool) -> Any:
    if pd.isna(val) or val is None:
        return val
    s = str(val)
    # Reemplazar espacio no separable (\u00a0) por espacio normal y quitar caracteres de control
    s = s.replace("\u00a0", " ")
    s = _RE_CONTROL_CHARS.sub("", s)
    if strip_accents:
        s = _remove_accents_preserve_enie(s)
    return s


def _trim_string(val: Any) -> Any:
    if pd.isna(val) or val is None:
        return val
    s = str(val).strip()
    return _RE_MULTI_SPACE.sub(" ", s)


def _normalize_case_val(val: Any, mode: str) -> Any:
    if pd.isna(val) or val is None:
        return val
    s = str(val)
    if not s:
        return s
    if mode == "upper":
        return s.upper()
    if mode == "lower":
        return s.lower()
    if mode == "title":
        return s.title()
    return s


def _try_parse_and_format_date(val: Any, out_fmt: str) -> Any:
    if pd.isna(val) or val is None:
        return val
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return val.strftime(out_fmt)

    s = str(val).strip()
    if len(s) < 6 or len(s) > 30:
        return val

    for fmt in _DATE_INPUT_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime(out_fmt)
        except ValueError:
            continue
    return val


def _apply_col_transformation(
    df: pd.DataFrame,
    cols: list[str],
    transform_fn: Callable[[Any], Any],
) -> tuple[int, set[int]]:
    """
    Aplica `transform_fn` a las columnas indicadas de `df` in-place y devuelve
    (cantidad_celdas_cambiadas, conjunto_indices_filas_afectadas).
    """
    cells_changed = 0
    rows_affected: set[int] = set()

    for col in cols:
        if col not in df.columns:
            continue
        before_series = df[col].copy()
        after_series = before_series.map(transform_fn)

        # Comparar considerando NaN == NaN como sin cambio
        both_na = before_series.isna() & after_series.isna()
        equal_vals = (before_series.astype(str) == after_series.astype(str)) & (
            before_series.isna() == after_series.isna()
        )
        changed_mask = ~(both_na | equal_vals)
        changed_count = int(changed_mask.sum())
        if changed_count > 0:
            cells_changed += changed_count
            rows_affected.update(df.index[changed_mask].tolist())
            df[col] = after_series

    return cells_changed, rows_affected


def build_before_after_preview(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    max_rows: int = 40,
) -> dict[str, Any]:
    """
    Construye una tabla de vista previa 'Antes ⇒ Después' destacando las celdas que cambiaron.
    """
    cols = [str(c) for c in df_before.columns]
    sample_indices = df_after.index[:max_rows]
    rows: list[list[str]] = []

    for idx in sample_indices:
        row_cells: list[str] = []
        has_before = idx in df_before.index
        for col in df_before.columns:
            val_after = df_after.at[idx, col] if col in df_after.columns else None
            str_after = "" if (pd.isna(val_after) or val_after is None) else str(val_after)

            if has_before:
                val_before = df_before.at[idx, col]
                str_before = "" if (pd.isna(val_before) or val_before is None) else str(val_before)
                if str_before != str_after:
                    disp_before = str_before if str_before != "" else "(vacío)"
                    disp_after = str_after if str_after != "" else "(vacío)"
                    row_cells.append(f"{disp_before} ⇒ {disp_after}")
                else:
                    row_cells.append(str_after)
            else:
                row_cells.append(str_after)
        rows.append(row_cells)

    return {
        "columns": cols,
        "rows": rows,
        "totalRows": int(len(df_after)),
        "totalCols": len(cols),
    }


def apply_cleaning_rules(
    df: pd.DataFrame,
    rules: CleaningRulesConfig,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> CleaningResult:
    """
    Ejecuta las reglas de limpieza seleccionadas sobre una copia del DataFrame,
    calculando cuántas celdas y filas modifica cada regla y generando la vista Antes/Después.
    """
    df_before = df.copy()
    work_df = df.copy()
    original_rows = len(work_df)

    all_cols = [str(c) for c in work_df.columns]
    target_cols = [c for c in rules.target_columns if c in all_cols] if rules.target_columns else all_cols

    impacts: list[RuleImpact] = []
    all_modified_rows: set[int] = set()
    total_cells_changed = 0

    if cancel_token:
        cancel_token.raise_if_cancelled()

    # 1. Quitar caracteres raros / acentos
    if rules.remove_weird_chars or rules.strip_accents:
        if progress_callback:
            progress_callback(30, "Limpiando caracteres no imprimibles / acentos...")
        c_cnt, r_set = _apply_col_transformation(
            work_df,
            target_cols,
            lambda v: _clean_weird_string(v, rules.strip_accents),
        )
        total_cells_changed += c_cnt
        all_modified_rows.update(r_set)
        impacts.append(
            RuleImpact(
                rule_name="Quitar caracteres raros" + (" y acentos" if rules.strip_accents else ""),
                cells_changed=c_cnt,
                rows_affected=len(r_set),
            )
        )

    # 2. Quitar espacios sobrantes
    if rules.trim_spaces:
        if progress_callback:
            progress_callback(45, "Eliminando espacios sobrantes...")
        c_cnt, r_set = _apply_col_transformation(work_df, target_cols, _trim_string)
        total_cells_changed += c_cnt
        all_modified_rows.update(r_set)
        impacts.append(
            RuleImpact(
                rule_name="Quitar espacios sobrantes",
                cells_changed=c_cnt,
                rows_affected=len(r_set),
            )
        )

    # 3. Reemplazar vacíos
    if rules.replace_empties:
        if progress_callback:
            progress_callback(60, "Normalizando y reemplazando valores vacíos...")
        if rules.empty_replacement_mode == "zero":
            rep_val: Any = "0"
        elif rules.empty_replacement_mode == "na":
            rep_val = "N/A"
        elif rules.empty_replacement_mode == "null":
            rep_val = None
        else:
            rep_val = rules.empty_custom_value

        def _replace_empty(v: Any) -> Any:
            if pd.isna(v) or v is None:
                return rep_val
            s = str(v).strip()
            if s == "":
                return rep_val
            if rules.treat_placeholders_as_empty and s.lower() in _PLACEHOLDER_EMPTIES:
                return rep_val
            return v

        c_cnt, r_set = _apply_col_transformation(work_df, target_cols, _replace_empty)
        total_cells_changed += c_cnt
        all_modified_rows.update(r_set)
        impacts.append(
            RuleImpact(
                rule_name="Reemplazar vacíos",
                cells_changed=c_cnt,
                rows_affected=len(r_set),
            )
        )

    # 4. Normalizar mayúsculas / minúsculas / título
    if rules.normalize_case:
        if progress_callback:
            progress_callback(72, "Normalizando uso de mayúsculas...")
        c_cnt, r_set = _apply_col_transformation(
            work_df,
            target_cols,
            lambda v: _normalize_case_val(v, rules.case_mode),
        )
        total_cells_changed += c_cnt
        all_modified_rows.update(r_set)
        impacts.append(
            RuleImpact(
                rule_name=f"Normalizar mayúsculas ({rules.case_mode})",
                cells_changed=c_cnt,
                rows_affected=len(r_set),
            )
        )

    # 5. Unificar formato de fecha
    if rules.unify_dates:
        if progress_callback:
            progress_callback(82, "Unificando formatos de fecha...")
        c_cnt, r_set = _apply_col_transformation(
            work_df,
            target_cols,
            lambda v: _try_parse_and_format_date(v, rules.date_output_format),
        )
        total_cells_changed += c_cnt
        all_modified_rows.update(r_set)
        impacts.append(
            RuleImpact(
                rule_name=f"Unificar fechas ({rules.date_output_format})",
                cells_changed=c_cnt,
                rows_affected=len(r_set),
            )
        )

    # 6. Eliminar filas duplicadas
    rows_removed = 0
    if rules.remove_duplicates:
        if progress_callback:
            progress_callback(90, "Eliminando filas duplicadas...")
        dedup_cols = [c for c in rules.duplicate_columns if c in all_cols]
        if not dedup_cols and rules.target_columns:
            dedup_cols = target_cols
        subset_arg = dedup_cols if dedup_cols else None
        before_len = len(work_df)
        work_df = work_df.drop_duplicates(subset=subset_arg, keep="first")
        rows_removed = before_len - len(work_df)
        impacts.append(
            RuleImpact(
                rule_name="Eliminar filas duplicadas",
                cells_changed=rows_removed * len(all_cols),
                rows_affected=rows_removed,
            )
        )

    preview = build_before_after_preview(df_before, work_df, max_rows=45)
    work_df = work_df.reset_index(drop=True)

    return CleaningResult(
        cleaned_df=work_df,
        original_rows=original_rows,
        final_rows=len(work_df),
        rows_removed=rows_removed,
        total_cells_changed=total_cells_changed,
        total_rows_modified=len(all_modified_rows),
        rule_impacts=impacts,
        before_after_preview=preview,
    )


def preview_cleaning_on_file(
    file_path: str | Path,
    rules: CleaningRulesConfig,
    sheet_name: str | None = None,
    delimiter: str = "auto",
    encoding: str = "auto",
    infer_types: bool = False,
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> CleaningResult:
    """Lee el archivo y calcula la vista previa 'Antes / Después' y el resumen de impacto sin escribir a disco."""
    df = read_tabular_file(
        file_path=file_path,
        sheet_name=sheet_name,
        delimiter=delimiter,
        encoding=encoding,
        infer_types=infer_types,
        progress_callback=lambda p, m: progress_callback(int(p * 0.25), m) if progress_callback else None,
        cancel_token=cancel_token,
    )
    res = apply_cleaning_rules(
        df=df,
        rules=rules,
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )
    if log_callback:
        log_callback(
            f"Vista previa de limpieza generada: {res.total_cells_changed:,} celdas cambiarían en "
            f"{res.total_rows_modified:,} filas ({res.rows_removed:,} duplicadas eliminadas).",
            "info",
        )
    if progress_callback:
        progress_callback(100, "Vista previa lista.")
    return res


def execute_and_save_cleaning(
    file_path: str | Path,
    rules: CleaningRulesConfig,
    sheet_name: str | None = None,
    delimiter: str = "auto",
    encoding: str = "auto",
    infer_types: bool = False,
    output_format: str = "xlsx",
    output_dir: str | Path | None = None,
    csv_delimiter: str = ",",
    csv_encoding: str = "utf-8-sig",
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> tuple[CleaningResult, Path]:
    """Aplica las reglas de limpieza y guarda el archivo resultante en el formato elegido."""
    res = preview_cleaning_on_file(
        file_path=file_path,
        rules=rules,
        sheet_name=sheet_name,
        delimiter=delimiter,
        encoding=encoding,
        infer_types=infer_types,
        progress_callback=progress_callback,
        log_callback=None,
        cancel_token=cancel_token,
    )
    out_path = export_dataframe(
        df=res.cleaned_df,
        source_path_or_name=file_path,
        suffix_tag="limpio",
        output_format=output_format,
        output_dir=output_dir,
        csv_delimiter=csv_delimiter,
        csv_encoding=csv_encoding,
        sheet_name="Datos Limpios",
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )
    if log_callback:
        log_callback(
            f"Limpieza aplicada y guardada en '{out_path.name}' "
            f"({res.total_cells_changed:,} celdas limpiadas, {res.final_rows:,} filas resultantes).",
            "success",
        )
    return res, out_path


class CleaningProfileStore:
    """Almacén persistente en JSON para guardar y cargar perfiles de reglas de limpieza."""

    def __init__(self, json_path: Path | str | None = None) -> None:
        self.path = Path(json_path) if json_path is not None else DEFAULT_CLEANING_PROFILES_PATH

    def load_all(self) -> dict[str, dict[str, Any]]:
        data = read_json_safe(self.path, default={})
        return data if isinstance(data, dict) else {}

    def list_names(self) -> list[str]:
        return sorted(self.load_all().keys())

    def save_profile(self, name: str, rules: CleaningRulesConfig) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise FriendlyAppError("El nombre del perfil no puede estar vacío.")
        profiles = self.load_all()
        profiles[clean_name] = rules.to_dict()
        atomic_write_json(self.path, profiles)

    def get_profile(self, name: str) -> CleaningRulesConfig | None:
        profiles = self.load_all()
        raw = profiles.get(name.strip())
        if not raw or not isinstance(raw, dict):
            return None
        return CleaningRulesConfig.from_dict(raw)

    def delete_profile(self, name: str) -> bool:
        profiles = self.load_all()
        clean_name = name.strip()
        if clean_name in profiles:
            del profiles[clean_name]
            atomic_write_json(self.path, profiles)
            return True
        return False

