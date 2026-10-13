"""Sistema centralizado de registro de actividad (Logs) con niveles, colores y sanitización."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from backend.core.config import OracleConfig, load_oracle_config, sanitize_sensitive_text


LEVEL_META: dict[str, dict[str, str]] = {
    "info": {
        "prefix": "ℹ️ INFO",
        "color": "#93c5fd",
        "text_color": "#edf2f7",
    },
    "success": {
        "prefix": "✅ ÉXITO",
        "color": "#10b981",
        "text_color": "#a7f3d0",
    },
    "warning": {
        "prefix": "⚠️ AVISO",
        "color": "#f59e0b",
        "text_color": "#fde68a",
    },
    "error": {
        "prefix": "❌ ERROR",
        "color": "#ef4444",
        "text_color": "#fecaca",
    },
}


class AppLogger(QObject):
    """Gestor de logs reactivo para QML con soporte de niveles, colores y exportación a .txt."""

    logsChanged = Signal()
    toastRequested = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[dict[str, str]] = []
        self._oracle_config: OracleConfig | None = None

    def set_oracle_config(self, config: OracleConfig) -> None:
        """Actualiza la referencia de configuración para sanitizar credenciales en logs."""
        self._oracle_config = config

    @Property("QVariantList", notify=logsChanged)
    def entries(self) -> list[dict[str, str]]:
        """Devuelve la lista de entradas estructuradas para QML."""
        return self._entries

    @Property(str, notify=logsChanged)
    def plainText(self) -> str:
        """Devuelve todos los logs en texto plano para copiar o guardar en .txt."""
        return "\n".join(item["plain"] for item in self._entries)

    @Property(str, notify=logsChanged)
    def richText(self) -> str:
        """Devuelve los logs formateados en HTML con colores por nivel para QML TextArea."""
        if not self._entries:
            return ""
        lines: list[str] = []
        for item in self._entries:
            ts = html.escape(item["timestamp"])
            prefix = html.escape(item["prefix"])
            msg = html.escape(item["message"]).replace("\n", "<br/>")
            badge_color = item["color"]
            text_color = item["text_color"]
            lines.append(
                f'<div style="margin-bottom: 4px; font-family: Consolas, \'Courier New\', monospace; font-size: 13px;">'
                f'<span style="color: #556e84;">[{ts}]</span> '
                f'<span style="color: {badge_color}; font-weight: bold;">{prefix}:</span> '
                f'<span style="color: {text_color};">{msg}</span>'
                f"</div>"
            )
        return "".join(lines)

    @Property(int, notify=logsChanged)
    def count(self) -> int:
        """Cantidad de registros actuales."""
        return len(self._entries)

    @Slot(str, str)
    def log(self, message: str, level: str = "info") -> None:
        """Registra un mensaje sanitizado con nivel ('info', 'success', 'warning', 'error')."""
        norm_level = level.lower().strip() if level else "info"
        if norm_level not in LEVEL_META:
            norm_level = "info"

        cfg = self._oracle_config or load_oracle_config()
        clean_msg = sanitize_sensitive_text(str(message), cfg)
        now_str = datetime.now().strftime("%H:%M:%S")
        meta = LEVEL_META[norm_level]
        plain_line = f"[{now_str}] {meta['prefix']}: {clean_msg}"

        self._entries.append(
            {
                "timestamp": now_str,
                "level": norm_level,
                "prefix": meta["prefix"],
                "message": clean_msg,
                "color": meta["color"],
                "text_color": meta["text_color"],
                "plain": plain_line,
            }
        )
        self.logsChanged.emit()

    def info(self, message: str) -> None:
        """Atajo para nivel info."""
        self.log(message, "info")

    def success(self, message: str) -> None:
        """Atajo para nivel success."""
        self.log(message, "success")

    def warning(self, message: str) -> None:
        """Atajo para nivel warning."""
        self.log(message, "warning")

    def error(self, message: str) -> None:
        """Atajo para nivel error."""
        self.log(message, "error")

    @Slot()
    def clear(self) -> None:
        """Vacía el registro de actividad."""
        self._entries.clear()
        self.logsChanged.emit()
        self.toastRequested.emit("Registro de actividad limpiado")

    @Slot(str, result=bool)
    def saveToFile(self, file_path: str) -> bool:
        """Guarda el contenido actual del log en un archivo .txt."""
        try:
            clean_path = self._clean_qml_path(file_path)
            if not clean_path:
                return False
            target = Path(clean_path)
            if target.suffix.lower() != ".txt":
                target = target.with_suffix(".txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            header = (
                f"=== REGISTRO DE ACTIVIDAD — TOOLBOX PRO v1.2 ===\n"
                f"Exportado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'=' * 50}\n\n"
            )
            target.write_text(header + self.plainText + "\n", encoding="utf-8")
            self.log(f"Registro guardado exitosamente en: {target}", "success")
            self.toastRequested.emit("Log guardado en archivo .txt")
            return True
        except Exception as exc:
            self.log(f"No se pudo guardar el archivo de log: {exc}", "error")
            return False

    @staticmethod
    def _clean_qml_path(raw_url: str) -> str:
        from urllib.parse import unquote

        s = str(raw_url).strip()
        if s.startswith("file:///"):
            s = s[8:]
        elif s.startswith("file://"):
            s = s[7:]
        return unquote(s)

