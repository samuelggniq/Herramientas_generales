"""Utilidades transversales: manejo amigable de errores, vistas previas y escritura atómica JSON."""

from __future__ import annotations

import json
import os
import tempfile
import traceback
from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.config import OracleConfig, sanitize_sensitive_text


class CancelledOperationError(Exception):
    """Excepción lanzada cuando el usuario cancela cooperativamente una tarea en segundo plano."""


class FriendlyAppError(Exception):
    """Excepción con mensaje amigable en español listo para mostrar al usuario."""

    def __init__(self, user_message: str, technical_detail: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_detail = technical_detail or user_message


def format_file_size(size_bytes: int) -> str:
    """Formatea un tamaño en bytes a una cadena legible (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    kb = size_bytes / 1024.0
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024.0
    if mb < 1024:
        return f"{mb:.2f} MB"
    gb = mb / 1024.0
    return f"{gb:.2f} GB"


def translate_exception_es(
    exc: BaseException,
    oracle_config: OracleConfig | None = None,
) -> tuple[str, str]:
    """
    Traduce una excepción técnica a una tupla (mensaje_amigable_usuario, detalle_tecnico_sanitizado).
    Nunca expone trazas crudas en el mensaje de usuario ni credenciales en el detalle técnico.
    """
    raw_tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    sanitized_tb = sanitize_sensitive_text(raw_tb, oracle_config)
    raw_msg = sanitize_sensitive_text(str(exc), oracle_config)

    if isinstance(exc, CancelledOperationError):
        return ("Operación cancelada por el usuario.", "Cancelación cooperativa solicitada.")

    if isinstance(exc, FriendlyAppError):
        detail = sanitize_sensitive_text(exc.technical_detail or raw_tb, oracle_config)
        return ( sanitize_sensitive_text(exc.user_message, oracle_config), detail )

    if isinstance(exc, PermissionError):
        return (
            "No se pudo acceder o escribir el archivo. Es muy probable que esté abierto en "
            "Microsoft Excel u otro programa, o que no tengas permisos en la carpeta. "
            "Cierra el archivo e inténtalo nuevamente.",
            sanitized_tb,
        )

    if isinstance(exc, FileNotFoundError):
        return (
            f"No se encontró el archivo o carpeta especificada ({raw_msg}). "
            "Verifica que el archivo no haya sido movido o eliminado.",
            sanitized_tb,
        )

    if isinstance(exc, pd.errors.EmptyDataError):
        return (
            "El archivo seleccionado está vacío o no contiene datos legibles.",
            sanitized_tb,
        )

    if isinstance(exc, KeyError):
        return (
            f"La columna seleccionada ({raw_msg}) no existe en el archivo.",
            sanitized_tb,
        )

    msg_lower = raw_msg.lower()
    if "worksheet" in msg_lower and ("not found" in msg_lower or "does not exist" in msg_lower):
        return (
            f"La hoja de Excel seleccionada no existe en el archivo ({raw_msg}).",
            sanitized_tb,
        )

    if "codec can't decode" in msg_lower or isinstance(exc, UnicodeDecodeError):
        return (
            "Error de codificación de caracteres al leer el archivo. "
            "Prueba cambiando manualmente la codificación a Latin-1 (CP1252) o UTF-8.",
            sanitized_tb,
        )

    if "ora-" in msg_lower or "dpy-" in msg_lower:
        return (
            f"Error al comunicar con la base de datos Oracle: {raw_msg}",
            sanitized_tb,
        )

    return (
        f"Ocurrió un problema durante el proceso: {raw_msg}",
        sanitized_tb,
    )


def dataframe_to_preview(
    df: pd.DataFrame,
    max_rows: int = 50,
) -> dict[str, Any]:
    """
    Convierte las primeras filas de un DataFrame en una estructura ligera para QML PreviewTable.
    """
    if df is None or df.empty and len(df.columns) == 0:
        return {
            "columns": [],
            "rows": [],
            "totalRows": 0,
            "totalCols": 0,
        }

    cols = [str(c) for c in df.columns]
    sample = df.head(max_rows)
    rows: list[list[str]] = []
    for _, row in sample.iterrows():
        formatted_row: list[str] = []
        for val in row:
            if pd.isna(val) or val is None:
                formatted_row.append("")
            else:
                formatted_row.append(str(val))
        rows.append(formatted_row)

    return {
        "columns": cols,
        "rows": rows,
        "totalRows": int(len(df)),
        "totalCols": int(len(cols)),
    }


def atomic_write_json(target_path: Path | str, data: Any) -> None:
    """
    Escribe un archivo JSON de forma atómica usando un archivo temporal en el mismo directorio
    y reemplazando el destino con os.replace.
    """
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem}_",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def read_json_safe(target_path: Path | str, default: Any) -> Any:
    """Lee un archivo JSON de forma segura, devolviendo `default` si no existe o es inválido."""
    path = Path(target_path)
    if not path.is_file():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

