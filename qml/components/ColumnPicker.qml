import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: pickerRoot

    property string label: "Seleccionar columnas:"
    property var availableColumns: []
    property var selectedColumns: []
    property int maxChipsHeight: 92

    signal selectionModified(var selected)

    Layout.fillWidth: true
    implicitHeight: pickerCol.implicitHeight + 20
    radius: 12
    color: "#0b151f"
    border.color: "#1f3143"
    border.width: 1

    onAvailableColumnsChanged: {
        // Filtrar seleccionadas para mantener solo las que existen en availableColumns
        var valid = []
        for (var i = 0; i < selectedColumns.length; i++) {
            if (availableColumns.indexOf(selectedColumns[i]) !== -1) {
                valid.push(selectedColumns[i])
            }
        }
        selectedColumns = valid
    }

    function isSelected(colName) {
        return selectedColumns.indexOf(colName) !== -1
    }

    function toggleColumn(colName) {
        var copy = selectedColumns.slice()
        var idx = copy.indexOf(colName)
        if (idx >= 0) {
            copy.splice(idx, 1)
        } else {
            copy.push(colName)
        }
        selectedColumns = copy
        selectionModified(selectedColumns)
    }

    function selectAll() {
        selectedColumns = availableColumns.slice()
        selectionModified(selectedColumns)
    }

    function clearAll() {
        selectedColumns = []
        selectionModified(selectedColumns)
    }

    ColumnLayout {
        id: pickerCol
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: pickerRoot.label
                color: "#edf2f7"
                font.pixelSize: 13
                font.bold: true
            }

            Text {
                text: "(" + pickerRoot.selectedColumns.length + " de " + pickerRoot.availableColumns.length + ")"
                color: "#2d9cff"
                font.pixelSize: 12
            }

            Item { Layout.fillWidth: true }

            StyledTextField {
                id: filterBox
                implicitWidth: 150
                implicitHeight: 28
                font.pixelSize: 12
                placeholderText: "Filtrar columna..."
                visible: pickerRoot.availableColumns.length > 5
            }

            ActionButton {
                isPrimary: false
                text: "Todas"
                implicitHeight: 26
                enabled: pickerRoot.availableColumns.length > 0
                onClicked: pickerRoot.selectAll()
            }

            ActionButton {
                isPrimary: false
                text: "Ninguna"
                implicitHeight: 26
                enabled: pickerRoot.selectedColumns.length > 0
                onClicked: pickerRoot.clearAll()
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(pickerRoot.maxChipsHeight, Math.max(36, chipFlow.implicitHeight + 8))
            clip: true

            Flow {
                id: chipFlow
                width: parent.width
                spacing: 6

                Text {
                    visible: pickerRoot.availableColumns.length === 0
                    text: "Carga un archivo para ver sus columnas disponibles."
                    color: "#556e84"
                    font.pixelSize: 12
                }

                Repeater {
                    model: pickerRoot.availableColumns
                    Rectangle {
                        readonly property string colName: String(modelData)
                        readonly property bool matchesFilter: filterBox.text.trim() === "" ||
                            colName.toLowerCase().indexOf(filterBox.text.trim().toLowerCase()) !== -1
                        readonly property bool active: pickerRoot.selectedColumns.indexOf(colName) !== -1

                        visible: matchesFilter
                        implicitWidth: chipTxt.implicitWidth + 22
                        implicitHeight: 28
                        radius: 8
                        color: active ? "#1b3a5c" : (chipArea.containsMouse ? "#162536" : "#14212f")
                        border.color: active ? "#2d9cff" : "#1f3143"
                        border.width: 1

                        Text {
                            id: chipTxt
                            anchors.centerIn: parent
                            text: (parent.active ? "✓ " : "") + parent.colName
                            color: parent.active ? "#ffffff" : "#8b9fb2"
                            font.pixelSize: 12
                            font.bold: parent.active
                        }

                        MouseArea {
                            id: chipArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: pickerRoot.toggleColumn(parent.colName)
                        }
                    }
                }
            }
        }
    }
}

