import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ContentCard {
    id: logCard

    property var logger: appLogger
    property int preferredLogHeight: 165

    Layout.fillWidth: true
    implicitHeight: preferredLogHeight

    FileDialog {
        id: saveLogDialog
        title: "Guardar registro de actividad como .txt"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Archivos de texto (*.txt)", "Todos los archivos (*.*)"]
        onAccepted: {
            if (logCard.logger) {
                logCard.logger.saveToFile(selectedFile.toString())
            }
        }
    }

    TextEdit {
        id: localClipboard
        visible: false
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "📋 Registro de Actividad (Logs)"
                color: "#edf2f7"
                font.pixelSize: 15
                font.bold: true
                Layout.fillWidth: true
            }

            ActionButton {
                isPrimary: false
                text: "Copiar Logs"
                implicitHeight: 30
                enabled: logCard.logger && logCard.logger.count > 0
                onClicked: {
                    localClipboard.text = logCard.logger.plainText
                    localClipboard.selectAll()
                    localClipboard.copy()
                    if (logCard.logger) logCard.logger.toastRequested("Logs copiados al portapapeles")
                }
            }

            ActionButton {
                isPrimary: false
                text: "Guardar log"
                implicitHeight: 30
                enabled: logCard.logger && logCard.logger.count > 0
                onClicked: saveLogDialog.open()
            }

            ActionButton {
                isPrimary: false
                text: "Limpiar"
                implicitHeight: 30
                enabled: logCard.logger && logCard.logger.count > 0
                onClicked: {
                    if (logCard.logger) logCard.logger.clear()
                }
            }
        }

        ScrollView {
            id: logScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            background: Rectangle {
                radius: 10
                color: "#0b151f"
                border.color: "#1f3143"
                border.width: 1
            }

            TextArea {
                id: logArea
                readOnly: true
                selectByMouse: true
                wrapMode: TextArea.Wrap
                textFormat: TextEdit.RichText
                text: logCard.logger ? logCard.logger.richText : ""
                color: "#edf2f7"
                font.family: "Consolas, Courier New, monospace"
                font.pixelSize: 12
                leftPadding: 12
                rightPadding: 12
                topPadding: 10
                bottomPadding: 10
                placeholderText: "Esperando acciones... Aquí se mostrarán los mensajes de estado y proceso."
                placeholderTextColor: "#556e84"
                background: null

                onTextChanged: {
                    if (logScroll.ScrollBar.vertical) {
                        logScroll.ScrollBar.vertical.position = Math.max(0, 1.0 - logScroll.ScrollBar.vertical.size)
                    }
                }
            }
        }
    }
}

