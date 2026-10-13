import QtQuick
import QtQuick.Layouts

ContentCard {
    id: connCard

    property var controller: null

    Layout.fillWidth: true
    implicitHeight: col.implicitHeight + 28

    readonly property string stateCode: controller ? controller.connectionState : "disconnected"
    readonly property color badgeColor: {
        if (stateCode === "connected") return "#10b981"
        if (stateCode === "error" || stateCode === "missing_env") return "#ef4444"
        if (stateCode === "testing") return "#f59e0b"
        return "#8b9fb2"
    }
    readonly property string badgeLabel: {
        if (stateCode === "connected") return "Conectado"
        if (stateCode === "error") return "Error de conexión"
        if (stateCode === "missing_env") return "Falta configurar .env"
        if (stateCode === "testing") return "Probando..."
        return "Desconectado"
    }

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: "🔌 Estado de Conexión Oracle (.env)"
                color: "#edf2f7"
                font.pixelSize: 15
                font.bold: true
            }

            // Indicador de estado
            Rectangle {
                radius: 11
                height: 22
                implicitWidth: statusRow.implicitWidth + 18
                color: "#0b151f"
                border.color: connCard.badgeColor
                border.width: 1

                RowLayout {
                    id: statusRow
                    anchors.centerIn: parent
                    spacing: 6

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: connCard.badgeColor
                    }

                    Text {
                        text: connCard.badgeLabel
                        color: connCard.badgeColor
                        font.pixelSize: 11
                        font.bold: true
                    }
                }
            }

            // Host y Servicio (NUNCA usuario ni contraseña)
            Rectangle {
                visible: connCard.controller && connCard.controller.isConfigValid
                radius: 8
                height: 24
                implicitWidth: hostTxt.implicitWidth + 16
                color: "#162536"
                border.color: "#1f3143"

                Text {
                    id: hostTxt
                    anchors.centerIn: parent
                    text: connCard.controller
                        ? ("Host: " + connCard.controller.displayHost + "  |  Servicio: " + connCard.controller.displayService)
                        : ""
                    color: "#edf2f7"
                    font.pixelSize: 12
                    font.family: "Consolas, Courier New, monospace"
                }
            }

            Item { Layout.fillWidth: true }

            ActionButton {
                isPrimary: false
                text: "🔄 Recargar .env"
                implicitHeight: 32
                enabled: connCard.controller && !connCard.controller.isBusy
                onClicked: {
                    if (connCard.controller) connCard.controller.reloadConfig()
                }
            }

            ActionButton {
                isPrimary: false
                text: "⚡ Probar conexión"
                implicitHeight: 32
                enabled: connCard.controller && connCard.controller.isConfigValid && !connCard.controller.isBusy
                onClicked: {
                    if (connCard.controller) connCard.controller.testConnection()
                }
            }
        }

        // Mensaje de estado o alerta de variables faltantes en .env
        Rectangle {
            Layout.fillWidth: true
            visible: connCard.controller && connCard.controller.statusMessage !== ""
            implicitHeight: msgText.implicitHeight + 16
            radius: 10
            color: (connCard.stateCode === "missing_env" || connCard.stateCode === "error") ? "#2c161e" : "#0b151f"
            border.color: (connCard.stateCode === "missing_env" || connCard.stateCode === "error") ? "#ef4444" : "#1f3143"
            border.width: 1

            Text {
                id: msgText
                anchors.fill: parent
                anchors.margins: 8
                wrapMode: Text.WordWrap
                text: connCard.controller ? connCard.controller.statusMessage : ""
                color: (connCard.stateCode === "missing_env" || connCard.stateCode === "error") ? "#fecaca" : "#8b9fb2"
                font.pixelSize: 12
            }
        }
    }
}

