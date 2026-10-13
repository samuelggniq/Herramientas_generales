"""Herramienta 5: Perfilado rápido de archivos con detección de tipos, estadísticas y alertas de calidad."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, Callable

import pandas as pd

from backend.core.file_io import (
    clean_file_path,
    export_dataframe,
    read_tabular_file,
    write_formatted_excel,
    build_output_path,
)
from backend.core.utils import format_file_size
from backend.core.worker import CancelToken

_RE_INT = re.compile(r"^[+-]?(?:0|[1-9]\d*)$")
_RE_DEC = re.compile(r"^[+-]?\d+[.,]\d+$")
_RE_DATE = re.compile(
    r"^(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$"
)
_BOOL_VALUES = {"true", "false", "verdadero", "falso", "si", "sí", "no"}


@dataclass
class ColumnProfile:
    """Estadísticas detalladas de una columna individual."""

    column_name: str
    detected_type: str
    null_count: int
    null_pct: float
    unique_count: int
    min_value: str
    max_value: str
    length_range: str
    top_values: str

    def to_row_list(self) -> list[str]:
        return [
            self.column_name,
            self.detected_type,
            f"{self.null_pct:.1f}% ({self.null_count})",
            str(self.unique_count),
            self.min_value,
            self.max_value,
            self.length_range,
            self.top_values,
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "Columna": self.column_name,
            "Tipo Detectado": self.detected_type,
            "% Nulos / Vacíos": round(self.null_pct, 2),
            "Cant. Nulos": self.null_count,
            "Valores Únicos": self.unique_count,
            "Mínimo": self.min_value,
            "Máximo": self.max_value,
            "Long. Mín/Máx (Texto)": self.length_range,
            "Top 3 Más Frecuentes": self.top_values,
        }


@dataclass
class FileProfileResult:
    """Resultado completo del perfilado de un archivo."""

    file_path: str
    file_name: str
    file_size_bytes: int
    file_size_formatted: str
    total_rows: int
    total_cols: int
    duplicate_rows: int
    columns_profile: list[ColumnProfile] = field(default_factory=list)
    alerts: list[dict[str, str]] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        if not self.columns_profile:
            return pd.DataFrame(
                columns=[
                    "Columna",
                    "Tipo Detectado",
                    "% Nulos / Vacíos",
                    "Cant. Nulos",
                    "Valores Únicos",
                    "Mínimo",
                    "Máximo",
                    "Long. Mín/Máx (Texto)",
                    "Top 3 Más Frecuentes",
                ]
            )
        return pd.DataFrame([c.to_dict() for c in self.columns_profile])

    def to_table_preview(self) -> dict[str, Any]:
        headers = [
            "Columna",
            "Tipo Detectado",
            "% Nulos / Vacíos",
            "Valores Únicos",
            "Mínimo",
            "Máximo",
            "Long. Mín/Máx",
            "Top 3 Frecuentes",
        ]
        rows = [c.to_row_list() for c in self.columns_profile]
        return {
            "columns": headers,
            "rows": rows,
            "totalRows": len(rows),
            "totalCols": len(headers),
        }


def _classify_scalar(val: Any) -> str:
    """Clasifica un valor escalar no nulo en: booleano, entero, decimal, fecha o texto."""
    if isinstance(val, bool):
        return "booleano"
    if isinstance(val, int):
        return "entero"
    if isinstance(val, float):
        return "decimal" if not val.is_integer() else "entero"
    if isinstance(val, (datetime, date, pd.Timestamp)):
        return "fecha"

    s = str(val).strip()
    s_lower = s.lower()
    if s_lower in _BOOL_VALUES:
        return "booleano"
    if _RE_INT.match(s):
        return "entero"
    if _RE_DEC.match(s):
        return "decimal"
    if _RE_DATE.match(s):
        return "fecha"
    return "texto"


def _determine_column_type(classifications: list[str]) -> str:
    """Determina el tipo consolidado de una columna a partir de las clasificaciones de sus celdas."""
    if not classifications:
        return "texto"

    counts: dict[str, int] = {}
    for c in classifications:
        counts[c] = counts.get(c, 0) + 1

    distinct_types = set(counts.keys())
    if len(distinct_types) == 1:
        return next(iter(distinct_types))

    # Entero + Decimal juntos se consolidan como decimal
    if distinct_types == {"entero", "decimal"}:
        return "decimal"

    return "mixto"


def profile_dataframe(
    df: pd.DataFrame,
    file_path: str | Path = "datos.csv",
    file_size_bytes: int = 0,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> FileProfileResult:
    """Calcula el perfil estadístico y alertas de calidad sobre un DataFrame ya cargado."""
    path = clean_file_path(file_path)
    total_rows = len(df)
    total_cols = len(df.columns)
    dup_rows = int(df.duplicated(keep="first").sum()) if total_rows > 0 else 0

    col_profiles: list[ColumnProfile] = []
    high_null_cols: list[str] = []
    single_val_cols: list[str] = []
    mixed_type_cols: list[str] = []

    for idx, col in enumerate(df.columns):
        if cancel_token:
            cancel_token.raise_if_cancelled()

        col_name = str(col)
        series = df[col]

        # Considerar nulos tanto NaN como cadenas vacías o de solo espacios
        is_null_mask = series.isna() | (series.astype(str).str.strip() == "")
        null_count = int(is_null_mask.sum())
        null_pct = (null_count / total_rows * 100.0) if total_rows > 0 else 0.0

        valid_series = series[~is_null_mask]
        valid_str = valid_series.astype(str).str.strip()
        unique_count = int(valid_str.nunique(dropna=True))

        # Clasificar muestra (hasta 5000 valores para velocidad y precisión)
        sample_vals = valid_series.head(5000).tolist()
        classifications = [_classify_scalar(v) for v in sample_vals]
        detected_type = _determine_column_type(classifications)

        # Calcular mínimo, máximo y longitudes
        min_val_str = "-"
        max_val_str = "-"
        len_range_str = "-"

        if not valid_str.empty:
            lengths = valid_str.map(len)
            min_len = int(lengths.min())
            max_len = int(lengths.max())
            len_range_str = f"{min_len} - {max_len} car."

            if detected_type in {"entero", "decimal"}:
                num_s = pd.to_numeric(valid_str.str.replace(",", ".", regex=False), errors="coerce").dropna()
                if not num_s.empty:
                    if detected_type == "entero":
                        min_val_str = f"{int(num_s.min()):,}"
                        max_val_str = f"{int(num_s.max()):,}"
                    else:
                        min_val_str = f"{num_s.min():,.2f}"
                        max_val_str = f"{num_s.max():,.2f}"
            else:
                min_val_str = str(valid_str.min())[:35]
                max_val_str = str(valid_str.max())[:35]

        # Top 3 valores más frecuentes
        if not valid_str.empty:
            vc = valid_str.value_counts().head(3)
            top_parts = [f"{val} ({cnt})" for val, cnt in vc.items()]
            top_str = " | ".join(top_parts)
        else:
            top_str = "(Sin valores)"

        col_profiles.append(
            ColumnProfile(
                column_name=col_name,
                detected_type=detected_type,
                null_count=null_count,
                null_pct=null_pct,
                unique_count=unique_count,
                min_value=min_val_str,
                max_value=max_val_str,
                length_range=len_range_str,
                top_values=top_str,
            )
        )

        if null_pct >= 20.0:
            high_null_cols.append(f"{col_name} ({null_pct:.1f}%)")
        if total_rows > 1 and unique_count == 1:
            single_val_cols.append(col_name)
        if detected_type == "mixto":
            mixed_type_cols.append(col_name)

        if progress_callback and total_cols > 0:
            pct = 50 + int(((idx + 1) / total_cols) * 45)
            progress_callback(min(98, pct), f"Analizando columna '{col_name}' ({idx + 1}/{total_cols})...")

    alerts: list[dict[str, str]] = []
    if high_null_cols:
        alerts.append(
            {
                "level": "warning",
                "icon": "⚠️",
                "title": "Columnas con alto porcentaje de nulos/vacíos",
                "detail": ", ".join(high_null_cols),
            }
        )
    if mixed_type_cols:
        alerts.append(
            {
                "level": "danger",
                "icon": "🔀",
                "title": "Columnas con tipos de datos mixtos",
                "detail": ", ".join(mixed_type_cols),
            }
        )
    if single_val_cols:
        alerts.append(
            {
                "level": "info",
                "icon": "📌",
                "title": "Columnas con un único valor constante",
                "detail": ", ".join(single_val_cols),
            }
        )
    if dup_rows > 0:
        alerts.append(
            {
                "level": "warning",
                "icon": "🗂️",
                "title": "Posibles filas duplicadas completas",
                "detail": f"Se detectaron {dup_rows:,} fila(s) exactamente iguales en el archivo.",
            }
        )

    return FileProfileResult(
        file_path=str(path),
        file_name=path.name,
        file_size_bytes=file_size_bytes,
        file_size_formatted=format_file_size(file_size_bytes),
        total_rows=total_rows,
        total_cols=total_cols,
        duplicate_rows=dup_rows,
        columns_profile=col_profiles,
        alerts=alerts,
    )


def profile_file(
    file_path: str | Path,
    sheet_name: str | None = None,
    delimiter: str = "auto",
    encoding: str = "auto",
    infer_types: bool = False,
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> FileProfileResult:
    """Lee un archivo y ejecuta el perfilado rápido completo."""
    path = clean_file_path(file_path)
    size_bytes = path.stat().st_size if path.is_file() else 0

    if log_callback:
        log_callback(f"Iniciando perfilado rápido de: {path.name} ({format_file_size(size_bytes)})", "info")

    def _read_prog(p: int, msg: str) -> None:
        if progress_callback:
            progress_callback(int(p * 0.5), msg)

    df = read_tabular_file(
        file_path=path,
        sheet_name=sheet_name,
        delimiter=delimiter,
        encoding=encoding,
        infer_types=infer_types,
        progress_callback=_read_prog,
        cancel_token=cancel_token,
    )

    res = profile_dataframe(
        df=df,
        file_path=path,
        file_size_bytes=size_bytes,
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )

    if log_callback:
        log_callback(
            f"Perfilado completado: {res.total_rows:,} filas, {res.total_cols} columnas, "
            f"{len(res.alerts)} alerta(s) de calidad.",
            "success",
        )
    if progress_callback:
        progress_callback(100, "Perfilado finalizado.")
    return res


def export_profile_result(
    profile: FileProfileResult,
    output_format: str = "xlsx",
    output_dir: str | Path | None = None,
    csv_delimiter: str = ",",
    csv_encoding: str = "utf-8-sig",
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> Path:
    """Exporta el reporte de perfilado a Excel (con hojas Perfil y Resumen) o CSV."""
    df_profile = profile.to_dataframe()
    fmt = output_format.lower().strip().lstrip(".")

    if fmt == "xlsx":
        df_summary = pd.DataFrame(
            [
                {"Métrica": "Archivo", "Valor": profile.file_name},
                {"Métrica": "Tamaño en disco", "Valor": profile.file_size_formatted},
                {"Métrica": "Total de Filas", "Valor": profile.total_rows},
                {"Métrica": "Total de Columnas", "Valor": profile.total_cols},
                {"Métrica": "Filas Duplicadas Exactas", "Valor": profile.duplicate_rows},
                {"Métrica": "Alertas Detectadas", "Valor": len(profile.alerts)},
            ]
        )
        out_path = build_output_path(profile.file_path, "perfil", "xlsx", output_dir)
        write_formatted_excel(
            sheets_data={"Perfil de Columnas": df_profile, "Resumen General": df_summary},
            output_path=out_path,
            progress_callback=progress_callback,
            cancel_token=cancel_token,
        )
    else:
        out_path = export_dataframe(
            df=df_profile,
            source_path_or_name=profile.file_path,
            suffix_tag="perfil",
            output_format="csv",
            output_dir=output_dir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
            progress_callback=progress_callback,
            cancel_token=cancel_token,
        )

    if log_callback:
        log_callback(f"Reporte de perfilado exportado en: {out_path}", "success")
    return out_path

