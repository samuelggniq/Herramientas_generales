import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ContentCard {
    id: progCard

    property var controller: null
    property string primaryText: "Ejecutar Proceso"
    property bool canExecute: true
    signal executeClicked()

    readonly property bool isBusy: controller ? controller.isBusy : false
    readonly property int progressValue: controller ? controller.progressValue : 0
    readonly property string progressMessage: controller ? controller.progressMessage : "Listo"
    readonly property string lastOutputPath: controller ? controller.lastOutputPath : ""

    Layout.fillWidth: true
    implicitHeight: col.implicitHeight + 28

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ActionButton {
                isPrimary: true
                text: progCard.primaryText
                Layout.fillWidth: true
                implicitHeight: 44
                enabled: progCard.canExecute && !progCard.isBusy
                onClicked: progCard.executeClicked()
            }

            ActionButton {
                visible: progCard.isBusy
                isPrimary: false
                isDanger: true
                text: "⏹ Cancelar"
                implicitHeight: 44
                onClicked: {
                    if (progCard.controller) progCard.controller.cancelTask()
                }
            }

            ActionButton {
                visible: !progCard.isBusy && progCard.lastOutputPath !== ""
                isPrimary: false
                text: "📄 Abrir archivo"
                implicitHeight: 44
                onClicked: {
                    if (progCard.controller) progCard.controller.openOutputFile()
                }
            }

            ActionButton {
                visible: !progCard.isBusy && progCard.lastOutputPath !== ""
                isPrimary: false
                text: "📂 Abrir carpeta"
                implicitHeight: 44
                onClicked: {
                    if (progCard.controller) progCard.controller.openOutputFolder()
                }
            }
        }

        // Barra de progreso y estado
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            visible: progCard.isBusy || progCard.progressValue > 0

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: progCard.progressMessage
                    color: "#8b9fb2"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Text {
                    text: progCard.progressValue + "%"
                    color: "#2d9cff"
                    font.pixelSize: 12
                    font.bold: true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 8
                radius: 4
                color: "#0b151f"
                border.color: "#1f3143"
                border.width: 1
                clip: true

                Rectangle {
                    width: parent.width * (Math.max(0, Math.min(100, progCard.progressValue)) / 100.0)
                    height: parent.height
                    radius: 4
                    color: progCard.progressValue >= 100 ? "#10b981" : "#2d9cff"
                    Behavior on width { NumberAnimation { duration: 120 } }
                }
            }
        }
    }
}

