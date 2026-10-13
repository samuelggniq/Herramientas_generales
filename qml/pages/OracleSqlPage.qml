import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: pageRoot
    property var controller: oracleSqlController

    // Mapa local de valores y tipos de parámetros bind (:param)
    property var paramValues: ({})
    property var paramTypes: ({})
    property string editingFavId: ""
    property string pendingDangerousKeywords: ""

    Connections {
        target: pageRoot.controller
        function onConfirmExecutionRequested(keywordsStr) {
            pageRoot.pendingDangerousKeywords = keywordsStr
            confirmDialog.open()
        }
        function onDetectedParamsChanged() {
            if (!pageRoot.controller) return
            var list = pageRoot.controller.detectedParams || []
            var vCopy = Object.assign({}, pageRoot.paramValues)
            var tCopy = Object.assign({}, pageRoot.paramTypes)
            for (var i = 0; i < list.length; i++) {
                var p = list[i]
                if (vCopy[p.name] === undefined || vCopy[p.name] === "") {
                    vCopy[p.name] = p.defaultValue || ""
                }
                tCopy[p.name] = p.type || "texto"
            }
            pageRoot.paramValues = vCopy
            pageRoot.paramTypes = tCopy
        }
    }

    function buildParamsPayload() {
        var payload = {}
        if (!controller) return payload
        var list = controller.detectedParams || []
        for (var i = 0; i < list.length; i++) {
            var pName = list[i].name
            payload[pName] = {
                "value": pageRoot.paramValues[pName] !== undefined ? String(pageRoot.paramValues[pName]) : "",
                "type": pageRoot.paramTypes[pName] || list[i].type || "texto"
            }
        }
        return payload
    }

    // Diálogo de confirmación para modo Solo Lectura
    Popup {
        id: confirmDialog
        modal: true
        focus: true
        anchors.centerIn: Overlay.overlay
        width: 460
        padding: 20

        background: Rectangle {
            radius: 16
            color: "#14212f"
            border.color: "#ef4444"
            border.width: 2
        }

        contentItem: ColumnLayout {
            spacing: 14

            Text {
                text: "⚠️ Advertencia de Modo Solo Lectura"
                color: "#ef4444"
                font.pixelSize: 17
                font.bold: true
            }

            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "La consulta contiene instrucciones que pueden modificar datos o estructuras en Oracle (" +
                      pageRoot.pendingDangerousKeywords + ").\n\n¿Estás seguro de que deseas ejecutar esta sentencia?"
                color: "#edf2f7"
                font.pixelSize: 13
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Item { Layout.fillWidth: true }

                ActionButton {
                    isPrimary: false
                    text: "Cancelar"
                    onClicked: confirmDialog.close()
                }

                ActionButton {
                    isPrimary: true
                    isDanger: true
                    text: "Sí, Ejecutar de todos modos"
                    onClicked: {
                        confirmDialog.close()
                        pageRoot.controller.executeQuery(
                            sqlTextArea.text,
                            pageRoot.buildParamsPayload(),
                            chkReadOnly.checked,
                            true
                        )
                    }
                }
            }
        }
    }

    // Selector rápido de Fecha (Popup Calendario / Selector AAAA-MM-DD)
    Popup {
        id: datePickerPopup
        property string targetParamName: ""
        modal: true
        focus: true
        anchors.centerIn: Overlay.overlay
        width: 320
        padding: 16

        background: Rectangle {
            radius: 14
            color: "#14212f"
            border.color: "#2d9cff"
            border.width: 1
        }

        function openForParam(pName) {
            targetParamName = pName
            var now = new Date()
            spinYear.value = now.getFullYear()
            spinMonth.value = now.getMonth() + 1
            spinDay.value = now.getDate()
            datePickerPopup.open()
        }

        contentItem: ColumnLayout {
            spacing: 12

            Text {
                text: "📅 Seleccionar Fecha para :" + datePickerPopup.targetParamName
                color: "#edf2f7"
                font.pixelSize: 14
                font.bold: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ColumnLayout {
                    Text { text: "Año"; color: "#8b9fb2"; font.pixelSize: 11 }
                    SpinBox {
                        id: spinYear
                        from: 1990
                        to: 2050
                        value: 2026
                        editable: true
                    }
                }
                ColumnLayout {
                    Text { text: "Mes"; color: "#8b9fb2"; font.pixelSize: 11 }
                    SpinBox {
                        id: spinMonth
                        from: 1
                        to: 12
                        value: 1
                        editable: true
                    }
                }
                ColumnLayout {
                    Text { text: "Día"; color: "#8b9fb2"; font.pixelSize: 11 }
                    SpinBox {
                        id: spinDay
                        from: 1
                        to: 31
                        value: 1
                        editable: true
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Item { Layout.fillWidth: true }

                ActionButton {
                    isPrimary: false
                    text: "Hoy"
                    implicitHeight: 32
                    onClicked: {
                        var d = new Date()
                        spinYear.value = d.getFullYear()
                        spinMonth.value = d.getMonth() + 1
                        spinDay.value = d.getDate()
                    }
                }

                ActionButton {
                    isPrimary: true
                    text: "Aplicar Fecha"
                    implicitHeight: 32
                    onClicked: {
                        var mm = ("0" + spinMonth.value).slice(-2)
                        var dd = ("0" + spinDay.value).slice(-2)
                        var formatted = spinYear.value + "-" + mm + "-" + dd
                        var copy = Object.assign({}, pageRoot.paramValues)
                        copy[datePickerPopup.targetParamName] = formatted
                        pageRoot.paramValues = copy
                        datePickerPopup.close()
                    }
                }
            }
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
                    text: "Oracle Database SQL"
                    color: "#edf2f7"
                    font.pixelSize: 26
                    font.bold: true
                }
                Text {
                    text: "Ejecutor seguro con credenciales desde .env, variables bind dinámicas (:param), consultas favoritas y exportación."
                    color: "#8b9fb2"
                    font.pixelSize: 13
                }
            }

            // 1. Tarjeta de Estado de Conexión (.env) — Sin campos de usuario ni contraseña
            ConnectionStatusCard {
                controller: pageRoot.controller
            }

            // 2. Panel dividido: Favoritas a la izquierda + Editor SQL a la derecha
            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                // Columna Izquierda: Consultas Favoritas
                ContentCard {
                    Layout.preferredWidth: 310
                    Layout.fillHeight: true
                    implicitHeight: 360

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Text {
                            text: "⭐ Consultas Favoritas"
                            color: "#edf2f7"
                            font.pixelSize: 15
                            font.bold: true
                        }

                        StyledTextField {
                            id: favSearchBox
                            Layout.fillWidth: true
                            implicitHeight: 32
                            placeholderText: "Buscar por nombre, descripción o SQL..."
                            onTextChanged: {
                                if (pageRoot.controller) pageRoot.controller.setFavoritesSearch(text)
                            }
                        }

                        ListView {
                            id: favListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 6
                            model: pageRoot.controller ? pageRoot.controller.favoritesList : []

                            Text {
                                anchors.centerIn: parent
                                visible: favListView.count === 0
                                text: "No hay consultas favoritas guardadas."
                                color: "#556e84"
                                font.pixelSize: 12
                            }

                            delegate: Rectangle {
                                width: favListView.width
                                implicitHeight: favItemCol.implicitHeight + 16
                                radius: 10
                                readonly property bool isCurrent: pageRoot.editingFavId === modelData.id
                                color: isCurrent ? "#1b3a5c" : "#0b151f"
                                border.color: isCurrent ? "#2d9cff" : "#1f3143"
                                border.width: 1

                                ColumnLayout {
                                    id: favItemCol
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 4

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text {
                                            text: String(modelData.name || "")
                                            color: "#ffffff"
                                            font.pixelSize: 13
                                            font.bold: true
                                            elide: Text.ElideRight
                                            Layout.fillWidth: true
                                        }
                                    }

                                    Text {
                                        visible: String(modelData.description || "") !== ""
                                        text: String(modelData.description || "")
                                        color: "#8b9fb2"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 4

                                        ActionButton {
                                            isPrimary: false
                                            text: "Cargar"
                                            implicitHeight: 24
                                            onClicked: {
                                                var loaded = pageRoot.controller.loadFavorite(modelData.id)
                                                if (loaded && loaded.sql !== undefined) {
                                                    pageRoot.editingFavId = loaded.id
                                                    favNameInput.text = loaded.name || ""
                                                    favDescInput.text = loaded.description || ""
                                                    sqlTextArea.text = loaded.sql || ""
                                                }
                                            }
                                        }

                                        ActionButton {
                                            isPrimary: false
                                            text: "Duplicar"
                                            implicitHeight: 24
                                            onClicked: pageRoot.controller.duplicateFavorite(modelData.id)
                                        }

                                        ActionButton {
                                            isPrimary: false
                                            text: "Eliminar"
                                            implicitHeight: 24
                                            onClicked: {
                                                if (pageRoot.editingFavId === modelData.id) {
                                                    pageRoot.editingFavId = ""
                                                }
                                                pageRoot.controller.deleteFavorite(modelData.id)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Formulario compacto para guardar/editar favorita
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: "#1f3143"
                        }

                        StyledTextField {
                            id: favNameInput
                            Layout.fillWidth: true
                            implicitHeight: 32
                            placeholderText: "Nombre de la favorita..."
                        }

                        StyledTextField {
                            id: favDescInput
                            Layout.fillWidth: true
                            implicitHeight: 32
                            placeholderText: "Descripción corta (opcional)..."
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            ActionButton {
                                isPrimary: false
                                text: pageRoot.editingFavId !== "" ? "💾 Actualizar" : "⭐ Guardar Nueva"
                                Layout.fillWidth: true
                                implicitHeight: 32
                                enabled: favNameInput.text.trim().length > 0 && sqlTextArea.text.trim().length > 0
                                onClicked: {
                                    pageRoot.controller.saveFavorite(
                                        favNameInput.text.trim(),
                                        favDescInput.text.trim(),
                                        sqlTextArea.text,
                                        pageRoot.paramTypes,
                                        pageRoot.editingFavId
                                    )
                                }
                            }

                            ActionButton {
                                visible: pageRoot.editingFavId !== ""
                                isPrimary: false
                                text: "Nueva"
                                implicitHeight: 32
                                onClicked: {
                                    pageRoot.editingFavId = ""
                                    favNameInput.text = ""
                                    favDescInput.text = ""
                                }
                            }
                        }
                    }
                }

                // Columna Derecha: Editor SQL + Parámetros Bind (:param)
                ContentCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    implicitHeight: 360

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: "💬 Editor de Consulta SQL"
                                color: "#edf2f7"
                                font.pixelSize: 15
                                font.bold: true
                                Layout.fillWidth: true
                            }

                            StyledCheckBox {
                                id: chkReadOnly
                                text: "Modo solo lectura (advertir en DML/DDL)"
                                checked: true
                            }

                            ActionButton {
                                isPrimary: false
                                text: "Limpiar"
                                implicitHeight: 30
                                enabled: sqlTextArea.text.trim().length > 0
                                onClicked: {
                                    sqlTextArea.text = ""
                                    pageRoot.editingFavId = ""
                                }
                            }
                        }

                        // Snippets rápidos con soporte de parámetros bind
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text { text: "Snippets:"; color: "#556e84"; font.pixelSize: 12 }

                            QueryChip {
                                chipText: "SELECT * FROM dual"
                                onClicked: sqlTextArea.text = "SELECT SYSDATE AS FECHA_SERVIDOR, USER AS USUARIO_CONECTADO FROM DUAL"
                            }

                            QueryChip {
                                chipText: "FETCH FIRST 100 ROWS"
                                onClicked: sqlTextArea.text += "\nFETCH FIRST 100 ROWS ONLY"
                            }

                            Item { Layout.fillWidth: true }
                        }

                        // Área de texto monoespaciada
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 130
                            clip: true

                            background: Rectangle {
                                radius: 10
                                color: "#0b151f"
                                border.color: sqlTextArea.activeFocus ? "#2d9cff" : "#1f3143"
                                border.width: sqlTextArea.activeFocus ? 2 : 1
                            }

                            TextArea {
                                id: sqlTextArea
                                selectByMouse: true
                                wrapMode: TextArea.NoWrap
                                color: "#edf2f7"
                                font.family: "Consolas, Courier New, monospace"
                                font.pixelSize: 13
                                leftPadding: 12
                                rightPadding: 12
                                topPadding: 10
                                bottomPadding: 10
                                placeholderText: "-- Escribe tu consulta SQL usando parámetros bind (:fecha_inicio, :codigo)\nSELECT * FROM DUAL"
                                placeholderTextColor: "#556e84"
                                background: null
                                onTextChanged: {
                                    if (pageRoot.controller) {
                                        pageRoot.controller.inspectSqlParams(text)
                                    }
                                }
                            }
                        }

                        // Botón Ejecutar Consulta
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ActionButton {
                                isPrimary: true
                                text: "▶  Ejecutar Consulta en Oracle"
                                Layout.fillWidth: true
                                implicitHeight: 42
                                enabled: sqlTextArea.text.trim().length > 0 && (!pageRoot.controller || !pageRoot.controller.isBusy)
                                onClicked: {
                                    pageRoot.controller.executeQuery(
                                        sqlTextArea.text,
                                        pageRoot.buildParamsPayload(),
                                        chkReadOnly.checked,
                                        false
                                    )
                                }
                            }

                            ActionButton {
                                visible: pageRoot.controller && pageRoot.controller.isBusy
                                isPrimary: false
                                isDanger: true
                                text: "⏹ Cancelar"
                                implicitHeight: 42
                                onClicked: pageRoot.controller.cancelTask()
                            }
                        }
                    }
                }
            }

            // Tarjetas de resumen del resultado SQL
            ResultSummaryCards {
                cards: pageRoot.controller ? pageRoot.controller.summaryCards : []
            }

            // Vista previa del resultado SQL
            PreviewTable {
                title: "👁️ Vista Previa del Resultado SQL (Primeras 50 filas)"
                columns: pageRoot.controller ? pageRoot.controller.previewColumns : []
                rows: pageRoot.controller ? pageRoot.controller.previewRows : []
                totalRows: pageRoot.controller ? pageRoot.controller.previewTotalRows : 0
                preferredTableHeight: 190
            }

            // Exportación del resultado a Excel o CSV
            OutputFormatSelector {
                id: outFormat
                controller: pageRoot.controller
            }

            ProgressCard {
                controller: pageRoot.controller
                primaryText: "💾 Exportar Resultado de la Consulta"
                canExecute: pageRoot.controller && pageRoot.controller.hasQueryResult
                onExecuteClicked: {
                    pageRoot.controller.exportResult(
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

