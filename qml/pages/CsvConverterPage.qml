import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: csvConverterController

    property var previewCols: []
    property var previewRows: []
    property int previewTotalRows: 0

    function refreshPreview() {
        if (!controller || !fileSelector.filePath) {
            previewCols = []
            previewRows = []
            previewTotalRows = 0
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
            previewCols = prev.columns
            previewRows = prev.rows
            previewTotalRows = prev.totalRows
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
                    text: "Conversión CSV a XLSX"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Transforma uno o varios archivos CSV/Excel en libros XLSX con formato corporativo o CSV normalizado."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // Selección de archivos (soporta lote)
            FileDropField {
                id: fileSelector
                title: "📂 Archivo(s) de Origen (Individual o Lote)"
                placeholder: "Selecciona o arrastra uno o varios archivos .csv, .tsv, .xlsx..."
                controller: pageRoot.controller
                allowMultiple: true
                onConfigurationChanged: pageRoot.refreshPreview()
            }

            // Tarjetas resumen del último lote
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Tabla de vista previa
            PreviewTable {
                title: fileSelector.selectedFiles.length > 1
                    ? ("👁️ Vista Previa (Primer archivo del lote — +" + (fileSelector.selectedFiles.length - 1) + " más)")
                    : "👁️ Vista Previa de Datos (Primeras 50 filas)"
                columns: pageRoot.previewCols
                rows: pageRoot.previewRows
                totalRows: pageRoot.previewTotalRows
                preferredTableHeight: 190
            }

            // Selector de formato de salida (Excel .xlsx o CSV)
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            // Barra de acción y progreso
            ProgressCard {
                controller: pageRoot.controller
                primaryText: fileSelector.selectedFiles.length > 1
                    ? ("Convertir Lote (" + fileSelector.selectedFiles.length + " archivos)")
                    : "Convertir y Exportar"
                canExecute: fileSelector.selectedFiles.length > 0
                onExecuteClicked: {
                    pageRoot.controller.convertFiles(
                        fileSelector.selectedFiles,
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

            // Registro de actividad
            LogPanel {
                preferredLogHeight: 150
            }
        }
    }
}

