import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: duplicateFinderController
    property var availableColumns: []
    property var previewCols: []
    property var previewRows: []
    property int previewTotal: 0

    function onFileUpdated() {
        if (!controller || !fileSelector.filePath) {
            availableColumns = []
            previewCols = []
            previewRows = []
            previewTotal = 0
            return
        }
        var prev = controller.loadPreview(
            fileSelector.filePath,
            fileSelector.selectedSheet,
            fileSelector.selectedDelimiter,
            fileSelector.selectedEncoding,
            fileSelector.inferTypes
        )
        if (prev && prev.ok) {
            availableColumns = prev.columns || []
            previewCols = prev.columns || []
            previewRows = prev.rows || []
            previewTotal = prev.totalRows || 0
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
                    text: "Detector de Duplicados"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Separa el archivo en registros limpios y registros duplicados identificados por grupo y número de repeticiones."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // Selección de archivo
            FileDropField {
                id: fileSelector
                title: "📂 Archivo a Analizar"
                controller: pageRoot.controller
                onConfigurationChanged: pageRoot.onFileUpdated()
            }

            // Opciones de detección
            ContentCard {
                Layout.fillWidth: true
                implicitHeight: optCol.implicitHeight + 28

                ColumnLayout {
                    id: optCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text {
                        text: "⚙️ Criterios de Duplicidad"
                        color: "#edf2f7"
                        font.pixelSize: 15
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 18

                        Text {
                            text: "Modo:"
                            color: "#8b9fb2"
                            font.pixelSize: 13
                        }

                        StyledComboBox {
                            id: modeCombo
                            implicitWidth: 240
                            model: ["Por combinación de columnas", "Duplicados exactos (fila completa)"]
                        }

                        Text {
                            text: "Conservar como original:"
                            color: "#8b9fb2"
                            font.pixelSize: 13
                        }

                        StyledComboBox {
                            id: keepCombo
                            implicitWidth: 180
                            model: ["Primera ocurrencia", "Última ocurrencia", "Ninguna (descartar todas)"]
                        }

                        StyledCheckBox {
                            id: chkIgnoreCase
                            text: "Ignorar mayúsculas/minúsculas"
                            checked: true
                        }

                        StyledCheckBox {
                            id: chkIgnoreSpaces
                            text: "Ignorar espacios sobrantes"
                            checked: true
                        }
                    }

                    ColumnPicker {
                        id: colPicker
                        visible: modeCombo.currentIndex === 0
                        label: "Columnas clave para evaluar duplicados (si no marcas ninguna, se compara la fila completa):"
                        availableColumns: pageRoot.availableColumns
                    }
                }
            }

            // Tarjetas de conteo en pantalla
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Tabla: muestra los duplicados encontrados (o vista previa inicial)
            PreviewTable {
                title: (pageRoot.controller && pageRoot.controller.dupColumns && pageRoot.controller.dupColumns.length > 0)
                    ? "🗂️ Registros Duplicados Detectados (Con GRUPO_DUPLICADO y NUM_REPETICIONES)"
                    : "👁️ Vista Previa del Archivo de Entrada"
                columns: (pageRoot.controller && pageRoot.controller.dupColumns && pageRoot.controller.dupColumns.length > 0)
                    ? pageRoot.controller.dupColumns
                    : pageRoot.previewCols
                rows: (pageRoot.controller && pageRoot.controller.dupColumns && pageRoot.controller.dupColumns.length > 0)
                    ? pageRoot.controller.dupRows
                    : pageRoot.previewRows
                totalRows: (pageRoot.controller && pageRoot.controller.dupColumns && pageRoot.controller.dupColumns.length > 0)
                    ? pageRoot.controller.dupTotalRows
                    : pageRoot.previewTotal
                preferredTableHeight: 195
            }

            // Selector de formato de salida
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            // Acción y progreso
            ProgressCard {
                controller: pageRoot.controller
                primaryText: "🔍 Detectar Duplicados y Exportar Resultados"
                canExecute: fileSelector.filePath !== ""
                onExecuteClicked: {
                    var keepModes = ["first", "last", "none"]
                    var cols = modeCombo.currentIndex === 0 ? colPicker.selectedColumns : []
                    pageRoot.controller.analyzeAndExport(
                        fileSelector.filePath,
                        cols,
                        chkIgnoreCase.checked,
                        chkIgnoreSpaces.checked,
                        keepModes[keepCombo.currentIndex] || "first",
                        fileSelector.selectedSheet,
                        fileSelector.selectedDelimiter,
                        fileSelector.selectedEncoding,
                        fileSelector.inferTypes,
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

