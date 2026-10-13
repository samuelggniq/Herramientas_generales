import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: fileMergeController

    property var leftColumns: []
    property var rightColumns: []
    property var keyPairs: [] // [{ left: "colA", right: "colB" }]

    function loadLeft() {
        if (!controller || !fileLeft.filePath) {
            leftColumns = []
            keyPairs = []
            return
        }
        var prev = controller.loadPreview(
            fileLeft.filePath,
            fileLeft.selectedSheet,
            fileLeft.selectedDelimiter,
            fileLeft.selectedEncoding,
            fileLeft.inferTypes
        )
        if (prev && prev.ok) {
            leftColumns = prev.columns || []
            autoSuggestFirstKey()
        }
    }

    function loadRight() {
        if (!controller || !fileRight.filePath) {
            rightColumns = []
            keyPairs = []
            return
        }
        var prev = controller.loadPreview(
            fileRight.filePath,
            fileRight.selectedSheet,
            fileRight.selectedDelimiter,
            fileRight.selectedEncoding,
            fileRight.inferTypes
        )
        if (prev && prev.ok) {
            rightColumns = prev.columns || []
            autoSuggestFirstKey()
        }
    }

    function autoSuggestFirstKey() {
        if (keyPairs.length > 0 || leftColumns.length === 0 || rightColumns.length === 0) return
        for (var i = 0; i < leftColumns.length; i++) {
            for (var j = 0; j < rightColumns.length; j++) {
                if (leftColumns[i].toLowerCase() === rightColumns[j].toLowerCase()) {
                    keyPairs = [{ "left": leftColumns[i], "right": rightColumns[j] }]
                    return
                }
            }
        }
    }

    function addKeyPair() {
        var lk = comboLeftKey.currentText
        var rk = comboRightKey.currentText
        if (!lk || !rk) return
        var copy = keyPairs.slice()
        for (var i = 0; i < copy.length; i++) {
            if (copy[i].left === lk && copy[i].right === rk) return
        }
        copy.push({ "left": lk, "right": rk })
        keyPairs = copy
    }

    function removeKeyPair(idx) {
        var copy = keyPairs.slice()
        copy.splice(idx, 1)
        keyPairs = copy
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: 24
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 14

            // Encabezado
            ColumnLayout {
                spacing: 4
                Text {
                    text: "Cruce de Archivos (Merge / VLOOKUP)"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Une dos archivos emparejando una o varias columnas clave (aunque se llamen distinto) y selecciona qué columnas traer."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // Selectores de archivos
            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                FileDropField {
                    id: fileLeft
                    Layout.fillWidth: true
                    title: "📂 Archivo Izquierdo (Base / Principal)"
                    controller: pageRoot.controller
                    showInferTypes: false
                    onConfigurationChanged: pageRoot.loadLeft()
                }

                FileDropField {
                    id: fileRight
                    Layout.fillWidth: true
                    title: "📂 Archivo Derecho (Catálogo / VLOOKUP)"
                    controller: pageRoot.controller
                    showInferTypes: false
                    onConfigurationChanged: pageRoot.loadRight()
                }
            }

            // Configuración de emparejamiento de claves y tipo de cruce
            ContentCard {
                Layout.fillWidth: true
                implicitHeight: mergeCfgCol.implicitHeight + 28

                ColumnLayout {
                    id: mergeCfgCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text {
                        text: "🔗 Emparejamiento Manual de Columnas Clave"
                        color: "#edf2f7"
                        font.pixelSize: 15
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text { text: "Clave Izquierda:"; color: "#8b9fb2"; font.pixelSize: 12 }
                        StyledComboBox {
                            id: comboLeftKey
                            implicitWidth: 185
                            model: pageRoot.leftColumns
                        }

                        Text { text: "⇔ Clave Derecha:"; color: "#8b9fb2"; font.pixelSize: 12 }
                        StyledComboBox {
                            id: comboRightKey
                            implicitWidth: 185
                            model: pageRoot.rightColumns
                        }

                        ActionButton {
                            isPrimary: false
                            text: "+ Vincular par de claves"
                            implicitHeight: 34
                            enabled: comboLeftKey.currentText !== "" && comboRightKey.currentText !== ""
                            onClicked: pageRoot.addKeyPair()
                        }

                        Item { Layout.fillWidth: true }
                    }

                    // Lista de pares de claves vinculados
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            visible: pageRoot.keyPairs.length === 0
                            text: "No hay claves vinculadas todavía. Selecciona una columna de cada archivo y presiona '+ Vincular par de claves'."
                            color: "#f59e0b"
                            font.pixelSize: 12
                        }

                        Repeater {
                            model: pageRoot.keyPairs
                            Rectangle {
                                radius: 10
                                color: "#1b3a5c"
                                border.color: "#2d9cff"
                                border.width: 1
                                implicitWidth: pairRow.implicitWidth + 20
                                implicitHeight: 30

                                RowLayout {
                                    id: pairRow
                                    anchors.centerIn: parent
                                    spacing: 8

                                    Text {
                                        text: "🔑 " + modelData.left + "  ⇔  " + modelData.right
                                        color: "#ffffff"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    Text {
                                        text: "✕"
                                        color: "#fecaca"
                                        font.pixelSize: 12
                                        font.bold: true
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: pageRoot.removeKeyPair(index)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Selector de columnas del archivo derecho a traer (como en VLOOKUP)
                    ColumnPicker {
                        id: rightColsPicker
                        label: "Columnas del Archivo Derecho a traer (vacío = traer todas):"
                        availableColumns: pageRoot.rightColumns
                    }

                    // Tipo de cruce, filtro de no coincidentes y sufijos
                    Flow {
                        Layout.fillWidth: true
                        spacing: 16

                        RowLayout {
                            spacing: 6
                            Text { text: "Tipo de Cruce:"; color: "#8b9fb2"; font.pixelSize: 12 }
                            StyledComboBox {
                                id: comboHow
                                implicitWidth: 185
                                model: [
                                    "Left Join (Todo Izq + Coincidencias)",
                                    "Inner Join (Solo Coincidentes)",
                                    "Right Join (Todo Der + Coincidencias)",
                                    "Outer Join (Ambos Completos)"
                                ]
                            }
                        }

                        RowLayout {
                            spacing: 6
                            Text { text: "Filtro de Coincidencia:"; color: "#8b9fb2"; font.pixelSize: 12 }
                            StyledComboBox {
                                id: comboUnmatched
                                implicitWidth: 215
                                model: [
                                    "Resultado normal del cruce",
                                    "Solo sin coincidencia (Izquierdo)",
                                    "Solo sin coincidencia (Derecho)",
                                    "Solo sin coincidencia (Ambos lados)"
                                ]
                            }
                        }

                        RowLayout {
                            spacing: 6
                            Text { text: "Sufijos (Izq / Der):"; color: "#8b9fb2"; font.pixelSize: 12 }
                            StyledTextField {
                                id: txtSufLeft
                                implicitWidth: 65
                                implicitHeight: 32
                                text: "_izq"
                            }
                            StyledTextField {
                                id: txtSufRight
                                implicitWidth: 65
                                implicitHeight: 32
                                text: "_der"
                            }
                        }

                        StyledCheckBox {
                            id: chkKeyText
                            text: "Claves como texto (preservar ceros)"
                            checked: true
                        }

                        StyledCheckBox {
                            id: chkIgnoreCase
                            text: "Ignorar mayúsculas en clave"
                            checked: true
                        }

                        StyledCheckBox {
                            id: chkIgnoreSpaces
                            text: "Ignorar espacios en clave"
                            checked: true
                        }
                    }
                }
            }

            // Alerta visual de multiplicación de filas 1:N
            ContentCard {
                Layout.fillWidth: true
                visible: pageRoot.controller && pageRoot.controller.multiplicationWarning !== ""
                color: "#2c161e"
                border.color: "#ef4444"
                implicitHeight: multTxt.implicitHeight + 20

                Text {
                    id: multTxt
                    anchors.fill: parent
                    anchors.margins: 10
                    text: "⚠️ " + (pageRoot.controller ? pageRoot.controller.multiplicationWarning : "")
                    color: "#fecaca"
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
            }

            // Resumen de conteos
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Vista previa del resultado cruzado
            PreviewTable {
                title: "👁️ Vista Previa del Resultado del Cruce"
                columns: pageRoot.controller ? pageRoot.controller.previewColumns : []
                rows: pageRoot.controller ? pageRoot.controller.previewRows : []
                totalRows: pageRoot.controller ? pageRoot.controller.previewTotalRows : 0
                preferredTableHeight: 190
            }

            // Formato de salida
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            // Barra de acción y progreso
            ProgressCard {
                controller: pageRoot.controller
                primaryText: "🔗 Ejecutar Cruce y Exportar"
                canExecute: fileLeft.filePath !== "" && fileRight.filePath !== "" && pageRoot.keyPairs.length > 0
                onExecuteClicked: {
                    var lKeys = []
                    var rKeys = []
                    for (var i = 0; i < pageRoot.keyPairs.length; i++) {
                        lKeys.push(pageRoot.keyPairs[i].left)
                        rKeys.push(pageRoot.keyPairs[i].right)
                    }
                    var howCodes = ["left", "inner", "right", "outer"]
                    var ufCodes = ["all", "left_only", "right_only", "both_unmatched"]

                    pageRoot.controller.executeMerge(
                        fileLeft.filePath,
                        fileRight.filePath,
                        lKeys,
                        rKeys,
                        howCodes[comboHow.currentIndex] || "left",
                        ufCodes[comboUnmatched.currentIndex] || "all",
                        rightColsPicker.selectedColumns,
                        txtSufLeft.text,
                        txtSufRight.text,
                        chkIgnoreCase.checked,
                        chkIgnoreSpaces.checked,
                        chkKeyText.checked,
                        fileLeft.selectedSheet,
                        fileLeft.selectedDelimiter,
                        fileLeft.selectedEncoding,
                        fileLeft.inferTypes,
                        fileRight.selectedSheet,
                        fileRight.selectedDelimiter,
                        fileRight.selectedEncoding,
                        fileRight.inferTypes,
                        outFormat.outputFormat,
                        outFormat.csvDelimiter,
                        outFormat.csvEncoding
                    )
                }
            }

            LogPanel {
                preferredLogHeight: 145
            }
        }
    }
}

