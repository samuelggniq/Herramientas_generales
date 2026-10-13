"""Controlador base QObject con gestión de workers, barra de progreso, cancelación y apertura de resultados."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from backend.core.config import DEFAULT_OUTPUT_DIR, ensure_output_dir
from backend.core.file_io import (
    clean_file_path,
    inspect_file_metadata,
    read_tabular_file,
)
from backend.core.logger import AppLogger
from backend.core.utils import dataframe_to_preview, translate_exception_es
from backend.core.worker import TaskWorker, start_worker


class BaseToolController(QObject):
    """Clase base para los controladores de herramientas expuestos a QML."""

    busyChanged = Signal()
    progressChanged = Signal()
    lastOutputChanged = Signal()
    outputDirChanged = Signal()
    toastRequested = Signal(str)

    def __init__(self, logger: AppLogger, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = logger
        self._is_busy = False
        self._progress_value = 0
        self._progress_message = "Listo"
        self._last_output_path = ""
        self._output_dir = str(ensure_output_dir(DEFAULT_OUTPUT_DIR))
        self._active_worker: TaskWorker | None = None

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        """Indica si hay una tarea ejecutándose en segundo plano."""
        return self._is_busy

    @Property(int, notify=progressChanged)
    def progressValue(self) -> int:
        """Valor de progreso actual (0 a 100)."""
        return self._progress_value

    @Property(str, notify=progressChanged)
    def progressMessage(self) -> str:
        """Mensaje descriptivo del estado actual del proceso."""
        return self._progress_message

    @Property(str, notify=lastOutputChanged)
    def lastOutputPath(self) -> str:
        """Ruta absoluta del último archivo generado."""
        return self._last_output_path

    @Property(str, notify=outputDirChanged)
    def outputDir(self) -> str:
        """Carpeta configurada para guardar archivos de salida."""
        return self._output_dir

    def _set_busy(self, busy: bool, initial_msg: str = "") -> None:
        self._is_busy = busy
        if busy:
            self._progress_value = 0
            self._progress_message = initial_msg or "Iniciando proceso..."
        self.busyChanged.emit()
        self.progressChanged.emit()

    def _update_progress(self, value: int, message: str) -> None:
        self._progress_value = value
        if message:
            self._progress_message = message
        self.progressChanged.emit()

    def _set_last_output(self, path: str | Path) -> None:
        self._last_output_path = str(path) if path else ""
        self.lastOutputChanged.emit()

    def _run_in_background(
        self,
        fn: Callable[..., Any],
        on_success: Callable[[Any], None] | None = None,
        initial_message: str = "Procesando...",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Lanza una función en segundo plano conectando progreso, logs, errores y cancelación."""
        if self._is_busy:
            self._logger.warning("Ya hay una operación en curso. Espera a que termine o cancélala.")
            return

        self._set_busy(True, initial_message)
        worker = TaskWorker(fn, *args, **kwargs)
        self._active_worker = worker

        worker.signals.progress.connect(self._update_progress)
        worker.signals.log.connect(self._logger.log)

        def _handle_finished(result: Any) -> None:
            self._active_worker = None
            self._update_progress(100, "Proceso completado")
            self._set_busy(False)
            if on_success is not None:
                on_success(result)

        def _handle_cancelled(msg: str) -> None:
            self._active_worker = None
            self._progress_value = 0
            self._progress_message = "Cancelado por el usuario"
            self._set_busy(False)
            self._logger.warning(msg)
            self.toastRequested.emit("Operación cancelada")

        def _handle_error(user_msg: str, tech_detail: str) -> None:
            self._active_worker = None
            self._progress_message = "Error en el proceso"
            self._set_busy(False)
            self._logger.error(user_msg)
            if tech_detail and tech_detail.strip() != user_msg.strip():
                first_line = tech_detail.strip().splitlines()[-1] if tech_detail.strip().splitlines() else ""
                if first_line and first_line != user_msg:
                    self._logger.info(f"Detalle técnico: {first_line}")
            self.toastRequested.emit("Error en la operación. Revisa el registro.")

        worker.signals.finished.connect(_handle_finished)
        worker.signals.cancelled.connect(_handle_cancelled)
        worker.signals.error.connect(_handle_error)

        start_worker(worker)

    @Slot()
    def cancelTask(self) -> None:
        """Solicita cancelar cooperativamente la tarea actual en segundo plano."""
        if self._active_worker is not None:
            self._logger.warning("Solicitando cancelación de la tarea en curso...")
            self._progress_message = "Cancelando operación..."
            self.progressChanged.emit()
            self._active_worker.cancel()

    @Slot(str)
    def setOutputDir(self, folder_url: str) -> None:
        """Actualiza la carpeta de salida para resultados."""
        clean = clean_file_path(folder_url)
        if str(clean).strip():
            ensured = ensure_output_dir(clean)
            self._output_dir = str(ensured)
            self.outputDirChanged.emit()
            self._logger.info(f"Carpeta de salida establecida: {self._output_dir}")
            self.toastRequested.emit("Carpeta de salida actualizada")

    @Slot()
    def openOutputFile(self) -> None:
        """Abre el último archivo de resultado con la aplicación predeterminada del sistema."""
        if not self._last_output_path:
            self.toastRequested.emit("No hay ningún archivo de resultado aún")
            return
        path = Path(self._last_output_path)
        if not path.exists():
            self._logger.warning(f"El archivo no existe en disco: {path}")
            return
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @Slot()
    def openOutputFolder(self) -> None:
        """Abre la carpeta donde se guardó el último resultado (o la carpeta de salida actual)."""
        target_dir = Path(self._output_dir)
        if self._last_output_path:
            p = Path(self._last_output_path)
            if p.exists():
                target_dir = p.parent if p.is_file() else p
        target_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(target_dir))  # type: ignore[attr-defined]
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    @Slot(str, result="QVariantMap")
    def inspectFile(self, file_url: str) -> dict[str, Any]:
        """Inspecciona hojas de Excel o delimitador/codificación de CSV sin bloquear."""
        try:
            meta = inspect_file_metadata(file_url)
            meta["ok"] = True
            meta["error"] = ""
            return meta
        except Exception as exc:
            user_msg, _ = translate_exception_es(exc)
            self._logger.error(user_msg)
            return {
                "ok": False,
                "error": user_msg,
                "isExcel": False,
                "isCsv": False,
                "sheets": [],
                "defaultSheet": "",
                "detectedEncoding": "",
                "detectedDelimiter": "",
            }

    @Slot(str, str, str, str, bool, result="QVariantMap")
    def loadPreview(
        self,
        file_url: str,
        sheet_name: str = "",
        delimiter: str = "auto",
        encoding: str = "auto",
        infer_types: bool = False,
    ) -> dict[str, Any]:
        """Carga una vista previa rápida (primeras 50 filas) y devuelve columnas y filas."""
        try:
            df = read_tabular_file(
                file_path=file_url,
                sheet_name=sheet_name if sheet_name else None,
                delimiter=delimiter,
                encoding=encoding,
                infer_types=infer_types,
                nrows=50,
            )
            preview = dataframe_to_preview(df, max_rows=50)
            preview["ok"] = True
            preview["error"] = ""
            return preview
        except Exception as exc:
            user_msg, _ = translate_exception_es(exc)
            self._logger.error(user_msg)
            return {
                "ok": False,
                "error": user_msg,
                "columns": [],
                "rows": [],
                "totalRows": 0,
                "totalCols": 0,
            }

