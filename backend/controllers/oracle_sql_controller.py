"""Controlador QObject para Oracle SQL con estado de conexión .env, parámetros bind y favoritas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.controllers.base_controller import BaseToolController
from backend.core.config import OracleConfig, load_oracle_config
from backend.core.logger import AppLogger
from backend.core.utils import dataframe_to_preview
from backend.tools.oracle_sql import (
    FavoriteQueriesStore,
    OracleQueryResult,
    detect_modifying_keywords,
    execute_oracle_query,
    export_oracle_result,
    extract_bind_params,
    test_oracle_connection,
)


class OracleSqlController(BaseToolController):
    """Conecta OracleSqlPage.qml con la lógica de backend/tools/oracle_sql.py."""

    connectionChanged = Signal()
    paramsChanged = Signal()
    favoritesChanged = Signal()
    resultsChanged = Signal()
    confirmExecutionRequested = Signal(str)  # emite lista de keywords peligrosas detectadas

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(logger, parent)
        self._config: OracleConfig = load_oracle_config()
        self._logger.set_oracle_config(self._config)
        self._store = FavoriteQueriesStore()

        self._conn_state = "disconnected" if self._config.is_valid else "missing_env"
        self._status_message = self._config.status_message_es
        self._search_filter = ""
        self._active_fav_id = ""
        self._detected_params: list[dict[str, Any]] = []

        self._last_df = None
        self._preview_columns: list[str] = []
        self._preview_rows: list[list[str]] = []
        self._preview_total_rows: int = 0
        self._summary_cards: list[dict[str, Any]] = []

    @Property(str, notify=connectionChanged)
    def connectionState(self) -> str:
        return self._conn_state

    @Property(bool, notify=connectionChanged)
    def isConfigValid(self) -> bool:
        return self._config.is_valid

    @Property(str, notify=connectionChanged)
    def displayHost(self) -> str:
        return self._config.display_host

    @Property(str, notify=connectionChanged)
    def displayService(self) -> str:
        return self._config.display_service

    @Property(str, notify=connectionChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property("QVariantList", notify=paramsChanged)
    def detectedParams(self) -> list[dict[str, Any]]:
        return self._detected_params

    @Property("QVariantList", notify=favoritesChanged)
    def favoritesList(self) -> list[dict[str, Any]]:
        return self._store.list_favorites(self._search_filter)

    @Property(str, notify=favoritesChanged)
    def activeFavoriteId(self) -> str:
        return self._active_fav_id

    @Property("QVariantList", notify=resultsChanged)
    def previewColumns(self) -> list[str]:
        return self._preview_columns

    @Property("QVariantList", notify=resultsChanged)
    def previewRows(self) -> list[list[str]]:
        return self._preview_rows

    @Property(int, notify=resultsChanged)
    def previewTotalRows(self) -> int:
        return self._preview_total_rows

    @Property("QVariantList", notify=resultsChanged)
    def summaryCards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    @Property(bool, notify=resultsChanged)
    def hasQueryResult(self) -> bool:
        return self._last_df is not None and len(self._preview_columns) > 0

    @Slot()
    def reloadConfig(self) -> None:
        """Recarga el archivo .env en caliente sin reiniciar la aplicación."""
        self._config = load_oracle_config()
        self._logger.set_oracle_config(self._config)
        self._conn_state = "disconnected" if self._config.is_valid else "missing_env"
        self._status_message = self._config.status_message_es
        self.connectionChanged.emit()
        self._logger.info(self._status_message)
        self.toastRequested.emit("Configuración .env recargada")

    @Slot()
    def testConnection(self) -> None:
        """Prueba la conexión a Oracle en segundo plano."""
        self._config = load_oracle_config()
        self._logger.set_oracle_config(self._config)
        if not self._config.is_valid:
            self._conn_state = "missing_env"
            self._status_message = self._config.status_message_es
            self.connectionChanged.emit()
            self._logger.warning(self._status_message)
            return

        self._conn_state = "testing"
        self._status_message = f"Probando conexión a {self._config.display_host}..."
        self.connectionChanged.emit()

        def _worker_test(progress_callback=None, log_callback=None, cancel_token=None):
            if progress_callback:
                progress_callback(40, "Verificando credenciales y servicio en Oracle...")
            return test_oracle_connection(self._config)

        def _on_tested(res_tuple: tuple[bool, str]) -> None:
            ok, msg = res_tuple
            self._conn_state = "connected" if ok else "error"
            self._status_message = msg
            self.connectionChanged.emit()
            if ok:
                self._logger.success(msg)
                self.toastRequested.emit("Conexión a Oracle exitosa")
            else:
                self._logger.error(msg)
                self.toastRequested.emit("Fallo al conectar a Oracle")

        self._run_in_background(
            _worker_test,
            on_success=_on_tested,
            initial_message="Probando conexión Oracle...",
        )

    @Slot(str)
    def inspectSqlParams(self, sql_text: str) -> None:
        """Analiza el SQL escrito y genera los campos de parámetros bind con sugerencias."""
        names = extract_bind_params(sql_text)
        current_by_name = {p["name"]: p for p in self._detected_params}
        meta_list = self._store.get_param_metadata(names, self._active_fav_id or None)

        merged: list[dict[str, Any]] = []
        for item in meta_list:
            name = item["name"]
            if name in current_by_name:
                # Preservar lo que el usuario ya haya escrito en la sesión actual
                existing = current_by_name[name]
                item["type"] = existing.get("type", item["type"])
                if existing.get("defaultValue", "") != "":
                    item["defaultValue"] = existing["defaultValue"]
            merged.append(item)

        self._detected_params = merged
        self.paramsChanged.emit()

    @Slot(str, "QVariantMap", bool, bool)
    def executeQuery(
        self,
        sql_text: str,
        params_map: dict[str, Any],
        read_only_guard: bool = True,
        confirmed_by_user: bool = False,
    ) -> None:
        """
        Ejecuta la consulta SQL en segundo plano con variables bind y fetchmany por lotes.
        Si `read_only_guard` está activo y el SQL contiene INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER/MERGE,
        solicita confirmación al usuario antes de ejecutar.
        """
        if not sql_text or not sql_text.strip():
            self._logger.warning("Escribe una consulta SQL antes de ejecutar.")
            return

        self._config = load_oracle_config()
        self._logger.set_oracle_config(self._config)
        if not self._config.is_valid:
            self._conn_state = "missing_env"
            self._status_message = self._config.status_message_es
            self.connectionChanged.emit()
            self._logger.error(self._status_message)
            self.toastRequested.emit("Configura el archivo .env antes de ejecutar")
            return

        if read_only_guard and not confirmed_by_user:
            mod_kws = detect_modifying_keywords(sql_text)
            if mod_kws:
                kws_str = ", ".join(mod_kws)
                self._logger.warning(
                    f"Modo Solo Lectura: se detectaron instrucciones de modificación ({kws_str}). Esperando confirmación."
                )
                self.confirmExecutionRequested.emit(kws_str)
                return

        # Guardar los valores usados en el historial de sugerencias
        self._store.record_param_usage(params_map, self._active_fav_id or None)

        def _on_done(res: OracleQueryResult) -> None:
            self._conn_state = "connected"
            self._status_message = res.execution_message
            self.connectionChanged.emit()

            self._last_df = res.df
            prev = dataframe_to_preview(res.df, max_rows=50)
            self._preview_columns = prev["columns"]
            self._preview_rows = prev["rows"]
            self._preview_total_rows = prev["totalRows"]
            self._summary_cards = [
                {"label": "Filas Descargadas", "value": f"{res.rows_fetched:,}", "color": "#10b981", "icon": "📥"},
                {"label": "Columnas", "value": str(len(res.columns)), "color": "#2d9cff", "icon": "📋"},
                {"label": "Parámetros Bind", "value": str(len(params_map)), "color": "#f59e0b", "icon": "🔒"},
            ]
            self.resultsChanged.emit()
            self.inspectSqlParams(sql_text)
            self.toastRequested.emit(f"Consulta completada ({res.rows_fetched:,} filas)")

        self._run_in_background(
            execute_oracle_query,
            on_success=_on_done,
            initial_message="Ejecutando consulta en Oracle...",
            sql=sql_text,
            params_input=params_map,
            config=self._config,
        )

    @Slot(str, str, str)
    def exportResult(
        self,
        output_format: str = "xlsx",
        csv_delimiter: str = ",",
        csv_encoding: str = "utf-8-sig",
    ) -> None:
        """Exporta el resultado descargado a Excel (.xlsx con formato) o CSV."""
        if self._last_df is None or len(self._preview_columns) == 0:
            self._logger.warning("No hay datos de consulta para exportar.")
            return

        def _on_exported(out_path: Path) -> None:
            self._set_last_output(out_path)
            self.toastRequested.emit("Resultado de Oracle exportado")

        self._run_in_background(
            export_oracle_result,
            on_success=_on_exported,
            initial_message="Exportando resultados de Oracle...",
            df=self._last_df,
            query_name="consulta_oracle",
            output_format=output_format,
            output_dir=self.outputDir,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding,
        )

    #--------------------------------------------------
    # Gestión de Consultas Favoritas
    #--------------------------------------------------
    @Slot(str)
    def setFavoritesSearch(self, text: str) -> None:
        self._search_filter = text
        self.favoritesChanged.emit()

    @Slot(str, str, str, "QVariantMap", str)
    def saveFavorite(
        self,
        name: str,
        description: str,
        sql_text: str,
        param_types: dict[str, str],
        fav_id: str = "",
    ) -> None:
        try:
            saved = self._store.save_favorite(
                name=name,
                sql=sql_text,
                description=description,
                param_types=param_types,
                fav_id=fav_id if fav_id else None,
            )
            self._active_fav_id = str(saved.get("id", ""))
            self.favoritesChanged.emit()
            self._logger.success(f"Consulta favorita guardada: '{saved.get('name')}'")
            self.toastRequested.emit("Favorita guardada")
        except Exception as exc:
            self._logger.error(str(exc))

    @Slot(str, result="QVariantMap")
    def loadFavorite(self, fav_id: str) -> dict[str, Any]:
        fav = self._store.get_favorite(fav_id)
        if not fav:
            return {}
        self._active_fav_id = fav_id
        self.favoritesChanged.emit()
        self.inspectSqlParams(str(fav.get("sql", "")))
        self._logger.info(f"Consulta favorita cargada: '{fav.get('name')}'")
        self.toastRequested.emit(f"Cargada: {fav.get('name')}")
        return fav

    @Slot(str)
    def duplicateFavorite(self, fav_id: str) -> None:
        dup = self._store.duplicate_favorite(fav_id)
        if dup:
            self._active_fav_id = str(dup.get("id", ""))
            self.favoritesChanged.emit()
            self._logger.info(f"Favorita duplicada: '{dup.get('name')}'")
            self.toastRequested.emit("Favorita duplicada")

    @Slot(str)
    def deleteFavorite(self, fav_id: str) -> None:
        if self._store.delete_favorite(fav_id):
            if self._active_fav_id == fav_id:
                self._active_fav_id = ""
            self.favoritesChanged.emit()
            self._logger.info("Consulta favorita eliminada.")
            self.toastRequested.emit("Favorita eliminada")

