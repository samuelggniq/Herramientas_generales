"""Herramienta 4: Detector de duplicados con agrupación, conteo de repeticiones y exportación separada."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Callable

import pandas as pd

from backend.core.file_io import (
    build_output_path,
    clean_file_path,
    read_tabular_file,
    write_csv_file,
    write_formatted_excel,
)
from backend.core.utils import dataframe_to_preview
from backend.core.worker import CancelToken

_RE_SPACES = re.compile(r"\s+")


@dataclass
class DuplicateFinderResult:
    """Resultado del análisis y separación de duplicados."""

    total_rows: int
    unique_kept_rows: int
    duplicate_groups_count: int
    duplicate_rows_count: int
    redundant_rows_count: int
    clean_df: pd.DataFrame
    duplicates_df: pd.DataFrame
    summary_df: pd.DataFrame
    output_paths: list[str] = field(default_factory=list)

    @property
    def primary_output(self) -> str:
        return self.output_paths[0] if self.output_paths else ""


def _normalize_key_series(
    series: pd.Series,
    ignore_case: bool,
    ignore_spaces: bool,
) -> pd.Series:
    s = series.fillna("").astype(str)
    if ignore_spaces:
        s = s.str.strip().str.replace(_RE_SPACES, " ", regex=True)
    if ignore_case:
        s = s.str.lower()
    return s


def find_duplicates_in_dataframe(
    df: pd.DataFrame,
    subset_columns: list[str] | None = None,
    ignore_case: bool = True,
    ignore_spaces: bool = True,
    keep_mode: str = "first",  # "first" | "last" | "none"
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> DuplicateFinderResult:
    """
    Detecta duplicados exactos o por combinación de columnas sin alterar el DataFrame original.
    Genera:
      - clean_df: archivo sin duplicados
      - duplicates_df: archivo solo con los duplicados + GRUPO_DUPLICADO y NUM_REPETICIONES
      - summary_df: resumen de métricas
    """
    total_rows = len(df)
    all_cols = [str(c) for c in df.columns]
    key_cols = [c for c in (subset_columns or []) if c in all_cols]
    if not key_cols:
        key_cols = all_cols

    if total_rows == 0 or not all_cols:
        empty_dup = df.copy()
        empty_dup["GRUPO_DUPLICADO"] = pd.Series(dtype=str)
        empty_dup["NUM_REPETICIONES"] = pd.Series(dtype=int)
        summary = pd.DataFrame(
            [
                {"Métrica": "Filas Totales", "Valor": 0},
                {"Métrica": "Grupos Duplicados", "Valor": 0},
                {"Métrica": "Filas Duplicadas", "Valor": 0},
                {"Métrica": "Filas Sin Duplicados", "Valor": 0},
            ]
        )
        return DuplicateFinderResult(
            total_rows=0,
            unique_kept_rows=0,
            duplicate_groups_count=0,
            duplicate_rows_count=0,
            redundant_rows_count=0,
            clean_df=df.copy(),
            duplicates_df=empty_dup,
            summary_df=summary,
        )

    if cancel_token:
        cancel_token.raise_if_cancelled()

    if progress_callback:
        progress_callback(45, "Normalizando claves de comparación...")

    # Construir DataFrame temporal de claves normalizadas
    norm_df = pd.DataFrame(index=df.index)
    for col in key_cols:
        norm_df[col] = _normalize_key_series(df[col], ignore_case=ignore_case, ignore_spaces=ignore_spaces)

    if cancel_token:
        cancel_token.raise_if_cancelled()

    if progress_callback:
        progress_callback(65, "Identificando grupos y conteos de repeticiones...")

    keep_arg: str | bool = False if keep_mode == "none" else ("last" if keep_mode == "last" else "first")

    # Máscara para el archivo sin duplicados (según keep_mode elegido)
    dup_mask_for_clean = norm_df.duplicated(subset=key_cols, keep=keep_arg)
    clean_df = df.loc[~dup_mask_for_clean].copy().reset_index(drop=True)

    # Todas las ocurrencias que forman parte de un grupo con >= 2 repeticiones
    all_dup_members_mask = norm_df.duplicated(subset=key_cols, keep=False)
    dup_indices = df.index[all_dup_members_mask]

    if len(dup_indices) > 0:
        dup_norm_sub = norm_df.loc[dup_indices]
        # Crear clave tupla por fila para agrupar y contar repeticiones
        key_tuples = list(dup_norm_sub.itertuples(index=False, name=None))
        counts_map: dict[tuple[Any, ...], int] = {}
        group_id_map: dict[tuple[Any, ...], str] = {}

        for kt in key_tuples:
            counts_map[kt] = counts_map.get(kt, 0) + 1
            if kt not in group_id_map:
                group_id_map[kt] = f"G-{len(group_id_map) + 1:04d}"

        duplicates_df = df.loc[dup_indices].copy()
        duplicates_df.insert(0, "NUM_REPETICIONES", [counts_map[kt] for kt in key_tuples])
        duplicates_df.insert(0, "GRUPO_DUPLICADO", [group_id_map[kt] for kt in key_tuples])
        duplicates_df = duplicates_df.sort_values(by=["GRUPO_DUPLICADO"]).reset_index(drop=True)
        dup_groups_count = len(group_id_map)
    else:
        duplicates_df = df.iloc[0:0].copy()
        duplicates_df.insert(0, "NUM_REPETICIONES", pd.Series(dtype=int))
        duplicates_df.insert(0, "GRUPO_DUPLICADO", pd.Series(dtype=str))
        dup_groups_count = 0

    dup_rows_count = int(all_dup_members_mask.sum())
    redundant_count = int(dup_mask_for_clean.sum())

    summary_df = pd.DataFrame(
        [
            {"Métrica": "Filas Totales Analizadas", "Valor": total_rows},
            {"Métrica": "Modo de Comparación", "Valor": "Fila Completa" if len(key_cols) == len(all_cols) else f"Por Columnas ({', '.join(key_cols)})"},
            {"Métrica": "Conservar Ocurrencia", "Valor": {"first": "Primera", "last": "Última", "none": "Ninguna"}.get(keep_mode, "Primera")},
            {"Métrica": "Grupos de Duplicados Detectados", "Valor": dup_groups_count},
            {"Métrica": "Filas Totales en Grupos Duplicados", "Valor": dup_rows_count},
            {"Métrica": "Filas Redundantes Descartadas", "Valor": redundant_count},
            {"Métrica": "Filas en Archivo Sin Duplicados", "Valor": len(clean_df)},
        ]
    )

    return DuplicateFinderResult(
        total_rows=total_rows,
        unique_kept_rows=len(clean_df),
        duplicate_groups_count=dup_groups_count,
        duplicate_rows_count=dup_rows_count,
        redundant_rows_count=redundant_count,
        clean_df=clean_df,
        duplicates_df=duplicates_df,
        summary_df=summary_df,
    )


def run_duplicate_finder(
    file_path: str | Path,
    subset_columns: list[str] | None = None,
    ignore_case: bool = True,
    ignore_spaces: bool = True,
    keep_mode: str = "first",
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
) -> DuplicateFinderResult:
    """
    Ejecuta la detección de duplicados sobre un archivo y exporta el resultado:
    - En Excel (.xlsx): un libro con hojas 'Resumen', 'Sin Duplicados' y 'Solo Duplicados'.
    - En CSV (.csv): tres archivos separados (_sin_duplicados, _solo_duplicados, _resumen).
    """
    src_path = clean_file_path(file_path)
    if log_callback:
        log_callback(f"Analizando duplicados en: {src_path.name}", "info")

    df = read_tabular_file(
        file_path=src_path,
        sheet_name=sheet_name,
        delimiter=delimiter,
        encoding=encoding,
        infer_types=infer_types,
        progress_callback=lambda p, m: progress_callback(int(p * 0.4), m) if progress_callback else None,
        cancel_token=cancel_token,
    )

    res = find_duplicates_in_dataframe(
        df=df,
        subset_columns=subset_columns,
        ignore_case=ignore_case,
        ignore_spaces=ignore_spaces,
        keep_mode=keep_mode,
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )

    fmt = output_format.lower().strip().lstrip(".")
    if fmt == "xlsx":
        out_xlsx = build_output_path(src_path, "duplicados_reporte", "xlsx", output_dir)
        write_formatted_excel(
            sheets_data={
                "Resumen": res.summary_df,
                "Sin Duplicados": res.clean_df,
                "Solo Duplicados": res.duplicates_df,
            },
            output_path=out_xlsx,
            progress_callback=progress_callback,
            cancel_token=cancel_token,
        )
        res.output_paths = [str(out_xlsx)]
    else:
        p_clean = build_output_path(src_path, "sin_duplicados", "csv", output_dir)
        p_dups = build_output_path(src_path, "solo_duplicados", "csv", output_dir)
        p_sum = build_output_path(src_path, "resumen_duplicados", "csv", output_dir)

        write_csv_file(res.clean_df, p_clean, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        write_csv_file(res.duplicates_df, p_dups, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        write_csv_file(res.summary_df, p_sum, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        res.output_paths = [str(p_dups), str(p_clean), str(p_sum)]

    if log_callback:
        log_callback(
            f"Detección completada: {res.total_rows:,} filas totales | "
            f"{res.duplicate_groups_count:,} grupos duplicados | "
            f"{res.duplicate_rows_count:,} filas en grupos duplicados. "
            f"Resultado guardado en: {Path(res.primary_output).name}",
            "success",
        )
    if progress_callback:
        progress_callback(100, "Proceso de duplicados finalizado.")
    return res

