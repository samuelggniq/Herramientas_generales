"""Punto de entrada de Toolbox Pro v1.2 (Sistema Maestro de Herramientas)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from backend.controllers.csv_converter_controller import CsvConverterController
from backend.controllers.data_cleaner_controller import DataCleanerController
from backend.controllers.duplicate_finder_controller import DuplicateFinderController
from backend.controllers.file_diff_controller import FileDiffController
from backend.controllers.file_merge_controller import FileMergeController
from backend.controllers.file_profiler_controller import FileProfilerController
from backend.controllers.oracle_sql_controller import OracleSqlController
from backend.core.logger import AppLogger


def create_controllers(logger: AppLogger) -> dict[str, object]:
    """Instancia todos los controladores QObject que se exponen al contexto QML."""
    return {
        "appLogger": logger,
        "csvConverterController": CsvConverterController(logger),
        "fileProfilerController": FileProfilerController(logger),
        "dataCleanerController": DataCleanerController(logger),
        "duplicateFinderController": DuplicateFinderController(logger),
        "fileDiffController": FileDiffController(logger),
        "fileMergeController": FileMergeController(logger),
        "oracleSqlController": OracleSqlController(logger),
    }


def main() -> int:
    """Inicializa la aplicación Qt Quick, registra los controladores y carga qml/main.qml."""
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Toolbox Pro")
    app.setApplicationVersion("1.2")

    engine = QQmlApplicationEngine()

    logger = AppLogger()
    controllers = create_controllers(logger)

    root_ctx = engine.rootContext()
    for name, instance in controllers.items():
        root_ctx.setContextProperty(name, instance)

    logger.info("Sistema Maestro de Herramientas (Toolbox Pro v1.2) iniciado y listo.")

    qml_dir = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_dir))
    qml_path = qml_dir / "main.qml"
    engine.load(str(qml_path))

    if not engine.rootObjects():
        print(f"Error crítico: No se pudo cargar la interfaz QML desde {qml_path}", file=sys.stderr)
        return -1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())