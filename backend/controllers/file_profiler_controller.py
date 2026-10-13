"""Controlador QObject para la herramienta de Perfilado rápido de archivos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.logger import AppLogger
from backend.tools.file_profiler import (
    FileProfileResult,
    export_profile_result,
    profile_file,
)


class FileProfilerController(BaseToolController):
    """Conecta la página de Perfilado de Archivo con backend/tools/file_profiler.py."""

    profileChanged = Signal()

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._current_profile: FileProfileResult | None = None
        self._summary_cards: list[dict[str, Any]] = []
        self._alerts: list[dict[str, str]] = []
        self._table_columns: list[str] = []
        self._table_rows: list[list[str]] = []

    @Property("QVariantList", notify=profileChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Property("QVariantList", notify=profileChanged)
    def alerts(self) -> list[dict[str, str]]:
        return self._alerts

    @Property("QVariantList", notify=profileChanged)
    def tableColumns(self) -> list[str]:
        return self._table_columns

    @Property("QVariantList", notify=profileChanged)
    def tableRows(self) -> list[list[str]]:
        return self._table_rows

    @Property(bool, notify=profileChanged)
    def hasProfile(self) -> bool:
        return self._current_profile is not None

    @Slot(str, str, str, str, bool)
    def runProfile(
        self,
        file_path: str,
        sheet_name: str = "",
        delimiter: str = "auto",
        encoding: str = "auto",
        infer_types: bool = False,
    ) -> None:
        """Se ejecuta automáticamente al cargar un archivo (en segundo plano)."""
        if not file_path or not str(file_path).strip():
            return

        def _on_done(res: FileProfileResult) -> None:
            self._current_profile = res
            self._summary_cards = [
                {"label": "Total Filas", "value": f"{res.total_rows:,}", "color": "#2d9cff", "icon": "📊"},
                {"label": "Total Columnas", "value": str(res.total_cols), "color": "#10b981", "icon": "📋"},
                {"label": "Tamaño Archivo", "value": res.file_size_formatted, "color": "#8b9fb2", "icon": "💾"},
                {
                    "label": "Duplicados Exactos",
                    "value": f"{res.duplicate_rows:,}",
                    "color": "#f59e0b" if res.duplicate_rows > 0 else "#10b981",
                    "icon": "🗂️",
                },
                {
                    "label": "Alertas de Calidad",
                    "value": str(len(res.alerts)),
                    "color": "#ef4444" if len(res.alerts) > 0 else "#10b981",
                    "icon": "⚠️",
                },
            ]
            self._alerts = res.alerts
            preview = res.to_table_preview()
            self._table_columns = preview["columns"]
            self._table_rows = preview["rows"]
            self.profileChanged.emit()
            self.toastRequested.emit("Perfilado de archivo completado")

        self._run_in_background(
            profile_file,
            on_success=_on_done,
            initial_message="Ejecutando perfilado del archivo...",
            file_path=file_path,
            sheet_name=sheet_name or None,
            delimiter=delimiter,
            encoding=encoding,
            infer_types=infer_types,
        )

    @Slot(str, str, str)
    def exportProfile(
        self,
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Exporta el perfil actual a Excel (.xlsx) o CSV."""
        if self._current_profile is None:
            self._logger.warning("Primero debes cargar y perfilar un archivo.")
            return

        def _on_exported(out_path: Path) -> None:
            self._set_last_output(out_path)
            self.toastRequested.emit("Perfil exportado exitosamente")

        self._run_in_background(
            export_profile_result,
            on_success=_on_exported,
            initial_message="Exportando reporte de perfilado...",
            profile=self._current_profile,
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

