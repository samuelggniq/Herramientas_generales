import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: fileDiffController

    property var colsA: []
    property var colsB: []
    property var commonColumns: []

    function updateCommonColumns() {
        var common = []
        for (var i = 0; i < colsA.length; i++) {
            if (colsB.indexOf(colsA[i]) !== -1) {
                common.push(colsA[i])
            }
        }
        commonColumns = common
    }

    function refreshFileA() {
        if (!controller || !fileA.filePath) {
            colsA = []
            updateCommonColumns()
            return
        }
        var prev = controller.loadPreview(
            fileA.filePath,
            fileA.selectedSheet,
            fileA.selectedDelimiter,
            fileA.selectedEncoding,
            fileA.inferTypes
        )
        if (prev && prev.ok) {
            colsA = prev.columns || []
            updateCommonColumns()
        }
    }

    function refreshFileB() {
        if (!controller || !fileB.filePath) {
            colsB = []
            updateCommonColumns()
            return
        }
        var prev = controller.loadPreview(
            fileB.filePath,
            fileB.selectedSheet,
            fileB.selectedDelimiter,
            fileB.selectedEncoding,
            fileB.inferTypes
        )
        if (prev && prev.ok) {
            colsB = prev.columns || []
            updateCommonColumns()
        }
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
                    text: "Comparador de Archivos (Diff A vs B)"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Identifica filas nuevas, eliminadas, iguales y celdas exactas modificadas entre una versión original (A) y una nueva (B)."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // Selectores lado a lado
            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                FileDropField {
                    id: fileA
                    Layout.fillWidth: true
                    title: "📂 Archivo A (Original / Base)"
                    controller: pageRoot.controller
                    showInferTypes: false
                    onConfigurationChanged: pageRoot.refreshFileA()
                }

                FileDropField {
                    id: fileB
                    Layout.fillWidth: true
                    title: "📂 Archivo B (Nuevo / Actualizado)"
                    controller: pageRoot.controller
                    showInferTypes: false
                    onConfigurationChanged: pageRoot.refreshFileB()
                }
            }

            // Configuración de Claves y Opciones
            ContentCard {
                Layout.fillWidth: true
                implicitHeight: cfgCol.implicitHeight + 28

                ColumnLayout {
                    id: cfgCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text {
                        text: "⚙️ Claves y Opciones de Comparación"
                        color: "#edf2f7"
                        font.pixelSize: 15
                        font.bold: true
                    }

                    ColumnPicker {
                        id: keyPicker
                        label: "1. Columna(s) Clave que identifican cada fila (Obligatorio):"
                        availableColumns: pageRoot.commonColumns
                    }

                    ColumnPicker {
                        id: comparePicker
                        label: "2. Columnas a comparar (Opcional: vacío compara TODAS las comunes):"
                        availableColumns: pageRoot.commonColumns
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 18

                        StyledCheckBox {
                            id: chkIgnoreCase
                            text: "Ignorar mayúsculas/minúsculas"
                            checked: false
                        }

                        StyledCheckBox {
                            id: chkIgnoreSpaces
                            text: "Ignorar espacios sobrantes"
                            checked: true
                        }

                        StyledCheckBox {
                            id: chkEmptyNull
                            text: "Tratar vacío = nulo"
                            checked: true
                        }

                        RowLayout {
                            spacing: 6
                            Text {
                                text: "Tolerancia numérica:"
                                color: "#8b9fb2"
                                font.pixelSize: 12
                            }
                            StyledTextField {
                                id: txtTolerance
                                implicitWidth: 90
                                implicitHeight: 32
                                text: "0.0"
                                placeholderText: "0.00"
                            }
                        }
                    }
                }
            }

            // Avisos de claves duplicadas si existen
            ContentCard {
                Layout.fillWidth: true
                visible: pageRoot.controller && pageRoot.controller.warnings && pageRoot.controller.warnings.length > 0
                color: "#2b2213"
                border.color: "#f59e0b"
                implicitHeight: warnCol.implicitHeight + 20

                ColumnLayout {
                    id: warnCol
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 4

                    Repeater {
                        model: pageRoot.controller ? pageRoot.controller.warnings : []
                        Text {
                            text: "⚠️ " + String(modelData)
                            color: "#fde68a"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // Resumen en pantalla
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Selector de pestaña de vista previa del resultado
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: pageRoot.controller && pageRoot.controller.summaryCards.length > 0

                Text {
                    text: "Ver detalle en tabla:"
                    color: "#8b9fb2"
                    font.pixelSize: 12
                }

                QueryChip {
                    chipText: "🔎 Detalle Celdas Cambiadas"
                    onClicked: pageRoot.controller.setResultTab("changes")
                }
                QueryChip {
                    chipText: "✏️ Filas Modificadas"
                    onClicked: pageRoot.controller.setResultTab("modified")
                }
                QueryChip {
                    chipText: "➕ Filas Nuevas"
                    onClicked: pageRoot.controller.setResultTab("added")
                }
                QueryChip {
                    chipText: "➖ Filas Eliminadas"
                    onClicked: pageRoot.controller.setResultTab("deleted")
                }
                Item { Layout.fillWidth: true }
            }

            // Tabla de resultados
            PreviewTable {
                title: "📊 Resultado de Diferencias"
                columns: pageRoot.controller ? pageRoot.controller.tableColumns : []
                rows: pageRoot.controller ? pageRoot.controller.tableRows : []
                totalRows: pageRoot.controller ? pageRoot.controller.tableTotalRows : 0
                preferredTableHeight: 190
                columnWidth: 175
            }

            // Formato de salida
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            // Acción y progreso
            ProgressCard {
                controller: pageRoot.controller
                primaryText: "⚖️ Comparar Archivos y Exportar Reporte"
                canExecute: fileA.filePath !== "" && fileB.filePath !== "" && keyPicker.selectedColumns.length > 0
                onExecuteClicked: {
                    var tol = parseFloat(txtTolerance.text.replace(",", "."))
                    if (isNaN(tol) || tol < 0) tol = 0.0
                    pageRoot.controller.runComparison(
                        fileA.filePath,
                        fileB.filePath,
                        keyPicker.selectedColumns,
                        comparePicker.selectedColumns,
                        chkIgnoreCase.checked,
                        chkIgnoreSpaces.checked,
                        tol,
                        chkEmptyNull.checked,
                        fileA.selectedSheet,
                        fileA.selectedDelimiter,
                        fileA.selectedEncoding,
                        fileA.inferTypes,
                        fileB.selectedSheet,
                        fileB.selectedDelimiter,
                        fileB.selectedEncoding,
                        fileB.inferTypes,
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

