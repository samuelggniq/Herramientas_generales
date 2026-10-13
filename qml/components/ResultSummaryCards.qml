import QtQuick
import QtQuick.Layouts

Item {
    id: summaryRoot
    property var cards: []

    Layout.fillWidth: true
    implicitHeight: cards && cards.length > 0 ? 74 : 0
    visible: cards && cards.length > 0

    RowLayout {
        anchors.fill: parent
        spacing: 12

        Repeater {
            model: summaryRoot.cards
            ContentCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 14
                color: "#111e2c"
                border.color: modelData.color ? modelData.color : "#1f3143"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 2

                    Text {
                        text: (modelData.icon ? (modelData.icon + " ") : "") + String(modelData.label || "")
                        color: "#8b9fb2"
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Text {
                        text: String(modelData.value !== undefined ? modelData.value : "0")
                        color: modelData.color ? modelData.color : "#edf2f7"
                        font.pixelSize: 20
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }
}

