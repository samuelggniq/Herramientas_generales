import QtQuick
import QtQuick.Controls

CheckBox {
    id: control
    implicitHeight: 28
    spacing: 8

    indicator: Rectangle {
        implicitWidth: 18
        implicitHeight: 18
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: 5
        color: control.checked ? "#2d9cff" : "#0b151f"
        border.color: control.checked ? "#2d9cff" : (control.hovered ? "#48aaff" : "#2d445d")
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: "✓"
            color: "#ffffff"
            font.pixelSize: 12
            font.bold: true
            visible: control.checked
        }
    }

    contentItem: Text {
        text: control.text
        font.pixelSize: 13
        color: control.enabled ? "#edf2f7" : "#556e84"
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }
}

