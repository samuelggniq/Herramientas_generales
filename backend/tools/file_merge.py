"""Herramienta 2: Cruce de archivos (Merge / VLOOKUP) con emparejamiento manual de claves y alerta 1:N."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Callable

import pandas as pd

from backend.core.file_io import (
    clean_file_path,
    export_dataframe,
    read_tabular_file,
)
from backend.core.utils import FriendlyAppError
from backend.core.worker import CancelToken

_RE_SPACES = re.compile(r"\s+")


@dataclass
class MergeResult:
    """Resultado del cruce (Merge / VLOOKUP) entre archivo izquierdo y derecho."""

    merged_df: pd.DataFrame
    left_total_rows: int
    right_total_rows: int
    matched_rows: int
    left_unmatched_rows: int
    right_unmatched_rows: int
    result_total_rows: int
    multiplied_extra_rows: int = 0
    multiplication_warning: str = ""
    output_path: str = ""


def _normalize_merge_key(
    series: pd.Series,
    keys_as_text: bool,
    ignore_case: bool,
    ignore_spaces: bool,
) -> pd.Series:
    s = series.fillna("")
    if keys_as_text or ignore_case or ignore_spaces:
        s = s.astype(str)
    if ignore_spaces:
        s = s.str.strip().str.replace(_RE_SPACES, " ", regex=True)
    if ignore_case:
        s = s.str.lower()
    return s


def merge_dataframes(
    df_left: pd.DataFrame,
    df_right: pd.DataFrame,
    left_keys: list[str],
    right_keys: list[str],
    how: str = "left",  # "inner" | "left" | "right" | "outer"
    unmatched_filter: str = "all",  # "all" | "left_only" | "right_only" | "both_unmatched"
    right_columns_to_bring: list[str] | None = None,
    suffix_left: str = "_izq",
    suffix_right: str = "_der",
    ignore_case: bool = True,
    ignore_spaces: bool = True,
    keys_as_text: bool = True,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> MergeResult:
    """
    Cruza dos DataFrames emparejando `left_keys` con `right_keys` (los nombres pueden diferir).
    Detecta y alerta cuando claves duplicadas en el archivo derecho multiplican filas (1:N).
    """
    if not left_keys or not right_keys:
        raise FriendlyAppError("Debes definir al menos un par de columnas clave (izquierda y derecha).")
    if len(left_keys) != len(right_keys):
        raise FriendlyAppError(
            f"La cantidad de claves izquierdas ({len(left_keys)}) debe coincidir con las derechas ({len(right_keys)})."
        )

    cols_l = [str(c) for c in df_left.columns]
    cols_r = [str(c) for c in df_right.columns]

    for lk in left_keys:
        if lk not in cols_l:
            raise FriendlyAppError(f"La columna clave izquierda '{lk}' no existe en el archivo izquierdo.")
    for rk in right_keys:
        if rk not in cols_r:
            raise FriendlyAppError(f"La columna clave derecha '{rk}' no existe en el archivo derecho.")

    if cancel_token:
        cancel_token.raise_if_cancelled()

    if progress_callback:
        progress_callback(45, "Preparando y normalizando claves de cruce...")

    work_l = df_left.copy()
    work_l["__left_row_id__"] = range(len(work_l))

    # Seleccionar columnas del lado derecho que se traerán al resultado
    if right_columns_to_bring is not None and len(right_columns_to_bring) > 0:
        selected_r_cols = [c for c in right_columns_to_bring if c in cols_r]
    else:
        selected_r_cols = [c for c in cols_r if c not in right_keys]

    # Asegurar que las columnas clave derechas estén disponibles para construir la llave
    needed_r_cols = list(dict.fromkeys(right_keys + selected_r_cols))
    work_r = df_right[needed_r_cols].copy()

    temp_key_names: list[str] = []
    orig_rkey_Backups: list[tuple[str, str, str]] = []
    for idx, (lk, rk) in enumerate(zip(left_keys, right_keys)):
        t_col = f"__merge_key_{idx}__"
        temp_key_names.append(t_col)
        work_l[t_col] = _normalize_merge_key(work_l[lk], keys_as_text, ignore_case, ignore_spaces)
        work_r[t_col] = _normalize_merge_key(work_r[rk], keys_as_text, ignore_case, ignore_spaces)
        if lk == rk:
            r_backup = f"__rkey_orig_{idx}__"
            work_r[r_backup] = work_r[rk]
            orig_rkey_Backups.append((lk, rk, r_backup))

    # Eliminar de work_r las claves que tienen el mismo nombre que en left_keys (se unificarán con coalesce)
    # o aquellas que no fueron solicitadas explícitamente en right_columns_to_bring
    cols_to_drop_from_r = [
        rk for rk in right_keys
        if (rk in left_keys)
        or (right_columns_to_bring is not None and len(right_columns_to_bring) > 0 and rk not in right_columns_to_bring)
    ]
    for rk in cols_to_drop_from_r:
        if rk in work_r.columns:
            work_r = work_r.drop(columns=[rk])

    if cancel_token:
        cancel_token.raise_if_cancelled()

    if progress_callback:
        progress_callback(65, "Ejecutando cruce relacional...")

    eff_suffix_l = suffix_left if suffix_left else "_izq"
    eff_suffix_r = suffix_right if suffix_right else "_der"
    if eff_suffix_l == eff_suffix_r:
        eff_suffix_r = eff_suffix_r + "_2"

    full_merged = pd.merge(
        work_l,
        work_r,
        on=temp_key_names,
        how="outer",
        suffixes=(eff_suffix_l, eff_suffix_r),
        indicator="__merge_ind__",
    )

    both_mask = full_merged["__merge_ind__"] == "both"
    left_only_mask = full_merged["__merge_ind__"] == "left_only"
    right_only_mask = full_merged["__merge_ind__"] == "right_only"

    matched_rows = int(both_mask.sum())
    left_unmatched_rows = int(left_only_mask.sum())
    right_unmatched_rows = int(right_only_mask.sum())

    # Detectar multiplicación de filas 1:N causada por claves duplicadas en el archivo derecho
    distinct_left_matched = int(full_merged.loc[both_mask, "__left_row_id__"].nunique(dropna=True))
    multiplied_extra = max(0, matched_rows - distinct_left_matched)
    mult_warning = ""
    if multiplied_extra > 0:
        mult_warning = (
            f"Relación uno a muchos (1:N) detectada: claves duplicadas en el archivo derecho "
            f"multiplicaron las filas generando {multiplied_extra:,} fila(s) adicional(es) "
            f"({distinct_left_matched:,} filas izquierdas coincidentes produjeron {matched_rows:,} filas)."
        )

    # Aplicar el filtro de tipo de cruce / registros sin coincidencia
    uf = unmatched_filter.lower().strip()
    how_norm = how.lower().strip()

    if uf == "left_only":
        filtered = full_merged.loc[left_only_mask].copy()
    elif uf == "right_only":
        filtered = full_merged.loc[right_only_mask].copy()
    elif uf == "both_unmatched":
        filtered = full_merged.loc[left_only_mask | right_only_mask].copy()
    else:
        if how_norm == "inner":
            filtered = full_merged.loc[both_mask].copy()
        elif how_norm == "left":
            filtered = full_merged.loc[both_mask | left_only_mask].copy()
        elif how_norm == "right":
            filtered = full_merged.loc[both_mask | right_only_mask].copy()
        else:
            filtered = full_merged.copy()

    for lk, _rk, r_backup in orig_rkey_Backups:
        if lk in filtered.columns and r_backup in filtered.columns:
            filtered[lk] = filtered[lk].fillna(filtered[r_backup])

    # Eliminar columnas internas auxiliares
    backup_cols = [b for _, _, b in orig_rkey_Backups]
    aux_cols = [c for c in ["__left_row_id__", "__merge_ind__"] + temp_key_names + backup_cols if c in filtered.columns]
    filtered = filtered.drop(columns=aux_cols).reset_index(drop=True)

    return MergeResult(
        merged_df=filtered,
        left_total_rows=len(df_left),
        right_total_rows=len(df_right),
        matched_rows=matched_rows,
        left_unmatched_rows=left_unmatched_rows,
        right_unmatched_rows=right_unmatched_rows,
        result_total_rows=len(filtered),
        multiplied_extra_rows=multiplied_extra,
        multiplication_warning=mult_warning,
    )


def run_file_merge(
    file_left: str | Path,
    file_right: str | Path,
    left_keys: list[str],
    right_keys: list[str],
    how: str = "left",
    unmatched_filter: str = "all",
    right_columns_to_bring: list[str] | None = None,
    suffix_left: str = "_izq",
    suffix_right: str = "_der",
    ignore_case: bool = True,
    ignore_spaces: bool = True,
    keys_as_text: bool = True,
    sheet_left: str | None = None,
    delimiter_left: str = "auto",
    encoding_left: str = "auto",
    infer_left: bool = False,
    sheet_right: str | None = None,
    delimiter_right: str = "auto",
    encoding_right: str = "auto",
    infer_right: bool = False,
    output_format: str = "xlsx",
    output_dir: str | Path | None = None,
    csv_delimiter: str = ",",
    csv_encoding: str = "utf-8-sig",
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> MergeResult:
    """Lee ambos archivos, ejecuta el cruce (Merge / VLOOKUP) y exporta el resultado."""
    path_l = clean_file_path(file_left)
    path_r = clean_file_path(file_right)

    if log_callback:
        log_callback(
            f"Cruzando '{path_l.name}' ({left_keys}) con '{path_r.name}' ({right_keys}) [modo={how}]...",
            "info",
        )

    df_l = read_tabular_file(
        file_path=path_l,
        sheet_name=sheet_l if (sheet_l := sheet_left) else None,
        delimiter=delimiter_left,
        encoding=encoding_left,
        infer_types=False if keys_as_text else infer_left,
        progress_callback=lambda p, m: progress_callback(int(p * 0.2), f"[Izq] {m}") if progress_callback else None,
        cancel_token=cancel_token,
    )
    df_r = read_tabular_file(
        file_path=path_r,
        sheet_name=sheet_r if (sheet_r := sheet_right) else None,
        delimiter=delimiter_right,
        encoding=encoding_right,
        infer_types=False if keys_as_text else infer_right,
        progress_callback=lambda p, m: progress_callback(20 + int(p * 0.2), f"[Der] {m}") if progress_callback else None,
        cancel_token=cancel_token,
    )

    res = merge_dataframes(
        df_left=df_l,
        df_right=df_r,
        left_keys=left_keys,
        right_keys=right_keys,
        how=how,
        unmatched_filter=unmatched_filter,
        right_columns_to_bring=right_columns_to_bring,
        suffix_left=suffix_left,
        suffix_right=suffix_right,
        ignore_case=ignore_case,
        ignore_spaces=ignore_spaces,
        keys_as_text=keys_as_text,
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )

    if res.multiplication_warning and log_callback:
        log_callback(res.multiplication_warning, "warning")

    base_name = f"{path_l.stem}_cruce_{path_r.stem}"
    out_path = export_dataframe(
        df=res.merged_df,
        source_path_or_name=base_name,
        suffix_tag=how,
        output_format=output_format,
        output_dir=output_dir,
        csv_delimiter=csv_delimiter,
        csv_encoding=csv_encoding,
        sheet_name="Resultado Cruce",
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )
    res.output_path = str(out_path)

    if log_callback:
        log_callback(
            f"Cruce completado: Coincidentes={res.matched_rows:,}, Sin coincidencia Izq={res.left_unmatched_rows:,}, "
            f"Sin coincidencia Der={res.right_unmatched_rows:,}, Total Resultante={res.result_total_rows:,}.",
            "success",
        )
    if progress_callback:
        progress_callback(100, "Cruce de archivos finalizado.")
    return res
