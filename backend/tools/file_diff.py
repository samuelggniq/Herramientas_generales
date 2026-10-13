"""Herramienta 1: Comparador de archivos (Diff A vs B) con detalle celda a celda y resaltado en Excel."""

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
from backend.core.utils import FriendlyAppError
from backend.core.worker import CancelToken

_RE_SPACES = re.compile(r"\s+")


@dataclass
class DiffResult:
    """Resultado completo de la comparación entre el archivo A (original) y el archivo B (nuevo)."""

    added_df: pd.DataFrame
    deleted_df: pd.DataFrame
    modified_df: pd.DataFrame
    cell_changes_df: pd.DataFrame
    summary_df: pd.DataFrame
    unchanged_count: int
    dup_keys_a: int
    dup_keys_b: int
    warnings: list[str] = field(default_factory=list)
    modified_highlight_coords: set[tuple[int, int]] = field(default_factory=set)
    output_paths: list[str] = field(default_factory=list)

    @property
    def added_count(self) -> int:
        return len(self.added_df)

    @property
    def deleted_count(self) -> int:
        return len(self.deleted_df)

    @property
    def modified_count(self) -> int:
        return len(self.modified_df)

    @property
    def primary_output(self) -> str:
        return self.output_paths[0] if self.output_paths else ""


def _is_empty_val(val: Any, treat_empty_as_null: bool) -> bool:
    if pd.isna(val) or val is None:
        return True
    s = str(val).strip()
    if s == "":
        return True
    if treat_empty_as_null and s.lower() in {"null", "none", "nan"}:
        return True
    return False


def _normalize_str(val: Any, ignore_case: bool, ignore_spaces: bool) -> str:
    if pd.isna(val) or val is None:
        return ""
    s = str(val)
    if ignore_spaces:
        s = _RE_SPACES.sub(" ", s.strip())
    if ignore_case:
        s = s.lower()
    return s


def _cells_equal(
    val_a: Any,
    val_b: Any,
    ignore_case: bool,
    ignore_spaces: bool,
    numeric_tolerance: float,
    treat_empty_as_null: bool,
) -> bool:
    empty_a = _is_empty_val(val_a, treat_empty_as_null)
    empty_b = _is_empty_val(val_b, treat_empty_as_null)
    if empty_a and empty_b:
        return True
    if empty_a != empty_b:
        return False

    str_a = _normalize_str(val_a, ignore_case=ignore_case, ignore_spaces=ignore_spaces)
    str_b = _normalize_str(val_b, ignore_case=ignore_case, ignore_spaces=ignore_spaces)
    if str_a == str_b:
        return True

    # Comparación con tolerancia numérica si ambos son representaciones numéricas válidas
    try:
        num_a = float(str_a.replace(",", "."))
        num_b = float(str_b.replace(",", "."))
        if abs(num_a - num_b) <= max(0.0, float(numeric_tolerance)):
            return True
    except (ValueError, TypeError):
        pass

    return False


