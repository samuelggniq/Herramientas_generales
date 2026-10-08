import sys
from pathlib import Path
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

def main():
    # Establecer estilo Basic para soportar la personalización visual de controles en QML
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    qml_path = Path(__file__).resolve().parent / "qml" / "main.qml"
    engine.load(str(qml_path))

    if not engine.rootObjects():
        print(f"Error: No se pudo cargar el archivo QML en {qml_path}")
        sys.exit(-1)

    root_window = engine.rootObjects()[0]

    # Conectar señales emitidas desde QML hacia la lógica en Python
    def on_convert_csv(file_path):
        print(f"[Python] Solicitud de conversión para: {file_path}")
        root_window.appendLog(f"Iniciando proceso en backend para: {file_path}", "info")
        # Aquí puedes conectar tu lógica de pandas u openpyxl:
        # e.g., df = pd.read_csv(file_path); df.to_excel(...)
        root_window.appendLog("Conversión completada con éxito.", "success")
        root_window.showToast("Conversión finalizada exitosamente")

    def on_execute_query(query):
        print(f"[Python] Solicitud de query SQL: {query}")
        root_window.appendLog(f"Ejecutando en Oracle: {query[:60]}...", "info")
        # Aquí puedes conectar tu conexión cx_Oracle u oracledb:
        root_window.appendLog("Query ejecutada. (Conexión de prueba simulada)", "success")
        root_window.showToast("Query procesada")

    root_window.convertCsvRequested.connect(on_convert_csv)
    root_window.executeQueryRequested.connect(on_execute_query)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()