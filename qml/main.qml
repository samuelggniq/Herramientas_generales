import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root

    visible: true
    width: 960
    height: 720
    minimumWidth: 860
    minimumHeight: 620
    title: "Sistema Maestro de Herramientas"

    //--------------------------------------------------
    // Paleta de Colores y Tokens de Diseño
    //--------------------------------------------------
    readonly property color cBackground: "#081119"
    readonly property color cSidebar: "#0e1823"
    readonly property color cSidebarItemHover: "#162536"
    readonly property color cSidebarActive: "#1b2e42"
    readonly property color cCard: "#14212f"
    readonly property color cCardHover: "#18283a"
    readonly property color cCardDropTarget: "#1e3852"
    readonly property color cField: "#0b151f"
    readonly property color cBorder: "#1f3143"
    readonly property color cBorderHover: "#2d445d"
    readonly property color cBorderFocus: "#2d9cff"
    
    readonly property color cPrimary: "#2d9cff"
    readonly property color cPrimaryHover: "#48aaff"
    readonly property color cPrimaryPressed: "#1a84e2"
    readonly property color cSecondary: "#1d2e40"
    readonly property color cSecondaryHover: "#263b52"
    
    readonly property color cText: "#edf2f7"
    readonly property color cTextMuted: "#8b9fb2"
    readonly property color cTextDim: "#556e84"
    readonly property color cSuccess: "#10b981"
    readonly property color cWarning: "#f59e0b"
    readonly property color cDanger: "#ef4444"

    // Estado global de navegación
    property int currentPage: 0

    //--------------------------------------------------
    // Señales públicas para conexión con backend (Python)
    //--------------------------------------------------
    signal convertCsvRequested(string filePath)
    signal executeQueryRequested(string query)

    //--------------------------------------------------
    // Funciones de utilidad para UI y Backend
    //--------------------------------------------------
    function appendLog(message, type) {
        var now = new Date()
        var timeStr = ("0" + now.getHours()).slice(-2) + ":" +
                      ("0" + now.getMinutes()).slice(-2) + ":" +
                      ("0" + now.getSeconds()).slice(-2)
        var prefix = "[" + timeStr + "] "
        if (type === "error") {
            prefix += "❌ ERROR: "
        } else if (type === "success") {
            prefix += "✅ OK: "
        } else if (type === "info") {
            prefix += "ℹ️ INFO: "
        }
        
        if (logTextArea.text.length > 0) {
            logTextArea.text += "\n" + prefix + message
        } else {
            logTextArea.text = prefix + message
        }
        
        // Auto-scroll al final
        logScrollView.ScrollBar.vertical.position = 1.0 - logScrollView.ScrollBar.vertical.size
    }

    function clearLogs() {
        logTextArea.text = ""
        showToast("Registro de actividad limpiado")
    }

    function showToast(message) {
        toastNotification.message = message
        toastNotification.visible = true
        toastTimer.restart()
    }

    function copyToClipboard(textToCopy) {
        clipboardHelper.text = textToCopy
        clipboardHelper.selectAll()
        clipboardHelper.copy()
        showToast("Copiado al portapapeles")
    }

    function cleanFileUrl(rawUrl) {
        var str = rawUrl.toString()
        if (str.indexOf("file:///") === 0) {
            str = str.substring(8) // Windows file:///C:/path -> C:/path
        } else if (str.indexOf("file://") === 0) {
            str = str.substring(7)
        }
        return decodeURIComponent(str)
    }

    // Elemento auxiliar invisible para copiar texto al portapapeles
    TextEdit {
        id: clipboardHelper
        visible: false
    }

    // Diálogo nativo para selección de archivos CSV
    FileDialog {
        id: csvFileDialog
        title: "Seleccionar archivo CSV"
        nameFilters: ["Archivos CSV (*.csv)", "Archivos de texto (*.txt)", "Todos los archivos (*.*)"]
        fileMode: FileDialog.OpenFile
        onAccepted: {
            var path = root.cleanFileUrl(selectedFile)
            csvPathInput.text = path
            root.appendLog("Archivo seleccionado: " + path, "info")
            root.showToast("Archivo CSV cargado")
        }
    }

    color: cBackground

    //--------------------------------------------------
    // Componentes Reutilizables (Modern Qt 6 Components)
    //--------------------------------------------------

    // Botón Primario
    component PrimaryButton: Button {
        id: pBtn
        implicitHeight: 46
        hoverEnabled: true

        background: Rectangle {
            radius: 12
            color: !pBtn.enabled ? "#1c2836" : (pBtn.down ? root.cPrimaryPressed : (pBtn.hovered ? root.cPrimaryHover : root.cPrimary))
            Behavior on color { ColorAnimation { duration: 150 } }
        }

        contentItem: Text {
            text: pBtn.text
            color: !pBtn.enabled ? root.cTextDim : "#ffffff"
            font.pixelSize: 15
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: pBtn.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            acceptedButtons: Qt.NoButton
        }
    }

    // Botón Secundario / Outline
    component SecondaryButton: Button {
        id: sBtn
        implicitHeight: 38
        hoverEnabled: true

        background: Rectangle {
            radius: 10
            color: !sBtn.enabled ? "#131e2b" : (sBtn.down ? "#1c2d3f" : (sBtn.hovered ? root.cSecondaryHover : root.cSecondary))
            border.color: sBtn.hovered ? root.cPrimary : root.cBorder
            border.width: 1
            Behavior on color { ColorAnimation { duration: 150 } }
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }

        contentItem: Text {
            text: sBtn.text
            color: !sBtn.enabled ? root.cTextDim : (sBtn.hovered ? "#ffffff" : root.cTextMuted)
            font.pixelSize: 13
            font.bold: false
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: sBtn.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            acceptedButtons: Qt.NoButton
        }
    }

    // Campo de texto estilizado
    component StyledTextField: TextField {
        id: sField
        implicitHeight: 44
        color: root.cText
        placeholderTextColor: root.cTextDim
        font.pixelSize: 14
        verticalAlignment: Text.AlignVCenter
        leftPadding: 14
        rightPadding: 14
        selectByMouse: true

        background: Rectangle {
            radius: 12
            color: root.cField
            border.color: sField.activeFocus ? root.cBorderFocus : root.cBorder
            border.width: sField.activeFocus ? 2 : 1
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }
    }

    // Tarjeta contenedora
    component ContentCard: Rectangle {
        radius: 20
        color: root.cCard
        border.color: root.cBorder
        border.width: 1
    }

    // Chip / Snippet interactivo
    component QueryChip: Rectangle {
        id: chip
        property string chipText: ""
        signal clicked()

        implicitWidth: chipLabel.implicitWidth + 20
        implicitHeight: 30
        radius: 15
        color: chipMouse.containsMouse ? root.cPrimaryHover : root.cSecondary
        border.color: chipMouse.containsMouse ? root.cPrimary : root.cBorder
        border.width: 1
        Behavior on color { ColorAnimation { duration: 120 } }

        Text {
            id: chipLabel
            anchors.centerIn: parent
            text: chip.chipText
            font.pixelSize: 12
            font.family: "Consolas, Courier New, monospace"
            color: chipMouse.containsMouse ? "#ffffff" : root.cTextMuted
        }

        MouseArea {
            id: chipMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: chip.clicked()
        }
    }

    //--------------------------------------------------
    // Layout Principal
    //--------------------------------------------------
    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 18

        //--------------------------------------------------
        // SIDEBAR
        //--------------------------------------------------
        Rectangle {
            Layout.preferredWidth: 260
            Layout.fillHeight: true

            radius: 24
            color: cSidebar
            border.color: cBorder
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                // Cabecera / Identidad
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 6
                    Layout.bottomMargin: 10
                    spacing: 12

                    Rectangle {
                        width: 44
                        height: 44
                        radius: 12
                        color: Qt.rgba(45/255, 156/255, 255/255, 0.15)
                        border.color: Qt.rgba(45/255, 156/255, 255/255, 0.4)
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: "⚡"
                            font.pixelSize: 22
                        }
                    }

                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: "Toolbox Pro"
                            color: cText
                            font.pixelSize: 18
                            font.bold: true
                        }
                        Text {
                            text: "Herramientas Generales"
                            color: cTextMuted
                            font.pixelSize: 12
                        }
                    }
                }

                // Separador sutil
                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: cBorder
                    Layout.bottomMargin: 8
                }

                // Elementos de navegación del Sidebar generados dinámicamente
                Repeater {
                    model: [
                        { pageIndex: 0, title: "Conversión CSV", subtitle: "A formato XLSX", icon: "📊", isEnabled: true, badge: "" },
                        { pageIndex: 1, title: "Oracle SQL", subtitle: "Consultas y exportación", icon: "🗄️", isEnabled: true, badge: "" },
                        { pageIndex: 2, title: "SharePoint", subtitle: "Gestión documental", icon: "📁", isEnabled: false, badge: "Pronto" },
                        { pageIndex: 3, title: "Traducciones", subtitle: "Motor de textos", icon: "🌐", isEnabled: false, badge: "Pronto" }
                    ]

                    Rectangle {
                        id: navItem
                        Layout.fillWidth: true
                        implicitHeight: 56
                        radius: 14

                        readonly property bool isSelected: root.currentPage === modelData.pageIndex
                        readonly property bool isItemEnabled: modelData.isEnabled

                        color: !isItemEnabled
                               ? "transparent"
                               : (isSelected
                                  ? Qt.rgba(45/255, 156/255, 255/255, 0.18)
                                  : (navMouse.containsMouse ? root.cSidebarItemHover : "transparent"))

                        border.color: isSelected ? Qt.rgba(45/255, 156/255, 255/255, 0.35) : "transparent"
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: 150 } }
                        Behavior on border.color { ColorAnimation { duration: 150 } }

                        // Indicador de selección lateral izquierdo
                        Rectangle {
                            width: 4
                            height: 24
                            radius: 2
                            color: root.cPrimary
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            visible: navItem.isSelected
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 12
                            spacing: 12

                            Text {
                                text: modelData.icon
                                font.pixelSize: 18
                                opacity: navItem.isItemEnabled ? 1.0 : 0.4
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    text: modelData.title
                                    color: !navItem.isItemEnabled ? root.cTextDim : (navItem.isSelected ? "#ffffff" : root.cText)
                                    font.pixelSize: 14
                                    font.bold: navItem.isSelected
                                }

                                Text {
                                    text: modelData.subtitle
                                    color: !navItem.isItemEnabled ? root.cTextDim : root.cTextMuted
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            // Badge opcional (ej: "Pronto")
                            Rectangle {
                                visible: modelData.badge !== ""
                                implicitWidth: badgeText.implicitWidth + 10
                                implicitHeight: 20
                                radius: 10
                                color: "#192433"
                                border.color: root.cBorder
                                border.width: 1

                                Text {
                                    id: badgeText
                                    anchors.centerIn: parent
                                    text: modelData.badge
                                    color: root.cTextDim
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                            }
                        }

                        MouseArea {
                            id: navMouse
                            anchors.fill: parent
                            hoverEnabled: navItem.isItemEnabled
                            cursorShape: navItem.isItemEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (navItem.isItemEnabled) {
                                    root.currentPage = modelData.pageIndex
                                }
                            }
                        }
                    }
                }

                // Espaciador flexible
                Item {
                    Layout.fillHeight: true
                }

                // Pie del Sidebar: Estado del Sistema
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 44
                    radius: 12
                    color: Qt.rgba(11/255, 21/255, 31/255, 0.6)
                    border.color: cBorder
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.cSuccess
                        }

                        Text {
                            text: "Sistema Listo"
                            color: root.cTextMuted
                            font.pixelSize: 12
                            Layout.fillWidth: true
                        }

                        Text {
                            text: "v1.2"
                            color: root.cTextDim
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }

        //--------------------------------------------------
        // CONTENEDOR DE PÁGINAS PRINCIPALES
        //--------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true

            radius: 24
            color: cSidebar
            border.color: cBorder
            border.width: 1
            clip: true

            StackLayout {
                anchors.fill: parent
                currentIndex: currentPage

                //==================================================
                // PÁGINA 1: CONVERSIÓN CSV -> XLSX
                //==================================================
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        // Encabezado de la página
                        ColumnLayout {
                            spacing: 4

                            Text {
                                text: "Conversión CSV a XLSX"
                                color: cText
                                font.pixelSize: 28
                                font.bold: true
                            }

                            Text {
                                text: "Transforma archivos delimitados por comas o punto y coma en libros de Excel con detección inteligente."
                                color: cTextMuted
                                font.pixelSize: 13
                            }
                        }

                        // Tarjeta: Selección de Archivo y Drag & Drop
                        ContentCard {
                            id: csvCard
                            Layout.fillWidth: true
                            implicitHeight: 180

                            // Estado visual de arrastre de archivo
                            property bool isDraggingOver: false

                            color: isDraggingOver ? root.cCardDropTarget : root.cCard
                            border.color: isDraggingOver ? root.cPrimary : root.cBorder
                            border.width: isDraggingOver ? 2 : 1
                            Behavior on color { ColorAnimation { duration: 150 } }
                            Behavior on border.color { ColorAnimation { duration: 150 } }

                            // Área para soltar archivos arrastrados desde el explorador
                            DropArea {
                                anchors.fill: parent
                                onEntered: (drag) => {
                                    if (drag.hasUrls) {
                                        drag.accept()
                                        csvCard.isDraggingOver = true
                                    }
                                }
                                onExited: {
                                    csvCard.isDraggingOver = false
                                }
                                onDropped: (drop) => {
                                    csvCard.isDraggingOver = false
                                    if (drop.hasUrls && drop.urls.length > 0) {
                                        var path = root.cleanFileUrl(drop.urls[0])
                                        csvPathInput.text = path
                                        root.appendLog("Archivo arrastrado: " + path, "info")
                                        root.showToast("Archivo detectado correctamente")
                                    }
                                }
                            }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 14

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: "📂 Archivo CSV de Origen"
                                        color: cText
                                        font.pixelSize: 16
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: csvCard.isDraggingOver ? "¡Suelta el archivo aquí!" : "Puedes arrastrar y soltar el archivo"
                                        color: csvCard.isDraggingOver ? root.cPrimary : root.cTextDim
                                        font.pixelSize: 12
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    StyledTextField {
                                        id: csvPathInput
                                        Layout.fillWidth: true
                                        placeholderText: "Selecciona o arrastra un archivo .csv..."

                                        // Botón para borrar ruta si hay texto
                                        Rectangle {
                                            anchors.right: parent.right
                                            anchors.rightMargin: 10
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: 22
                                            height: 22
                                            radius: 11
                                            color: clearMouse.containsMouse ? "#2d445d" : "transparent"
                                            visible: csvPathInput.text.length > 0

                                            Text {
                                                anchors.centerIn: parent
                                                text: "✕"
                                                color: root.cTextMuted
                                                font.pixelSize: 11
                                            }

                                            MouseArea {
                                                id: clearMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    csvPathInput.text = ""
                                                    root.appendLog("Ruta de archivo limpiada", "info")
                                                }
                                            }
                                        }
                                    }

                                    SecondaryButton {
                                        text: "Examinar..."
                                        implicitWidth: 110
                                        implicitHeight: 44
                                        onClicked: csvFileDialog.open()
                                    }
                                }

                                PrimaryButton {
                                    id: convertBtn
                                    text: "Convertir a XLSX"
                                    Layout.fillWidth: true
                                    enabled: csvPathInput.text.trim().length > 0
                                    opacity: enabled ? 1.0 : 0.6

                                    onClicked: {
                                        var targetPath = csvPathInput.text.trim()
                                        root.appendLog("Iniciando conversión de: " + targetPath, "info")
                                        root.convertCsvRequested(targetPath)
                                        root.showToast("Procesando conversión...")
                                    }
                                }
                            }
                        }

                        // Tarjeta: Registro de Actividad y Logs
                        ContentCard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Text {
                                        text: "📋 Registro de Actividad (Logs)"
                                        color: cText
                                        font.pixelSize: 16
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }

                                    SecondaryButton {
                                        text: "Copiar Logs"
                                        implicitHeight: 32
                                        enabled: logTextArea.text.length > 0
                                        onClicked: root.copyToClipboard(logTextArea.text)
                                    }

                                    SecondaryButton {
                                        text: "Limpiar"
                                        implicitHeight: 32
                                        enabled: logTextArea.text.length > 0
                                        onClicked: root.clearLogs()
                                    }
                                }

                                // Contenedor ScrollView para que los logs no se corten
                                ScrollView {
                                    id: logScrollView
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true

                                    background: Rectangle {
                                        radius: 12
                                        color: root.cField
                                        border.color: root.cBorder
                                        border.width: 1
                                    }

                                    TextArea {
                                        id: logTextArea
                                        readOnly: true
                                        selectByMouse: true
                                        wrapMode: TextArea.Wrap
                                        color: root.cText
                                        font.family: "Consolas, Courier New, monospace"
                                        font.pixelSize: 13
                                        leftPadding: 14
                                        rightPadding: 14
                                        topPadding: 12
                                        bottomPadding: 12
                                        placeholderText: "Esperando acciones... Aquí se mostrarán los mensajes de estado y proceso."
                                        placeholderTextColor: root.cTextDim

                                        background: null
                                    }
                                }
                            }
                        }
                    }
                }

                //==================================================
                // PÁGINA 2: ORACLE SQL
                //==================================================
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        // Encabezado
                        ColumnLayout {
                            spacing: 4

                            Text {
                                text: "Oracle Database SQL"
                                color: cText
                                font.pixelSize: 28
                                font.bold: true
                            }

                            Text {
                                text: "Editor y ejecutor de consultas SQL para bases de datos Oracle."
                                color: cTextMuted
                                font.pixelSize: 13
                            }
                        }

                        // Tarjeta: Editor SQL
                        ContentCard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 12

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    Text {
                                        text: "💬 Editor de Consulta"
                                        color: cText
                                        font.pixelSize: 16
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }

                                    SecondaryButton {
                                        text: "Copiar SQL"
                                        implicitHeight: 32
                                        enabled: sqlTextArea.text.trim().length > 0
                                        onClicked: root.copyToClipboard(sqlTextArea.text)
                                    }

                                    SecondaryButton {
                                        text: "Limpiar"
                                        implicitHeight: 32
                                        enabled: sqlTextArea.text.trim().length > 0
                                        onClicked: {
                                            sqlTextArea.text = ""
                                            root.showToast("Editor SQL limpiado")
                                        }
                                    }
                                }

                                // Barra de snippets / plantillas rápidas
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: "Snippets:"
                                        color: root.cTextDim
                                        font.pixelSize: 12
                                    }

                                    QueryChip {
                                        chipText: "SELECT * FROM dual"
                                        onClicked: sqlTextArea.text = "SELECT SYSDATE, USER FROM dual;"
                                    }

                                    QueryChip {
                                        chipText: "SELECT COUNT(1)"
                                        onClicked: sqlTextArea.text = "SELECT COUNT(1) AS total FROM TABLA;"
                                    }

                                    QueryChip {
                                        chipText: "WHERE ROWNUM <= 50"
                                        onClicked: sqlTextArea.text += " WHERE ROWNUM <= 50"
                                    }

                                    Item { Layout.fillWidth: true }
                                }

                                // Área de texto con ScrollView y fuente monoespaciada
                                ScrollView {
                                    id: sqlScrollView
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true

                                    background: Rectangle {
                                        radius: 12
                                        color: root.cField
                                        border.color: sqlTextArea.activeFocus ? root.cBorderFocus : root.cBorder
                                        border.width: sqlTextArea.activeFocus ? 2 : 1
                                        Behavior on border.color { ColorAnimation { duration: 150 } }
                                    }

                                    TextArea {
                                        id: sqlTextArea
                                        selectByMouse: true
                                        wrapMode: TextArea.NoWrap
                                        color: root.cText
                                        font.family: "Consolas, Courier New, monospace"
                                        font.pixelSize: 14
                                        leftPadding: 14
                                        rightPadding: 14
                                        topPadding: 12
                                        bottomPadding: 12
                                        placeholderText: "-- Escribe tu consulta SQL aquí\nSELECT * FROM DUAL;"
                                        placeholderTextColor: root.cTextDim

                                        background: null
                                    }
                                }

                                // Botonera de Ejecución
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    PrimaryButton {
                                        text: "▶  Ejecutar Query"
                                        Layout.fillWidth: true
                                        implicitHeight: 48
                                        enabled: sqlTextArea.text.trim().length > 0
                                        opacity: enabled ? 1.0 : 0.6

                                        onClicked: {
                                            var query = sqlTextArea.text.trim()
                                            root.appendLog("Ejecutando consulta Oracle SQL: " + query.substring(0, 60) + (query.length > 60 ? "..." : ""), "info")
                                            root.executeQueryRequested(query)
                                            root.showToast("Consulta enviada a ejecución")
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

    //--------------------------------------------------
    // Toast Notification Flotante (Retroalimentación visual)
    //--------------------------------------------------
    Rectangle {
        id: toastNotification
        property string message: ""
        visible: false
        opacity: visible ? 1.0 : 0.0

        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 28

        implicitWidth: toastContent.implicitWidth + 36
        implicitHeight: 42
        radius: 21
        color: "#1e2f42"
        border.color: root.cPrimary
        border.width: 1

        Behavior on opacity { NumberAnimation { duration: 200 } }

        RowLayout {
            id: toastContent
            anchors.centerIn: parent
            spacing: 8

            Text {
                text: "✨"
                font.pixelSize: 14
            }

            Text {
                text: toastNotification.message
                color: "#ffffff"
                font.pixelSize: 13
                font.bold: true
            }
        }

        Timer {
            id: toastTimer
            interval: 2800
            repeat: false
            onTriggered: toastNotification.visible = false
        }
    }
}