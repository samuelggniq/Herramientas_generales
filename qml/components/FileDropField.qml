import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ContentCard {
    id: rootField

    property string title: "📂 Archivo de Origen"
    property string placeholder: "Selecciona o arrastra un archivo (.xlsx, .xls, .xlsm, .csv)..."
    property var controller: null
    property bool allowMultiple: false
    property bool showCsvOptions: true
    property bool showInferTypes: true

    // Estado expuesto
    property string filePath: ""
    property var selectedFiles: []
    property bool isExcel: false
    property bool isCsv: false
    property var sheets: []
    property string selectedSheet: ""
    property string selectedDelimiter: "auto"
    property string selectedEncoding: "auto"
    property bool inferTypes: false
    property string detectedInfo: ""

    signal fileLoaded()
    signal configurationChanged()

    property bool isDraggingOver: false

    Layout.fillWidth: true
    implicitHeight: mainCol.implicitHeight + 32

    color: isDraggingOver ? "#1e3852" : "#14212f"
    border.color: isDraggingOver ? "#2d9cff" : "#1f3143"
    border.width: isDraggingOver ? 2 : 1
    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }

    function cleanUrl(rawUrl) {
        var str = rawUrl.toString()
        if (str.indexOf("file:///") === 0) {
            str = str.substring(8)
        } else if (str.indexOf("file://") === 0) {
            str = str.substring(7)
        }
        return decodeURIComponent(str)
    }

    function applyPaths(pathsList) {
        if (!pathsList || pathsList.length === 0) return
        rootField.selectedFiles = pathsList
        rootField.filePath = pathsList[0]
        pathInput.text = pathsList.length > 1
            ? (pathsList[0] + " (+" + (pathsList.length - 1) + " archivos más)")
            : pathsList[0]

        if (rootField.controller) {
            var meta = rootField.controller.inspectFile(rootField.filePath)
            if (meta && meta.ok) {
                rootField.isExcel = meta.isExcel
                rootField.isCsv = meta.isCsv
                rootField.sheets = meta.sheets || []
                rootField.selectedSheet = meta.defaultSheet || ""
                if (meta.isCsv) {
                    var delimLabel = meta.detectedDelimiter === "\t" ? "\\t" : meta.detectedDelimiter
                    rootField.detectedInfo = "Detectado: " + meta.detectedEncoding + " | sep: '" + delimLabel + "'"
                } else {
                    rootField.detectedInfo = "Excel (" + rootField.sheets.length + " hoja(s))"
                }
            } else {
                rootField.detectedInfo = meta && meta.error ? meta.error : ""
            }
        }
        rootField.fileLoaded()
        rootField.configurationChanged()
    }

    function clearSelection() {
        rootField.filePath = ""
        rootField.selectedFiles = []
        rootField.isExcel = false
        rootField.isCsv = false
        rootField.sheets = []
        rootField.selectedSheet = ""
        rootField.detectedInfo = ""
        pathInput.text = ""
        rootField.configurationChanged()
    }

    FileDialog {
        id: fileDialog
        title: rootField.title
        fileMode: rootField.allowMultiple ? FileDialog.OpenFiles : FileDialog.OpenFile
        nameFilters: [
            "Archivos de Datos (*.xlsx *.xls *.xlsm *.csv *.tsv *.txt)",
            "Archivos Excel (*.xlsx *.xls *.xlsm)",
            "Archivos CSV / Texto (*.csv *.tsv *.txt)",
            "Todos los archivos (*.*)"
        ]
        onAccepted: {
            var list = []
            if (rootField.allowMultiple && selectedFiles && selectedFiles.length > 0) {
                for (var i = 0; i < selectedFiles.length; i++) {
                    list.push(rootField.cleanUrl(selectedFiles[i]))
                }
            } else if (selectedFile) {
                list.push(rootField.cleanUrl(selectedFile))
            }
            rootField.applyPaths(list)
        }
    }

    DropArea {
        anchors.fill: parent
        onEntered: (drag) => {
            if (drag.hasUrls) {
                drag.accept()
                rootField.isDraggingOver = true
            }
        }
        onExited: rootField.isDraggingOver = false
        onDropped: (drop) => {
            rootField.isDraggingOver = false
            if (drop.hasUrls && drop.urls.length > 0) {
                var list = []
                var maxCount = rootField.allowMultiple ? drop.urls.length : 1
                for (var i = 0; i < maxCount; i++) {
                    list.push(rootField.cleanUrl(drop.urls[i]))
                }
                rootField.applyPaths(list)
            }
        }
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: rootField.title
                color: "#edf2f7"
                font.pixelSize: 15
                font.bold: true
                Layout.fillWidth: true
            }

            Text {
                visible: rootField.detectedInfo !== ""
                text: rootField.detectedInfo
                color: "#10b981"
                font.pixelSize: 12
                font.bold: true
            }

            Text {
                text: rootField.isDraggingOver ? "¡Suelta aquí!" : "Arrastra y suelta o examina"
                color: rootField.isDraggingOver ? "#2d9cff" : "#556e84"
                font.pixelSize: 12
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            StyledTextField {
                id: pathInput
                Layout.fillWidth: true
                placeholderText: rootField.placeholder
                onEditingFinished: {
                    var trimmed = pathInput.text.trim()
                    if (trimmed.length > 0 && trimmed !== rootField.filePath && rootField.selectedFiles.length <= 1) {
                        rootField.applyPaths([trimmed])
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: 22
                    height: 22
                    radius: 11
                    color: clearMouse.containsMouse ? "#2d445d" : "transparent"
                    visible: pathInput.text.length > 0

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: "#8b9fb2"
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: clearMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: rootField.clearSelection()
                    }
                }
            }

            ActionButton {
                isPrimary: false
                text: "Examinar..."
                implicitWidth: 110
                implicitHeight: 40
                onClicked: fileDialog.open()
            }
        }

        // Opciones dinámicas según si es Excel (Hojas) o CSV (Delimitador/Codificación)
        Flow {
            Layout.fillWidth: true
            spacing: 14
            visible: rootField.filePath.length > 0

            RowLayout {
                spacing: 6
                visible: rootField.isExcel && rootField.sheets.length > 0

                Text {
                    text: "Hoja Excel:"
                    color: "#8b9fb2"
                    font.pixelSize: 12
                }

                StyledComboBox {
                    id: sheetCombo
                    implicitWidth: 170
                    implicitHeight: 34
                    model: rootField.sheets
                    onActivated: {
                        rootField.selectedSheet = currentText
                        rootField.configurationChanged()
                    }
                }
            }

            RowLayout {
                spacing: 6
                visible: rootField.isCsv && rootField.showCsvOptions

                Text {
                    text: "Delimitador:"
                    color: "#8b9fb2"
                    font.pixelSize: 12
                }

                StyledComboBox {
                    implicitWidth: 155
                    implicitHeight: 34
                    model: ["Automático", "Coma (,)", "Punto y coma (;)", "Tabulador (\\t)", "Barra vertical (|)"]
                    onActivated: {
                        var map = {
                            "Automático": "auto",
                            "Coma (,)": ",",
                            "Punto y coma (;)": ";",
                            "Tabulador (\\t)": "\t",
                            "Barra vertical (|)": "|"
                        }
                        rootField.selectedDelimiter = map[currentText] || "auto"
                        rootField.configurationChanged()
                    }
                }
            }

            RowLayout {
                spacing: 6
                visible: rootField.isCsv && rootField.showCsvOptions

                Text {
                    text: "Codificación:"
                    color: "#8b9fb2"
                    font.pixelSize: 12
                }

                StyledComboBox {
                    implicitWidth: 155
                    implicitHeight: 34
                    model: ["Automático", "utf-8-sig", "utf-8", "cp1252", "latin-1"]
                    onActivated: {
                        rootField.selectedEncoding = currentText === "Automático" ? "auto" : currentText
                        rootField.configurationChanged()
                    }
                }
            }

            StyledCheckBox {
                visible: rootField.showInferTypes
                text: "Inferir tipos (desactivar preserva ceros a la izquierda)"
                checked: rootField.inferTypes
                onToggled: {
                    rootField.inferTypes = checked
                    rootField.configurationChanged()
                }
            }
        }
    }
}

