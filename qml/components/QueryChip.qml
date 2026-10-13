import QtQuick

Rectangle {
    id: chip
    property string chipText: ""
    signal clicked()

    implicitWidth: chipLabel.implicitWidth + 20
    implicitHeight: 28
    radius: 14
    color: chipMouse.containsMouse ? "#48aaff" : "#1d2e40"
    border.color: chipMouse.containsMouse ? "#2d9cff" : "#1f3143"
    border.width: 1
    Behavior on color { ColorAnimation { duration: 120 } }

    Text {
        id: chipLabel
        anchors.centerIn: parent
        text: chip.chipText
        font.pixelSize: 12
        font.family: "Consolas, Courier New, monospace"
        color: chipMouse.containsMouse ? "#ffffff" : "#8b9fb2"
    }

    MouseArea {
        id: chipMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: chip.clicked()
    }
}

