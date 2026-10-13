"""Worker genérico en segundo plano basado en QRunnable/QThreadPool con cancelación cooperativa."""

from __future__ import annotations

import threading
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from backend.core.utils import CancelledOperationError, translate_exception_es


class CancelToken:
    """Token de cancelación cooperativa seguro entre hilos."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Solicita la cancelación de la tarea en curso."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Indica si se ha solicitado cancelar."""
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Lanza CancelledOperationError si la tarea fue cancelada."""
        if self._event.is_set():
            raise CancelledOperationError("Operación cancelada por el usuario.")


class WorkerSignals(QObject):
    """Señales emitidas por un TaskWorker hacia el hilo principal (UI)."""

    progress = Signal(int, str)      # (porcentaje 0-100, mensaje de estado)
    log = Signal(str, str)           # (mensaje, nivel: info/success/warning/error)
    finished = Signal(object)        # resultado de la tarea
    cancelled = Signal(str)          # mensaje de cancelación
    error = Signal(str, str)         # (mensaje_usuario_es, detalle_tecnico_sanitizado)


class TaskWorker(QRunnable):
    """
    Ejecuta cualquier función de negocio en el QThreadPool global sin bloquear la interfaz.

    La función objetivo recibe como argumentos con nombre opcionales `progress_callback`,
    `log_callback` y `cancel_token` si los acepta, o bien el contexto a través de kwargs.
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.cancel_token = CancelToken()

    def cancel(self) -> None:
        """Solicita la cancelación cooperativa del worker."""
        self.cancel_token.cancel()

    def _emit_progress(self, percent: int, message: str = "") -> None:
        clamped = max(0, min(100, int(percent)))
        self.signals.progress.emit(clamped, str(message))

    def _emit_log(self, message: str, level: str = "info") -> None:
        self.signals.log.emit(str(message), str(level))

    @Slot()
    def run(self) -> None:
        """Ejecución en hilo secundario."""
        try:
            self.cancel_token.raise_if_cancelled()
            result = self.fn(
                *self.args,
                progress_callback=self._emit_progress,
                log_callback=self._emit_log,
                cancel_token=self.cancel_token,
                **self.kwargs,
            )
            self.cancel_token.raise_if_cancelled()
            self.signals.finished.emit(result)
        except CancelledOperationError as exc:
            self.signals.cancelled.emit(str(exc) or "Operación cancelada por el usuario.")
        except Exception as exc:
            user_msg, tech_detail = translate_exception_es(exc)
            self.signals.error.emit(user_msg, tech_detail)


def start_worker(worker: TaskWorker) -> None:
    """Encola y ejecuta un TaskWorker en el QThreadPool global."""
    QThreadPool.globalInstance().start(worker)

