"""Herramienta A: Conversión de archivos CSV/Excel individual y por lotes con formato."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from backend.core.file_io import (
    clean_file_path,
    export_dataframe,
    read_tabular_file,
)
from backend.core.utils import FriendlyAppError
from backend.core.worker import CancelToken


@dataclass
class ConversionResult:
    """Resultado del proceso de conversión individual o por lote."""

    total_files: int = 0
    converted_files: int = 0
    total_rows: int = 0
    output_paths: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def last_output(self) -> str:
        return self.output_paths[-1] if self.output_paths else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalFiles": self.total_files,
            "convertedFiles": self.converted_files,
            "totalRows": self.total_rows,
            "outputPaths": self.output_paths,
            "lastOutput": self.last_output,
            "errors": self.errors,
        }


def convert_files_batch(
    file_paths: list[str | Path],
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
) -> ConversionResult:
    """
    Convierte uno o varios archivos (lote) al formato de salida seleccionado (.xlsx con formato o .csv).
    Cada archivo de entrada genera su propio archivo de salida sin sobrescribir el original.
    """
    cleaned_paths = [clean_file_path(p) for p in file_paths if str(p).strip()]
    if not cleaned_paths:
        raise FriendlyAppError("Debes seleccionar al menos un archivo para convertir.")

    result = ConversionResult(total_files=len(cleaned_paths))
    total = len(cleaned_paths)

    for idx, src_path in enumerate(cleaned_paths):
        if cancel_token:
            cancel_token.raise_if_cancelled()

        base_pct = int((idx / total) * 100)
        span_pct = max(1, int(100 / total))

        def _sub_progress(sub_p: int, msg: str) -> None:
            if progress_callback:
                overall = min(99, base_pct + int((sub_p / 100.0) * span_pct))
                prefix = f"[{idx + 1}/{total}] " if total > 1 else ""
                progress_callback(overall, f"{prefix}{msg}")

        if log_callback:
            log_callback(f"Procesando archivo ({idx + 1}/{total}): {src_path.name}", "info")

        df = read_tabular_file(
            file_path=src_path,
            sheet_name=sheet_name if (total == 1 and sheet_name) else None,
            delimiter=delimiter,
            encoding=encoding,
            infer_types=infer_types,
            progress_callback=_sub_progress,
            cancel_token=cancel_token,
        )

        out_path = export_dataframe(
            df=df,
            source_path_or_name=src_path,
            suffix_tag="convertido",
            output_format=output_format,
            output_dir=output_dir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
            sheet_name="Datos",
            progress_callback=_sub_progress,
            cancel_token=cancel_token,
        )

        result.converted_files += 1
        result.total_rows += len(df)
        result.output_paths.append(str(out_path))

        if log_callback:
            log_callback(
                f"Convertido '{src_path.name}' -> '{out_path.name}' ({len(df):,} filas, {len(df.columns)} cols)",
                "success",
            )

    if progress_callback:
        progress_callback(100, f"Conversión completada ({result.converted_files} archivo(s)).")

    return result

