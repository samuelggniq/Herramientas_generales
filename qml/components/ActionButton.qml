import QtQuick
import QtQuick.Controls

Button {
    id: btn
    property bool isPrimary: true
    property bool isDanger: false

    implicitHeight: isPrimary ? 44 : 36
    implicitWidth: contentLabel.implicitWidth + 32
    hoverEnabled: true

    readonly property color cPrimary: "#2d9cff"
    readonly property color cPrimaryHover: "#48aaff"
    readonly property color cPrimaryPressed: "#1a84e2"
    readonly property color cDanger: "#ef4444"
    readonly property color cDangerHover: "#f87171"
    readonly property color cSecondary: "#1d2e40"
    readonly property color cSecondaryHover: "#263b52"
    readonly property color cBorder: "#1f3143"
    readonly property color cTextMuted: "#8b9fb2"
    readonly property color cTextDim: "#556e84"

    background: Rectangle {
        radius: btn.isPrimary ? 12 : 10
        color: {
            if (!btn.enabled) return btn.isPrimary ? "#1c2836" : "#131e2b"
            if (btn.isDanger) {
                return btn.down ? "#dc2626" : (btn.hovered ? btn.cDangerHover : btn.cDanger)
            }
            if (btn.isPrimary) {
                return btn.down ? btn.cPrimaryPressed : (btn.hovered ? btn.cPrimaryHover : btn.cPrimary)
            }
            return btn.down ? "#1c2d3f" : (btn.hovered ? btn.cSecondaryHover : btn.cSecondary)
        }
        border.color: {
            if (btn.isPrimary || btn.isDanger) return "transparent"
            return btn.hovered ? btn.cPrimary : btn.cBorder
        }
        border.width: (btn.isPrimary || btn.isDanger) ? 0 : 1
        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }

    contentItem: Text {
        id: contentLabel
        text: btn.text
        color: {
            if (!btn.enabled) return btn.cTextDim
            if (btn.isPrimary || btn.isDanger) return "#ffffff"
            return btn.hovered ? "#ffffff" : btn.cTextMuted
        }
        font.pixelSize: btn.isPrimary ? 14 : 13
        font.bold: btn.isPrimary || btn.isDanger
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: btn.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        acceptedButtons: Qt.NoButton
    }
}

