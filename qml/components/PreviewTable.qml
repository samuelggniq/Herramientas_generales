import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ContentCard {
    id: tableCard

    property string title: "👁️ Vista Previa de Datos"
    property var columns: []
    property var rows: []
    property int totalRows: 0
    property int totalCols: 0
    property int columnWidth: 145
    property int preferredTableHeight: 220
    property bool sortable: true
    property int highlightNullColIndex: -1

    property int sortColIndex: -1
    property bool sortAscending: true
    property var displayedRows: rows

    Layout.fillWidth: true
    implicitHeight: mainCol.implicitHeight + 28

    onRowsChanged: {
        sortColIndex = -1
        displayedRows = rows || []
    }

    function sortByColumn(colIdx) {
        if (!sortable || !rows || rows.length === 0) return
        if (sortColIndex === colIdx) {
            sortAscending = !sortAscending
        } else {
            sortColIndex = colIdx
            sortAscending = true
        }
        var copy = rows.slice()
        var asc = sortAscending
        copy.sort(function(a, b) {
            var va = (a && colIdx < a.length) ? String(a[colIdx]) : ""
            var vb = (b && colIdx < b.length) ? String(b[colIdx]) : ""
            var na = parseFloat(va.replace("%", "").replace(",", "."))
            var nb = parseFloat(vb.replace("%", "").replace(",", "."))
            if (!isNaN(na) && !isNaN(nb) && va.trim() !== "" && vb.trim() !== "") {
                return asc ? (na - nb) : (nb - na)
            }
            return asc ? va.localeCompare(vb) : vb.localeCompare(va)
        })
        displayedRows = copy
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Text {
                text: tableCard.title
                color: "#edf2f7"
                font.pixelSize: 15
                font.bold: true
                Layout.fillWidth: true
            }

            Rectangle {
                visible: tableCard.columns && tableCard.columns.length > 0
                radius: 10
                color: "#1d2e40"
                border.color: "#1f3143"
                implicitWidth: statsText.implicitWidth + 18
                implicitHeight: 24

                Text {
                    id: statsText
                    anchors.centerIn: parent
                    text: "Mostrando " + (tableCard.displayedRows ? tableCard.displayedRows.length : 0) +
                          (tableCard.totalRows > 0 ? (" de " + tableCard.totalRows + " filas") : " filas") +
                          " • " + (tableCard.columns ? tableCard.columns.length : 0) + " cols"
                    color: "#8b9fb2"
                    font.pixelSize: 11
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: tableCard.preferredTableHeight
            radius: 10
            color: "#0b151f"
            border.color: "#1f3143"
            border.width: 1
            clip: true

            Text {
                anchors.centerIn: parent
                visible: !tableCard.columns || tableCard.columns.length === 0
                text: "Sin datos para previsualizar. Selecciona un archivo o ejecuta una consulta."
                color: "#556e84"
                font.pixelSize: 13
            }

            Flickable {
                id: hFlick
                anchors.fill: parent
                visible: tableCard.columns && tableCard.columns.length > 0
                contentWidth: Math.max(width, (tableCard.columns ? tableCard.columns.length : 0) * tableCard.columnWidth)
                contentHeight: height
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ScrollBar.horizontal: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                ColumnLayout {
                    width: hFlick.contentWidth
                    height: hFlick.height
                    spacing: 0

                    // Fila de encabezados
                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        color: "#162536"

                        Row {
                            anchors.fill: parent
                            Repeater {
                                model: tableCard.columns
                                Rectangle {
                                    width: tableCard.columnWidth
                                    height: 34
                                    color: headerMouse.containsMouse ? "#1e344b" : "transparent"
                                    border.color: "#1f3143"
                                    border.width: 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        spacing: 4

                                        Text {
                                            text: String(modelData)
                                            color: "#ffffff"
                                            font.pixelSize: 12
                                            font.bold: true
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }

                                        Text {
                                            visible: tableCard.sortColIndex === index
                                            text: tableCard.sortAscending ? "▲" : "▼"
                                            color: "#2d9cff"
                                            font.pixelSize: 10
                                        }
                                    }

                                    MouseArea {
                                        id: headerMouse
                                        anchors.fill: parent
                                        hoverEnabled: tableCard.sortable
                                        cursorShape: tableCard.sortable ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: tableCard.sortByColumn(index)
                                    }
                                }
                            }
                        }
                    }

                    // Lista de filas con scroll vertical
                    ListView {
                        id: rowListView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: tableCard.displayedRows
                        boundsBehavior: Flickable.StopAtBounds

                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                        }

                        delegate: Rectangle {
                            id: rowDelegate
                            width: hFlick.contentWidth
                            height: 28
                            readonly property var rowData: modelData
                            readonly property int rowNum: index
                            color: rowNum % 2 === 0 ? "#0b151f" : "#101d2b"

                            Row {
                                anchors.fill: parent
                                Repeater {
                                    model: tableCard.columns ? tableCard.columns.length : 0
                                    Rectangle {
                                        width: tableCard.columnWidth
                                        height: 28
                                        readonly property string cellVal: (rowDelegate.rowData && index < rowDelegate.rowData.length)
                                            ? String(rowDelegate.rowData[index])
                                            : ""
                                        color: {
                                            if (tableCard.highlightNullColIndex === index) {
                                                var pct = parseFloat(cellVal.replace("%", ""))
                                                if (!isNaN(pct)) {
                                                    if (pct >= 50) return "#3b1822"
                                                    if (pct >= 15) return "#382c18"
                                                    if (pct > 0) return "#162b28"
                                                }
                                            }
                                            return "transparent"
                                        }
                                        border.color: "#152331"
                                        border.width: 1

                                        Text {
                                            anchors.fill: parent
                                            anchors.leftMargin: 8
                                            anchors.rightMargin: 8
                                            verticalAlignment: Text.AlignVCenter
                                            text: parent.cellVal
                                            color: parent.cellVal === "" ? "#556e84" : "#edf2f7"
                                            font.pixelSize: 12
                                            font.family: "Consolas, Courier New, monospace"
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

