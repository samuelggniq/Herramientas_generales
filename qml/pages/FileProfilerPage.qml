import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: fileProfilerController

    function triggerAutoProfile() {
        if (controller && fileSelector.filePath !== "" && !controller.isBusy) {
            controller.runProfile(
                fileSelector.filePath,
                fileSelector.selectedSheet,
                fileSelector.selectedDelimiter,
                fileSelector.selectedEncoding,
                fileSelector.inferTypes
            )
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
                    text: "Perfilado Rápido de Archivo"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Analiza automáticamente tipos de datos, porcentaje de nulos, valores únicos, extremos y alertas de calidad."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // Selección de archivo (dispara perfilado automático al cargar o cambiar opciones)
            FileDropField {
                id: fileSelector
                title: "📂 Archivo a Analizar (Ejecución Automática)"
                controller: pageRoot.controller
                onConfigurationChanged: pageRoot.triggerAutoProfile()
            }

            // Tarjetas de resumen
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Tarjeta de Alertas Visuales de Calidad
            ContentCard {
                Layout.fillWidth: true
                visible: pageRoot.controller && pageRoot.controller.alerts && pageRoot.controller.alerts.length > 0
                implicitHeight: alertsCol.implicitHeight + 24

                ColumnLayout {
                    id: alertsCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Text {
                        text: "🚨 Alertas de Calidad Detectadas"
                        color: "#f59e0b"
                        font.pixelSize: 14
                        font.bold: true
                    }

                    Repeater {
                        model: pageRoot.controller ? pageRoot.controller.alerts : []
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: alertRow.implicitHeight + 14
                            radius: 8
                            color: modelData.level === "danger" ? "#2c161e" : (modelData.level === "warning" ? "#2b2213" : "#122436")
                            border.color: modelData.level === "danger" ? "#ef4444" : (modelData.level === "warning" ? "#f59e0b" : "#2d9cff")
                            border.width: 1

                            RowLayout {
                                id: alertRow
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8

                                Text {
                                    text: modelData.icon || "⚠️"
                                    font.pixelSize: 14
                                }

                                Text {
                                    text: modelData.title + ":"
                                    color: "#ffffff"
                                    font.pixelSize: 12
                                    font.bold: true
                                }

                                Text {
                                    text: modelData.detail
                                    color: "#edf2f7"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }

            // Tabla de perfilado por columna (ordenable y con colores sutiles para % de nulos en índice 2)
            PreviewTable {
                title: "🔍 Diagnóstico por Columna (Clic en encabezado para ordenar)"
                columns: pageRoot.controller ? pageRoot.controller.tableColumns : []
                rows: pageRoot.controller ? pageRoot.controller.tableRows : []
                totalRows: pageRoot.controller && pageRoot.controller.tableRows ? pageRoot.controller.tableRows.length : 0
                preferredTableHeight: 220
                columnWidth: 165
                sortable: true
                highlightNullColIndex: 2
            }

            // Formato de salida para exportar el perfil
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            // Barra de acción / progreso para re-analizar o exportar
            ProgressCard {
                controller: pageRoot.controller
                primaryText: "💾 Exportar Reporte de Perfilado"
                canExecute: pageRoot.controller && pageRoot.controller.hasProfile
                onExecuteClicked: {
                    pageRoot.controller.exportProfile(
                        outFormat.outputFormat,
                        outFormat.csvDelimiter,
                        outFormat.csvEncoding
                    )
                }
            }

            // Panel de logs
            LogPanel {
                preferredLogHeight: 145
            }
        }
    }
}

