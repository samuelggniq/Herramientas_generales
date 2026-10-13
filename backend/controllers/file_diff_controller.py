"""Controlador QObject para el Comparador de archivos (Diff)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.logger import AppLogger
from backend.core.utils import dataframe_to_preview
from backend.tools.file_diff import DiffResult, run_file_diff


class FileDiffController(BaseToolController):
    """Conecta FileDiffPage.qml con backend/tools/file_diff.py."""

    diffChanged = Signal()

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._last_result: DiffResult | None = None
        self._summary_cards: list[dict[str, Any]] = []
        self._warnings: list[str] = []
        self._active_tab: str = "changes"  # "changes" | "modified" | "added" | "deleted"
        self._table_columns: list[str] = []
        self._table_rows: list[list[str]] = []
        self._table_total_rows: int = 0

    @Property("QVariantList", notify=diffChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Property("QVariantList", notify=diffChanged)
    def warnings(self) -> list[str]:
        return self._warnings

    @Property("QVariantList", notify=diffChanged)
    def tableColumns(self) -> list[str]:
        return self._table_columns

    @Property("QVariantList", notify=diffChanged)
    def tableRows(self) -> list[list[str]]:
        return self._table_rows

    @Property(int, notify=diffChanged)
    def tableTotalRows(self) -> int:
        return self._table_total_rows

    def _refresh_active_table(self) -> None:
        if self._last_result is None:
            self._table_columns = []
            self._table_rows = []
            self._table_total_rows = 0
            return

        if self._active_tab == "added":
            df = self._last_result.added_df
        elif self._active_tab == "deleted":
            df = self._last_result.deleted_df
        elif self._active_tab == "modified":
            df = self._last_result.modified_df
        else:
            df = self._last_result.cell_changes_df

        prev = dataframe_to_preview(df, max_rows=50)
        self._table_columns = prev["columns"]
        self._table_rows = prev["rows"]
        self._table_total_rows = prev["totalRows"]
        self.diffChanged.emit()

    @Slot(str)
    def setResultTab(self, tab_name: str) -> None:
        """Cambia la categoría mostrada en la tabla de resultados (changes/modified/added/deleted)."""
        self._active_tab = tab_name
        self._refresh_active_table()

    @Slot(
        str, str, "QVariantList", "QVariantList",
        bool, bool, float, bool,
        str, str, str, bool,
        str, str, str, bool,
        str, str, str
    )
    def runComparison(
        self,
        file_a: str,
        file_b: str,
        key_columns: list[str],
        compare_columns: list[str],
        ignore_case: bool,
        ignore_spaces: bool,
        numeric_tolerance: float,
        treat_empty_as_null: bool,
        sheet_a: str,
        delimiter_a: str,
        encoding_a: str,
        infer_a: bool,
        sheet_b: str,
        delimiter_b: str,
        encoding_b: str,
        infer_b: bool,
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Ejecuta la comparación A vs B en segundo plano y exporta el reporte."""
        if not file_a or not file_b:
            self._logger.warning("Debes seleccionar tanto el Archivo A como el Archivo B.")
            return
        if not key_columns:
            self._logger.warning("Selecciona al menos una columna clave común.")
            return

        def _on_done(res: DiffResult) -> None:
            self._last_result = res
            if res.primary_output:
                self._set_last_output(res.primary_output)
            self._warnings = res.warnings
            self._summary_cards = [
                {"label": "Nuevas (Solo en B)", "value": f"{res.added_count:,}", "color": "#10b981", "icon": "➕"},
                {"label": "Eliminadas (Solo en A)", "value": f"{res.deleted_count:,}", "color": "#ef4444", "icon": "➖"},
                {"label": "Filas Modificadas", "value": f"{res.modified_count:,}", "color": "#f59e0b", "icon": "✏️"},
                {"label": "Celdas Cambiadas", "value": f"{len(res.cell_changes_df):,}", "color": "#2d9cff", "icon": "🔎"},
                {"label": "Iguales (Sin cambio)", "value": f"{res.unchanged_count:,}", "color": "#8b9fb2", "icon": "🟰"},
            ]
            self._refresh_active_table()
            self.toastRequested.emit("Comparación de archivos finalizada")

        self._run_in_background(
            run_file_diff,
            on_success=_on_done,
            initial_message="Comparando archivos A y B...",
            file_a=file_a,
            file_b=file_b,
            key_columns=key_columns,
            compare_columns=compare_columns if compare_columns else None,
            ignore_case=ignore_case,
            ignore_spaces=ignore_spaces,
            numeric_tolerance=numeric_tolerance,
            treat_empty_as_null=treat_empty_as_null,
            sheet_a=sheet_a or None,
            delimiter_a=delimiter_a,
            encoding_a=encoding_a,
            infer_a=infer_a,
            sheet_b=sheet_b or None,
            delimiter_b=delimiter_b,
            encoding_b=encoding_b,
            infer_b=infer_b,
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

