import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

def main():

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    engine.load("./Programa_general/qml/main.qml")

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()