def compare_dataframes(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    key_columns: list[str],
    compare_columns: list[str] | None = None,
    ignore_case: bool = False,
    ignore_spaces: bool = True,
    numeric_tolerance: float = 0.0,
    treat_empty_as_null: bool = True,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> DiffResult:
    """
    Compara dos DataFrames (A = Original, B = Nuevo) usando `key_columns`.
    Calcula filas NUEVAS, ELIMINADAS, MODIFICADAS (con detalle celda por celda) e IGUALES.
    """
    cols_a = [str(c) for c in df_a.columns]
    cols_b = [str(c) for c in df_b.columns]

    if not key_columns:
        raise FriendlyAppError("Debes elegir al menos una columna clave para comparar los archivos.")

    for k in key_columns:
        if k not in cols_a:
            raise FriendlyAppError(f"La columna clave '{k}' no existe en el Archivo A (Original).")
        if k not in cols_b:
            raise FriendlyAppError(f"La columna clave '{k}' no existe en el Archivo B (Nuevo).")

    common_non_key = [c for c in cols_a if c in cols_b and c not in key_columns]
    if compare_columns:
        comp_cols = [c for c in compare_columns if c in common_non_key]
    else:
        comp_cols = common_non_key

    ordered_cols = key_columns + comp_cols

    # Normalizar claves para emparejamiento
    work_a = df_a.copy()
    work_b = df_b.copy()

    def _make_key_series(df_src: pd.DataFrame) -> pd.Series:
        parts = [
            df_src[k].map(lambda v: _normalize_str(v, ignore_case=ignore_case, ignore_spaces=ignore_spaces))
            for k in key_columns
        ]
        if len(parts) == 1:
            return parts[0]
        combined = parts[0]
        for p in parts[1:]:
            combined = combined + " | " + p
        return combined

    keys_a = _make_key_series(work_a)
    keys_b = _make_key_series(work_b)

    dup_a = int(keys_a.duplicated(keep="first").sum())
    dup_b = int(keys_b.duplicated(keep="first").sum())
    warnings: list[str] = []
    if dup_a > 0:
        warnings.append(
            f"El Archivo A (Original) contiene {dup_a:,} fila(s) con clave duplicada. "
            "Se utilizó la primera aparición de cada clave."
        )
    if dup_b > 0:
        warnings.append(
            f"El Archivo B (Nuevo) contiene {dup_b:,} fila(s) con clave duplicada. "
            "Se utilizó la primera aparición de cada clave."
        )

    work_a["__diff_key__"] = keys_a
    work_b["__diff_key__"] = keys_b

    dedup_a = work_a.drop_duplicates(subset=["__diff_key__"], keep="first").set_index("__diff_key__")
    dedup_b = work_b.drop_duplicates(subset=["__diff_key__"], keep="first").set_index("__diff_key__")

    set_a = set(dedup_a.index)
    set_b = set(dedup_b.index)

    only_in_b = [k for k in dedup_b.index if k not in set_a]
    only_in_a = [k for k in dedup_a.index if k not in set_b]
    in_both = [k for k in dedup_b.index if k in set_a]

    added_df = dedup_b.loc[only_in_b, [c for c in ordered_cols if c in dedup_b.columns]].reset_index(drop=True)
    deleted_df = dedup_a.loc[only_in_a, [c for c in ordered_cols if c in dedup_a.columns]].reset_index(drop=True)

    modified_rows: list[dict[str, Any]] = []
    cell_changes: list[dict[str, Any]] = []
    highlight_coords: set[tuple[int, int]] = set()
    unchanged_count = 0

    total_common = max(1, len(in_both))
    for idx, k_val in enumerate(in_both):
        if idx % 1000 == 0 and cancel_token:
            cancel_token.raise_if_cancelled()

        row_a = dedup_a.loc[k_val]
        row_b = dedup_b.loc[k_val]

        row_changed = False
        mod_row_dict: dict[str, Any] = {}
        changed_col_indices: list[int] = []

        # Poblar columnas clave
        for col_pos, k_col in enumerate(key_columns):
            mod_row_dict[k_col] = row_b[k_col]

        # Comparar cada columna seleccionada
        for offset, c_col in enumerate(comp_cols):
            col_pos = len(key_columns) + offset
            va = row_a[c_col]
            vb = row_b[c_col]
            if _cells_equal(
                va,
                vb,
                ignore_case=ignore_case,
                ignore_spaces=ignore_spaces,
                numeric_tolerance=numeric_tolerance,
                treat_empty_as_null=treat_empty_as_null,
            ):
                mod_row_dict[c_col] = vb
            else:
                row_changed = True
                str_va = "(vacío)" if _is_empty_val(va, treat_empty_as_null) else str(va)
                str_vb = "(vacío)" if _is_empty_val(vb, treat_empty_as_null) else str(vb)
                mod_row_dict[c_col] = f"{str_va} ⇒ {str_vb}"
                changed_col_indices.append(col_pos)
                cell_changes.append(
                    {
                        "Clave": str(k_val),
                        "Columna": c_col,
                        "Valor Anterior (A)": "" if _is_empty_val(va, treat_empty_as_null) else str(va),
                        "Valor Nuevo (B)": "" if _is_empty_val(vb, treat_empty_as_null) else str(vb),
                    }
                )

        if row_changed:
            mod_row_idx = len(modified_rows)
            modified_rows.append(mod_row_dict)
            for c_pos in changed_col_indices:
                highlight_coords.add((mod_row_idx, c_pos))
        else:
            unchanged_count += 1

        if progress_callback and idx % 1000 == 0:
            pct = 45 + int(((idx + 1) / total_common) * 40)
            progress_callback(min(85, pct), f"Comparando registros comunes ({idx + 1:,}/{total_common:,})...")

    modified_df = pd.DataFrame(modified_rows, columns=ordered_cols) if modified_rows else pd.DataFrame(columns=ordered_cols)
    cell_changes_df = (
        pd.DataFrame(cell_changes, columns=["Clave", "Columna", "Valor Anterior (A)", "Valor Nuevo (B)"])
        if cell_changes
        else pd.DataFrame(columns=["Clave", "Columna", "Valor Anterior (A)", "Valor Nuevo (B)"])
    )

    summary_df = pd.DataFrame(
        [
            {"Categoría": "Filas en Archivo A (Original)", "Cantidad": len(df_a)},
            {"Categoría": "Filas en Archivo B (Nuevo)", "Cantidad": len(df_b)},
            {"Categoría": "Filas NUEVAS (Solo en B)", "Cantidad": len(added_df)},
            {"Categoría": "Filas ELIMINADAS (Solo en A)", "Cantidad": len(deleted_df)},
            {"Categoría": "Filas MODIFICADAS (Misma clave, distinto valor)", "Cantidad": len(modified_df)},
            {"Categoría": "Celdas Individuales Cambiadas", "Cantidad": len(cell_changes_df)},
            {"Categoría": "Filas IGUALES (Sin cambios)", "Cantidad": unchanged_count},
            {"Categoría": "Claves Duplicadas en A", "Cantidad": dup_a},
            {"Categoría": "Claves Duplicadas en B", "Cantidad": dup_b},
        ]
    )

    return DiffResult(
        added_df=added_df,
        deleted_df=deleted_df,
        modified_df=modified_df,
        cell_changes_df=cell_changes_df,
        summary_df=summary_df,
        unchanged_count=unchanged_count,
        dup_keys_a=dup_a,
        dup_keys_b=dup_b,
        warnings=warnings,
        modified_highlight_coords=highlight_coords,
    )


def run_file_diff(
    file_a: str | Path,
    file_b: str | Path,
    key_columns: list[str],
    compare_columns: list[str] | None = None,
    ignore_case: bool = False,
    ignore_spaces: bool = True,
    numeric_tolerance: float = 0.0,
    treat_empty_as_null: bool = True,
    sheet_a: str | None = None,
    delimiter_a: str = "auto",
    encoding_a: str = "auto",
    infer_a: bool = False,
    sheet_b: str | None = None,
    delimiter_b: str = "auto",
    encoding_b: str = "auto",
    infer_b: bool = False,
    output_format: str = "xlsx",
    output_dir: str | Path | None = None,
    csv_delimiter: str = ",",
    csv_encoding: str = "utf-8-sig",
    progress_callback: Callable[[int, str], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None,
    cancel_token: CancelToken | None = None,
) -> DiffResult:
    """Lee ambos archivos, ejecuta la comparación y exporta el reporte completo."""
    path_a = clean_file_path(file_a)
    path_b = clean_file_path(file_b)

    if log_callback:
        log_callback(f"Comparando A='{path_a.name}' vs B='{path_b.name}' por clave {key_columns}...", "info")

    df_a = read_tabular_file(
        file_path=path_a,
        sheet_name=sheet_a,
        delimiter=delimiter_a,
        encoding=encoding_a,
        infer_types=infer_a,
        progress_callback=lambda p, m: progress_callback(int(p * 0.2), f"[A] {m}") if progress_callback else None,
        cancel_token=cancel_token,
    )
    df_b = read_tabular_file(
        file_path=path_b,
        sheet_name=sheet_b,
        delimiter=delimiter_b,
        encoding=encoding_b,
        infer_types=infer_b,
        progress_callback=lambda p, m: progress_callback(20 + int(p * 0.2), f"[B] {m}") if progress_callback else None,
        cancel_token=cancel_token,
    )

    res = compare_dataframes(
        df_a=df_a,
        df_b=df_b,
        key_columns=key_columns,
        compare_columns=compare_columns,
        ignore_case=ignore_case,
        ignore_spaces=ignore_spaces,
        numeric_tolerance=numeric_tolerance,
        treat_empty_as_null=treat_empty_as_null,
        progress_callback=progress_callback,
        cancel_token=cancel_token,
    )

    if log_callback:
        for w in res.warnings:
            log_callback(w, "warning")

    fmt = output_format.lower().strip().lstrip(".")
    base_name = f"{path_a.stem}_vs_{path_b.stem}"

    if fmt == "xlsx":
        out_xlsx = build_output_path(base_name, "diff", "xlsx", output_dir)
        write_formatted_excel(
            sheets_data={
                "Resumen": res.summary_df,
                "Nuevas": res.added_df,
                "Eliminadas": res.deleted_df,
                "Modificadas": res.modified_df,
                "Detalle Celdas": res.cell_changes_df,
            },
            output_path=out_xlsx,
            highlight_cells={"Modificadas": res.modified_highlight_coords},
            progress_callback=progress_callback,
            cancel_token=cancel_token,
        )
        res.output_paths = [str(out_xlsx)]
    else:
        p_sum = build_output_path(base_name, "diff_resumen", "csv", output_dir)
        p_new = build_output_path(base_name, "diff_nuevas", "csv", output_dir)
        p_del = build_output_path(base_name, "diff_eliminadas", "csv", output_dir)
        p_mod = build_output_path(base_name, "diff_modificadas", "csv", output_dir)
        p_cel = build_output_path(base_name, "diff_detalle_celdas", "csv", output_dir)

        write_csv_file(res.summary_df, p_sum, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        write_csv_file(res.added_df, p_new, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        write_csv_file(res.deleted_df, p_del, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        write_csv_file(res.modified_df, p_mod, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        write_csv_file(res.cell_changes_df, p_cel, delimiter=csv_delimiter, encoding=csv_encoding, cancel_token=cancel_token)
        res.output_paths = [str(p_mod), str(p_cel), str(p_new), str(p_del), str(p_sum)]

    if log_callback:
        log_callback(
            f"Comparación finalizada: Nuevas={res.added_count:,}, Eliminadas={res.deleted_count:,}, "
            f"Modificadas={res.modified_count:,} ({len(res.cell_changes_df):,} celdas), Iguales={res.unchanged_count:,}.",
            "success",
        )
    if progress_callback:
        progress_callback(100, "Comparación completada.")
    return res

