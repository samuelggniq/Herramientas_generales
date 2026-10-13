import QtQuick
import QtQuick.Controls

TextField {
    id: sField
    implicitHeight: 40
    color: "#edf2f7"
    placeholderTextColor: "#556e84"
    font.pixelSize: 13
    verticalAlignment: Text.AlignVCenter
    leftPadding: 14
    rightPadding: 14
    selectByMouse: true

    background: Rectangle {
        radius: 10
        color: "#0b151f"
        border.color: sField.activeFocus ? "#2d9cff" : "#1f3143"
        border.width: sField.activeFocus ? 2 : 1
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }
}

