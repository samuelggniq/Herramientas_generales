import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: root

    visible: true
    width: 1180
    height: 780
    minimumWidth: 860
    minimumHeight: 620
    title: "Sistema Maestro de Herramientas"

    //--------------------------------------------------
    // Paleta de Colores y Tokens de Diseño (Tema Oscuro)
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

    readonly property bool anyToolBusy: (csvConverterController && csvConverterController.isBusy) ||
                                        (fileProfilerController && fileProfilerController.isBusy) ||
                                        (dataCleanerController && dataCleanerController.isBusy) ||
                                        (duplicateFinderController && duplicateFinderController.isBusy) ||
                                        (fileDiffController && fileDiffController.isBusy) ||
                                        (fileMergeController && fileMergeController.isBusy) ||
                                        (oracleSqlController && oracleSqlController.isBusy)

    function showToast(message) {
        toastNotification.message = message
        toastNotification.visible = true
        toastTimer.restart()
    }

    // Conexiones de notificaciones Toast desde el backend
    Connections {
        target: appLogger
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: csvConverterController
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: fileProfilerController
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: dataCleanerController
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: duplicateFinderController
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: fileDiffController
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: fileMergeController
        function onToastRequested(msg) { root.showToast(msg) }
    }
    Connections {
        target: oracleSqlController
        function onToastRequested(msg) { root.showToast(msg) }
    }

    color: cBackground

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
            Layout.preferredWidth: 265
            Layout.fillHeight: true

            radius: 24
            color: cSidebar
            border.color: cBorder
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8

                // Cabecera / Identidad
                RowLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: 4
                    Layout.bottomMargin: 6
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
                    Layout.bottomMargin: 4
                }

                // Lista de Navegación por Secciones con Scroll
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth

                    ColumnLayout {
                        width: parent.width
                        spacing: 4

                        Repeater {
                            model: [
                                { isSection: true, sectionTitle: "PREPARAR" },
                                { isSection: false, pageIndex: 0, title: "Conversión CSV", subtitle: "A formato XLSX o CSV", icon: "📊" },
                                { isSection: false, pageIndex: 1, title: "Limpieza de datos", subtitle: "Reglas y normalización", icon: "🧹" },
                                { isSection: false, pageIndex: 2, title: "Duplicados", subtitle: "Detectar y separar", icon: "🗂️" },
                                { isSection: true, sectionTitle: "ANALIZAR" },
                                { isSection: false, pageIndex: 3, title: "Perfilado de archivo", subtitle: "Calidad y estadísticas", icon: "🔍" },
                                { isSection: false, pageIndex: 4, title: "Comparar archivos", subtitle: "Diferencias A vs B", icon: "⚖️" },
                                { isSection: false, pageIndex: 5, title: "Cruzar archivos", subtitle: "Merge tipo VLOOKUP", icon: "🔗" },
                                { isSection: true, sectionTitle: "DATOS EXTERNOS" },
                                { isSection: false, pageIndex: 6, title: "Oracle SQL", subtitle: "Consultas y exportación", icon: "🗄️" }
                            ]

                            Item {
                                Layout.fillWidth: true
                                implicitHeight: modelData.isSection ? 26 : 52

                                // Encabezado de sección
                                Text {
                                    visible: modelData.isSection === true
                                    anchors.left: parent.left
                                    anchors.leftMargin: 10
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 2
                                    text: modelData.sectionTitle || ""
                                    color: root.cTextDim
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.letterSpacing: 1.2
                                }

                                // Ítem de herramienta
                                Rectangle {
                                    id: navItem
                                    visible: !modelData.isSection
                                    anchors.fill: parent
                                    radius: 14

                                    readonly property bool isSelected: !modelData.isSection && root.currentPage === modelData.pageIndex

                                    color: isSelected
                                           ? Qt.rgba(45/255, 156/255, 255/255, 0.18)
                                           : (navMouse.containsMouse ? root.cSidebarItemHover : "transparent")

                                    border.color: isSelected ? Qt.rgba(45/255, 156/255, 255/255, 0.35) : "transparent"
                                    border.width: 1

                                    Behavior on color { ColorAnimation { duration: 150 } }
                                    Behavior on border.color { ColorAnimation { duration: 150 } }

                                    Rectangle {
                                        width: 4
                                        height: 22
                                        radius: 2
                                        color: root.cPrimary
                                        anchors.left: parent.left
                                        anchors.leftMargin: 4
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: navItem.isSelected
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 10
                                        spacing: 10

                                        Text {
                                            text: modelData.icon || ""
                                            font.pixelSize: 17
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1

                                            Text {
                                                text: modelData.title || ""
                                                color: navItem.isSelected ? "#ffffff" : root.cText
                                                font.pixelSize: 13
                                                font.bold: navItem.isSelected
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }

                                            Text {
                                                text: modelData.subtitle || ""
                                                color: root.cTextMuted
                                                font.pixelSize: 11
                                                elide: Text.ElideRight
                                                Layout.fillWidth: true
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: navMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (!modelData.isSection) {
                                                root.currentPage = modelData.pageIndex
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Pie del Sidebar: Estado del Sistema y Versión
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
                            color: root.anyToolBusy ? root.cWarning : root.cSuccess
                        }

                        Text {
                            text: root.anyToolBusy ? "Procesando tarea..." : "Sistema Listo"
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
                currentIndex: root.currentPage

                CsvConverterPage {}
                DataCleanerPage {}
                DuplicateFinderPage {}
                FileProfilerPage {}
                FileDiffPage {}
                FileMergePage {}
                OracleSqlPage {}
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