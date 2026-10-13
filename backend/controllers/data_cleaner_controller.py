"""Controlador QObject para el Limpiador de datos con reglas seleccionables y perfiles JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.logger import AppLogger
from backend.tools.data_cleaner import (
    CleaningProfileStore,
    CleaningResult,
    CleaningRulesConfig,
    execute_and_save_cleaning,
    preview_cleaning_on_file,
)


class DataCleanerController(BaseToolController):
    """Conecta DataCleanerPage.qml con la lógica de backend/tools/data_cleaner.py."""

    stateChanged = Signal()
    profilesChanged = Signal()

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._store = CleaningProfileStore()
        self._summary_cards: list[dict[str, Any]] = []
        self._rule_impacts: list[dict[str, Any]] = []
        self._preview_columns: list[str] = []
        self._preview_rows: list[list[str]] = []
        self._preview_total_rows: int = 0

    @Property("QVariantList", notify=stateChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Property("QVariantList", notify=stateChanged)
    def ruleImpacts(self) -> list[dict[str, Any]]:
        return self._rule_impacts

    @Property("QVariantList", notify=stateChanged)
    def previewColumns(self) -> list[str]:
        return self._preview_columns

    @Property("QVariantList", notify=stateChanged)
    def previewRows(self) -> list[list[str]]:
        return self._preview_rows

    @Property(int, notify=stateChanged)
    def previewTotalRows(self) -> int:
        return self._preview_total_rows

    @Property("QVariantList", notify=profilesChanged)
    def profileNames(self) -> list[str]:
        return self._store.list_names()

    def _update_from_result(self, res: CleaningResult) -> None:
        self._summary_cards = [
            {"label": "Celdas Modificadas", "value": f"{res.total_cells_changed:,}", "color": "#2d9cff", "icon": "✨"},
            {"label": "Filas con Cambios", "value": f"{res.total_rows_modified:,}", "color": "#f59e0b", "icon": "📝"},
            {"label": "Duplicadas Eliminadas", "value": f"{res.rows_removed:,}", "color": "#ef4444", "icon": "🗑️"},
            {"label": "Filas Resultantes", "value": f"{res.final_rows:,}", "color": "#10b981", "icon": "✅"},
        ]
        self._rule_impacts = [imp.to_dict() for imp in res.rule_impacts]
        self._preview_columns = res.before_after_preview.get("columns", [])
        self._preview_rows = res.before_after_preview.get("rows", [])
        self._preview_total_rows = res.before_after_preview.get("totalRows", 0)
        self.stateChanged.emit()

    @Slot(str, str, str, str, bool, "QVariantMap")
    def generatePreview(
        self,
        file_path: str,
        sheet_name: str,
        delimiter: str,
        encoding: str,
        infer_types: bool,
        rules_map: dict[str, Any],
    ) -> None:
        """Calcula en segundo plano la vista previa Antes/Después sin guardar en disco."""
        if not file_path:
            self._logger.warning("Selecciona un archivo antes de previsualizar la limpieza.")
            return
        rules = CleaningRulesConfig.from_dict(rules_map)

        def _on_done(res: CleaningResult) -> None:
            self._update_from_result(res)
            self.toastRequested.emit("Vista previa Antes/Después actualizada")

        self._run_in_background(
            preview_cleaning_on_file,
            on_success=_on_done,
            initial_message="Simulando reglas de limpieza...",
            file_path=file_path,
            rules=rules,
            sheet_name=sheet_name or None,
            delimiter=delimiter,
            encoding=encoding,
            infer_types=infer_types,
        )

    @Slot(str, str, str, str, bool, "QVariantMap", str, str, str)
    def applyAndSave(
        self,
        file_path: str,
        sheet_name: str,
        delimiter: str,
        encoding: str,
        infer_types: bool,
        rules_map: dict[str, Any],
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Aplica las reglas de limpieza y guarda el archivo resultante cuando el usuario lo confirma."""
        if not file_path:
            self._logger.warning("Selecciona un archivo antes de aplicar y guardar.")
            return
        rules = CleaningRulesConfig.from_dict(rules_map)

        def _on_done(result_tuple: tuple[CleaningResult, Path]) -> None:
            res, out_path = result_tuple
            self._update_from_result(res)
            self._set_last_output(out_path)
            self.toastRequested.emit("Archivo limpio guardado exitosamente")

        self._run_in_background(
            execute_and_save_cleaning,
            on_success=_on_done,
            initial_message="Aplicando limpieza y guardando resultado...",
            file_path=file_path,
            rules=rules,
            sheet_name=sheet_name or None,
            delimiter=delimiter,
            encoding=encoding,
            infer_types=infer_types,
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

    @Slot(str, "QVariantMap")
    def saveProfile(self, profile_name: str, rules_map: dict[str, Any]) -> None:
        """Guarda un perfil de limpieza con nombre en JSON."""
        try:
            rules = CleaningRulesConfig.from_dict(rules_map)
            self._store.save_profile(profile_name, rules)
            self.profilesChanged.emit()
            self._logger.success(f"Perfil de limpieza guardado: '{profile_name.strip()}'")
            self.toastRequested.emit(f"Perfil '{profile_name.strip()}' guardado")
        except Exception as exc:
            self._logger.error(str(exc))

    @Slot(str, result="QVariantMap")
    def loadProfile(self, profile_name: str) -> dict[str, Any]:
        """Carga un perfil de limpieza por su nombre."""
        cfg = self._store.get_profile(profile_name)
        if cfg is None:
            return {}
        self._logger.info(f"Perfil de limpieza cargado: '{profile_name}'")
        self.toastRequested.emit(f"Perfil '{profile_name}' cargado")
        return cfg.to_dict()

    @Slot(str)
    def deleteProfile(self, profile_name: str) -> None:
        """Elimina un perfil de limpieza guardado."""
        if self._store.delete_profile(profile_name):
            self.profilesChanged.emit()
            self._logger.info(f"Perfil de limpieza eliminado: '{profile_name}'")
            self.toastRequested.emit("Perfil eliminado")

