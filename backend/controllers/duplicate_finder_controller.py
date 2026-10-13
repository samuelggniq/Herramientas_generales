"""Controlador QObject para el Detector de duplicados."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.logger import AppLogger
from backend.core.utils import dataframe_to_preview
from backend.tools.duplicate_finder import DuplicateFinderResult, run_duplicate_finder


class DuplicateFinderController(BaseToolController):
    """Conecta DuplicateFinderPage.qml con backend/tools/duplicate_finder.py."""

    resultsChanged = Signal()

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._summary_cards: list[dict[str, Any]] = []
        self._dup_columns: list[str] = []
        self._dup_rows: list[list[str]] = []
        self._dup_total_rows: int = 0

    @Property("QVariantList", notify=resultsChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Property("QVariantList", notify=resultsChanged)
    def dupColumns(self) -> list[str]:
        return self._dup_columns

    @Property("QVariantList", notify=resultsChanged)
    def dupRows(self) -> list[list[str]]:
        return self._dup_rows

    @Property(int, notify=resultsChanged)
    def dupTotalRows(self) -> int:
        return self._dup_total_rows

    @Slot(str, "QVariantList", bool, bool, str, str, str, str, bool, str, str, str)
    def analyzeAndExport(
        self,
        file_path: str,
        subset_columns: list[str],
        ignore_case: bool,
        ignore_spaces: bool,
        keep_mode: str,
        sheet_name: str = "",
        delimiter: str = "auto",
        encoding: str = "auto",
        infer_types: bool = False,
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Ejecuta el detector de duplicados y exporta el reporte en segundo plano."""
        if not file_path:
            self._logger.warning("Selecciona un archivo para buscar duplicados.")
            return

        def _on_done(res: DuplicateFinderResult) -> None:
            if res.primary_output:
                self._set_last_output(res.primary_output)
            self._summary_cards = [
                {"label": "Filas Totales", "value": f"{res.total_rows:,}", "color": "#2d9cff", "icon": "📊"},
                {
                    "label": "Grupos Duplicados",
                    "value": f"{res.duplicate_groups_count:,}",
                    "color": "#f59e0b" if res.duplicate_groups_count > 0 else "#10b981",
                    "icon": "🗂️",
                },
                {
                    "label": "Filas Duplicadas",
                    "value": f"{res.duplicate_rows_count:,}",
                    "color": "#ef4444" if res.duplicate_rows_count > 0 else "#10b981",
                    "icon": "⚠️",
                },
                {
                    "label": "Filas Sin Duplicados",
                    "value": f"{res.unique_kept_rows:,}",
                    "color": "#10b981",
                    "icon": "✅",
                },
            ]
            prev = dataframe_to_preview(res.duplicates_df, max_rows=50)
            self._dup_columns = prev["columns"]
            self._dup_rows = prev["rows"]
            self._dup_total_rows = prev["totalRows"]
            self.resultsChanged.emit()
            self.toastRequested.emit(f"Análisis terminado: {res.duplicate_groups_count} grupo(s) duplicado(s)")

        self._run_in_background(
            run_duplicate_finder,
            on_success=_on_done,
            initial_message="Buscando registros duplicados...",
            file_path=file_path,
            subset_columns=subset_columns if subset_columns else None,
            ignore_case=ignore_case,
            ignore_spaces=ignore_spaces,
            keep_mode=keep_mode,
            sheet_name=sheet_name or None,
            delimiter=delimiter,
            encoding=encoding,
            infer_types=infer_types,
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

