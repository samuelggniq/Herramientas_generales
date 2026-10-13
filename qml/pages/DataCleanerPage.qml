import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: dataCleanerController
    property var availableColumns: []

    function buildRulesPayload() {
        var caseModes = ["upper", "lower", "title"]
        var dateFormats = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
        var emptyModes = ["na", "zero", "custom", "null"]
        return {
            "target_columns": colPicker.selectedColumns,
            "trim_spaces": chkTrim.checked,
            "normalize_case": chkCase.checked,
            "case_mode": caseModes[comboCase.currentIndex] || "upper",
            "remove_duplicates": chkDedup.checked,
            "duplicate_columns": colPicker.selectedColumns,
            "unify_dates": chkDates.checked,
            "date_output_format": dateFormats[comboDateFmt.currentIndex] || "%Y-%m-%d",
            "replace_empties": chkEmpties.checked,
            "empty_replacement_mode": emptyModes[comboEmptyMode.currentIndex] || "na",
            "empty_custom_value": txtCustomEmpty.text,
            "treat_placeholders_as_empty": chkPlaceholders.checked,
            "remove_weird_chars": chkWeird.checked,
            "strip_accents": chkAccents.checked
        }
    }

    function applyProfileData(data) {
        if (!data) return
        if (data.trim_spaces !== undefined) chkTrim.checked = data.trim_spaces
        if (data.normalize_case !== undefined) chkCase.checked = data.normalize_case
        if (data.case_mode === "lower") comboCase.currentIndex = 1
        else if (data.case_mode === "title") comboCase.currentIndex = 2
        else comboCase.currentIndex = 0

        if (data.remove_duplicates !== undefined) chkDedup.checked = data.remove_duplicates
        if (data.unify_dates !== undefined) chkDates.checked = data.unify_dates
        if (data.date_output_format === "%d/%m/%Y") comboDateFmt.currentIndex = 1
        else if (data.date_output_format === "%Y/%m/%d") comboDateFmt.currentIndex = 2
        else comboDateFmt.currentIndex = 0

        if (data.replace_empties !== undefined) chkEmpties.checked = data.replace_empties
        if (data.empty_replacement_mode === "zero") comboEmptyMode.currentIndex = 1
        else if (data.empty_replacement_mode === "custom") comboEmptyMode.currentIndex = 2
        else if (data.empty_replacement_mode === "null") comboEmptyMode.currentIndex = 3
        else comboEmptyMode.currentIndex = 0

        if (data.empty_custom_value !== undefined) txtCustomEmpty.text = data.empty_custom_value
        if (data.treat_placeholders_as_empty !== undefined) chkPlaceholders.checked = data.treat_placeholders_as_empty
        if (data.remove_weird_chars !== undefined) chkWeird.checked = data.remove_weird_chars
        if (data.strip_accents !== undefined) chkAccents.checked = data.strip_accents
    }

    function loadFileColumns() {
        if (!controller || !fileSelector.filePath) {
            availableColumns = []
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
            controller.generatePreview(
                fileSelector.filePath,
                fileSelector.selectedSheet,
                fileSelector.selectedDelimiter,
                fileSelector.selectedEncoding,
                fileSelector.inferTypes,
                buildRulesPayload()
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
                    text: "Limpiador de Datos con Reglas"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Aplica reglas de normalización, previsualiza el impacto 'Antes ⇒ Después' y guarda perfiles reutilizables."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // Archivo de entrada
            FileDropField {
                id: fileSelector
                title: "📂 Archivo a Limpiar"
                controller: pageRoot.controller
                onConfigurationChanged: pageRoot.loadFileColumns()
            }

            // Tarjeta de Reglas y Perfiles
            ContentCard {
                Layout.fillWidth: true
                implicitHeight: rulesCol.implicitHeight + 28

                ColumnLayout {
                    id: rulesCol
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    // Barra de perfiles JSON
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: "⚙️ Reglas de Limpieza"
                            color: "#edf2f7"
                            font.pixelSize: 15
                            font.bold: true
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: "Perfil:"
                            color: "#8b9fb2"
                            font.pixelSize: 12
                        }

                        StyledComboBox {
                            id: profileCombo
                            implicitWidth: 165
                            implicitHeight: 32
                            model: pageRoot.controller ? pageRoot.controller.profileNames : []
                        }

                        ActionButton {
                            isPrimary: false
                            text: "Cargar"
                            implicitHeight: 32
                            enabled: profileCombo.currentText !== ""
                            onClicked: {
                                var d = pageRoot.controller.loadProfile(profileCombo.currentText)
                                pageRoot.applyProfileData(d)
                            }
                        }

                        ActionButton {
                            isPrimary: false
                            text: "Eliminar"
                            implicitHeight: 32
                            enabled: profileCombo.currentText !== ""
                            onClicked: pageRoot.controller.deleteProfile(profileCombo.currentText)
                        }

                        StyledTextField {
                            id: newProfileName
                            implicitWidth: 155
                            implicitHeight: 32
                            placeholderText: "Ej: Catálogo semanal"
                        }

                        ActionButton {
                            isPrimary: false
                            text: "💾 Guardar perfil"
                            implicitHeight: 32
                            enabled: newProfileName.text.trim().length > 0
                            onClicked: {
                                pageRoot.controller.saveProfile(newProfileName.text.trim(), pageRoot.buildRulesPayload())
                                newProfileName.text = ""
                            }
                        }
                    }

                    // Selector de columnas objetivo (vacío = todas)
                    ColumnPicker {
                        id: colPicker
                        label: "Columnas donde aplicar (si no eliges ninguna, se aplica a TODAS):"
                        availableColumns: pageRoot.availableColumns
                    }

                    // Cuadrícula de las 6 reglas
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 18
                        rowSpacing: 8

                        StyledCheckBox {
                            id: chkTrim
                            text: "1. Quitar espacios sobrantes (inicio, fin y dobles internos)"
                            checked: true
                        }

                        RowLayout {
                            spacing: 8
                            StyledCheckBox {
                                id: chkCase
                                text: "2. Normalizar mayúsculas:"
                                checked: false
                            }
                            StyledComboBox {
                                id: comboCase
                                implicitWidth: 145
                                implicitHeight: 32
                                enabled: chkCase.checked
                                model: ["MAYÚSCULAS", "minúsculas", "Tipo Título"]
                            }
                        }

                        StyledCheckBox {
                            id: chkDedup
                            text: "3. Eliminar filas duplicadas (exactas o por columnas elegidas)"
                            checked: false
                        }

                        RowLayout {
                            spacing: 8
                            StyledCheckBox {
                                id: chkDates
                                text: "4. Unificar fechas a:"
                                checked: false
                            }
                            StyledComboBox {
                                id: comboDateFmt
                                implicitWidth: 145
                                implicitHeight: 32
                                enabled: chkDates.checked
                                model: ["AAAA-MM-DD", "DD/MM/AAAA", "AAAA/MM/DD"]
                            }
                        }

                        RowLayout {
                            spacing: 6
                            StyledCheckBox {
                                id: chkEmpties
                                text: "5. Reemplazar vacíos:"
                                checked: false
                            }
                            StyledComboBox {
                                id: comboEmptyMode
                                implicitWidth: 125
                                implicitHeight: 32
                                enabled: chkEmpties.checked
                                model: ["\"N/A\"", "0", "Texto fijo", "Dejar nulo"]
                            }
                            StyledTextField {
                                id: txtCustomEmpty
                                implicitWidth: 110
                                implicitHeight: 32
                                visible: chkEmpties.checked && comboEmptyMode.currentIndex === 2
                                placeholderText: "Valor fijo..."
                                text: "SIN DATO"
                            }
                            StyledCheckBox {
                                id: chkPlaceholders
                                enabled: chkEmpties.checked
                                checked: true
                                text: "Tratar NULL/N/A/- como vacío"
                            }
                        }

                        RowLayout {
                            spacing: 8
                            StyledCheckBox {
                                id: chkWeird
                                text: "6. Quitar caracteres de control / no imprimibles"
                                checked: false
                            }
                            StyledCheckBox {
                                id: chkAccents
                                text: "Quitar acentos"
                                checked: false
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Item { Layout.fillWidth: true }
                        ActionButton {
                            isPrimary: false
                            text: "👁️ Actualizar Vista Previa 'Antes ⇒ Después'"
                            enabled: fileSelector.filePath !== "" && (!pageRoot.controller || !pageRoot.controller.isBusy)
                            onClicked: {
                                pageRoot.controller.generatePreview(
                                    fileSelector.filePath,
                                    fileSelector.selectedSheet,
                                    fileSelector.selectedDelimiter,
                                    fileSelector.selectedEncoding,
                                    fileSelector.inferTypes,
                                    pageRoot.buildRulesPayload()
                                )
                            }
                        }
                    }
                }
            }

            // Resumen de impacto
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Desglose por regla
            ContentCard {
                Layout.fillWidth: true
                visible: pageRoot.controller && pageRoot.controller.ruleImpacts && pageRoot.controller.ruleImpacts.length > 0
                implicitHeight: impactFlow.implicitHeight + 24

                Flow {
                    id: impactFlow
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Repeater {
                        model: pageRoot.controller ? pageRoot.controller.ruleImpacts : []
                        Rectangle {
                            radius: 8
                            color: "#0b151f"
                            border.color: modelData.cellsChanged > 0 ? "#2d9cff" : "#1f3143"
                            implicitWidth: impLabel.implicitWidth + 20
                            implicitHeight: 28

                            Text {
                                id: impLabel
                                anchors.centerIn: parent
                                text: modelData.ruleName + ": " + modelData.cellsChanged + " celdas (" + modelData.rowsAffected + " filas)"
                                color: modelData.cellsChanged > 0 ? "#edf2f7" : "#8b9fb2"
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }

            // Vista previa Antes / Después
            PreviewTable {
                title: "👁️ Vista Previa Antes ⇒ Después (Celdas modificadas muestran: valor_anterior ⇒ valor_nuevo)"
                columns: pageRoot.controller ? pageRoot.controller.previewColumns : []
                rows: pageRoot.controller ? pageRoot.controller.previewRows : []
                totalRows: pageRoot.controller ? pageRoot.controller.previewTotalRows : 0
                preferredTableHeight: 195
                columnWidth: 185
            }

            // Selector de formato de salida
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            // Acción principal: Aplicar y Guardar
            ProgressCard {
                controller: pageRoot.controller
                primaryText: "✨ Aplicar Reglas y Guardar"
                canExecute: fileSelector.filePath !== ""
                onExecuteClicked: {
                    pageRoot.controller.applyAndSave(
                        fileSelector.filePath,
                        fileSelector.selectedSheet,
                        fileSelector.selectedDelimiter,
                        fileSelector.selectedEncoding,
                        fileSelector.inferTypes,
                        pageRoot.buildRulesPayload(),
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

