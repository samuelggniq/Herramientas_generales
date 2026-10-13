"""Controlador QObject para la herramienta de Conversión CSV a XLSX."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.logger import AppLogger
from backend.tools.csv_converter import ConversionResult, convert_files_batch


class CsvConverterController(BaseToolController):
    """Conecta la página de Conversión CSV con la lógica de backend/tools/csv_converter.py."""

    summaryChanged = Signal()

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._summary_cards: list[dict[str, Any]] = []

    @Property("QVariantList", notify=summaryChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Slot("QVariantList", str, str, str, bool, str, str, str)
    def convertFiles(
        self,
        file_paths: list[str],
        sheet_name: str = "",
        delimiter: str = "auto",
        encoding: str = "auto",
        infer_types: bool = False,
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Ejecuta la conversión individual o por lote en segundo plano."""
        if not file_paths:
            self._logger.warning("Selecciona al menos un archivo para convertir.")
            return

        def _on_done(res: ConversionResult) -> None:
            if res.last_output:
                self._set_last_output(res.last_output)
            self._summary_cards = [
                {
                    "label": "Archivos Convertidos",
                    "value": f"{res.converted_files} / {res.total_files}",
                    "color": "#10b981",
                    "icon": "📁",
                },
                {
                    "label": "Filas Totales Procesadas",
                    "value": f"{res.total_rows:,}",
                    "color": "#2d9cff",
                    "icon": "📊",
                },
                {
                    "label": "Formato Generado",
                    "value": output_format.upper(),
                    "color": "#f59e0b",
                    "icon": "💾",
                },
            ]
            self.summaryChanged.emit()
            self.toastRequested.emit(f"Conversión exitosa ({res.converted_files} archivo(s))")

        self._run_in_background(
            convert_files_batch,
            on_success=_on_done,
            initial_message="Iniciando conversión de archivos...",
            file_paths=file_paths,
            sheet_name=sheet_name or None,
            delimiter=delimiter,
            encoding=encoding,
            infer_types=infer_types,
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

