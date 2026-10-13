"""Controlador QObject para el Cruce de archivos (Merge / VLOOKUP)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.logger import AppLogger
from backend.core.utils import dataframe_to_preview
from backend.tools.file_merge import MergeResult, run_file_merge


class FileMergeController(BaseToolController):
    """Conecta FileMergePage.qml con backend/tools/file_merge.py."""

    mergeChanged = Signal()

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._summary_cards: list[dict[str, Any]] = []
        self._multiplication_warning: str = ""
        self._preview_columns: list[str] = []
        self._preview_rows: list[list[str]] = []
        self._preview_total_rows: int = 0

    @Property("QVariantList", notify=mergeChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Property(str, notify=mergeChanged)
    def multiplicationWarning(self) -> str:
        return self._multiplication_warning

    @Property("QVariantList", notify=mergeChanged)
    def previewColumns(self) -> list[str]:
        return self._preview_columns

    @Property("QVariantList", notify=mergeChanged)
    def previewRows(self) -> list[list[str]]:
        return self._preview_rows

    @Property(int, notify=mergeChanged)
    def previewTotalRows(self) -> int:
        return self._preview_total_rows

    @Slot(
        str, str, "QVariantList", "QVariantList",
        str, str, "QVariantList", str, str,
        bool, bool, bool,
        str, str, str, bool,
        str, str, str, bool,
        str, str, str
    )
    def executeMerge(
        self,
        file_left: str,
        file_right: str,
        left_keys: list[str],
        right_keys: list[str],
        how: str,
        unmatched_filter: str,
        right_columns_to_bring: list[str],
        suffix_left: str,
        suffix_right: str,
        ignore_case: bool,
        ignore_spaces: bool,
        keys_as_text: bool,
        sheet_left: str,
        delimiter_left: str,
        encoding_left: str,
        infer_left: bool,
        sheet_right: str,
        delimiter_right: str,
        encoding_right: str,
        infer_right: bool,
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Ejecuta el cruce de archivos en segundo plano y exporta el resultado."""
        if not file_left or not file_right:
            self._logger.warning("Selecciona tanto el archivo izquierdo como el archivo derecho.")
            return
        if not left_keys or not right_keys:
            self._logger.warning("Agrega al menos un par de columnas clave para cruzar los archivos.")
            return

        def _on_done(res: MergeResult) -> None:
            if res.output_path:
                self._set_last_output(res.output_path)
            self._multiplication_warning = res.multiplication_warning
            self._summary_cards = [
                {"label": "Filas Coincidentes", "value": f"{res.matched_rows:,}", "color": "#10b981", "icon": "🔗"},
                {"label": "Sin Coincidencia Izq.", "value": f"{res.left_unmatched_rows:,}", "color": "#f59e0b", "icon": "⬅️"},
                {"label": "Sin Coincidencia Der.", "value": f"{res.right_unmatched_rows:,}", "color": "#f59e0b", "icon": "➡️"},
                {
                    "label": "Filas Multiplicadas (1:N)",
                    "value": f"+{res.multiplied_extra_rows:,}",
                    "color": "#ef4444" if res.multiplied_extra_rows > 0 else "#8b9fb2",
                    "icon": "⚠️",
                },
                {"label": "Total Resultante", "value": f"{res.result_total_rows:,}", "color": "#2d9cff", "icon": "📊"},
            ]
            prev = dataframe_to_preview(res.merged_df, max_rows=50)
            self._preview_columns = prev["columns"]
            self._preview_rows = prev["rows"]
            self._preview_total_rows = prev["totalRows"]
            self.mergeChanged.emit()
            self.toastRequested.emit("Cruce de archivos completado")

        self._run_in_background(
            run_file_merge,
            on_success=_on_done,
            initial_message="Cruzando archivos...",
            file_left=file_left,
            file_right=file_right,
            left_keys=left_keys,
            right_keys=right_keys,
            how=how,
            unmatched_filter=unmatched_filter,
            right_columns_to_bring=right_columns_to_bring if right_columns_to_bring else None,
            suffix_left=suffix_left,
            suffix_right=suffix_right,
            ignore_case=ignore_case,
            ignore_spaces=ignore_spaces,
            keys_as_text=keys_as_text,
            sheet_left=sheet_left or None,
            delimiter_left=delimiter_left,
            encoding_left=encoding_left,
            infer_left=infer_left,
            sheet_right=sheet_right or None,
            delimiter_right=delimiter_right,
            encoding_right=encoding_right,
            infer_right=infer_right,
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

