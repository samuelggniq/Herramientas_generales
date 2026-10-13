import QtQuick
import QtQuick.Controls

ComboBox {
    id: combo
    implicitHeight: 38
    implicitWidth: 160
    font.pixelSize: 13

    delegate: ItemDelegate {
        width: combo.width
        height: 34
        contentItem: Text {
            text: combo.textRole ? (Array.isArray(combo.model) ? modelData[combo.textRole] : model[combo.textRole]) : modelData
            color: highlighted ? "#ffffff" : "#edf2f7"
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: highlighted ? "#2d9cff" : (hovered ? "#18283a" : "#0e1823")
        }
        highlighted: combo.highlightedIndex === index
    }

    indicator: Text {
        x: combo.width - width - 12
        y: combo.topPadding + (combo.availableHeight - height) / 2
        text: "▾"
        color: "#8b9fb2"
        font.pixelSize: 13
    }

    contentItem: Text {
        leftPadding: 12
        rightPadding: combo.indicator.width + 16
        text: combo.displayText
        font: combo.font
        color: combo.enabled ? "#edf2f7" : "#556e84"
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        implicitWidth: 140
        implicitHeight: 38
        color: "#0b151f"
        border.color: combo.visualFocus || combo.popup.visible ? "#2d9cff" : (combo.hovered ? "#2d445d" : "#1f3143")
        border.width: 1
        radius: 10
    }

    popup: Popup {
        y: combo.height + 2
        width: combo.width
        implicitHeight: Math.min(260, contentItem.implicitHeight + 4)
        padding: 2

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: combo.popup.visible ? combo.delegateModel : null
            currentIndex: combo.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator { }
        }

        background: Rectangle {
            color: "#0e1823"
            border.color: "#2d9cff"
            border.width: 1
            radius: 10
        }
    }
}

