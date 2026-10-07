import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root

    visible: true
    width: 900
    height: 700
    title: "Sistema Maestro de Herramientas"

    //--------------------------------------------------
    // Colores
    //--------------------------------------------------

    property color cBackground: "#071018"
    property color cSidebar: "#111b24"
    property color cCard: "#162330"
    property color cPrimary: "#2d9cff"
    property color cPrimaryHover: "#45a8ff"
    property color cText: "#e9f0f7"
    property color cMuted: "#94a8bb"
    property color cField: "#0d1720"

    property int currentPage: 0

    color: cBackground

    //--------------------------------------------------
    // Layout Principal
    //--------------------------------------------------

    RowLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        //--------------------------------------------------
        // SIDEBAR
        //--------------------------------------------------

        Rectangle {
            Layout.preferredWidth: 250
            Layout.fillHeight: true

            radius: 28
            color: cSidebar

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 12

                Text {
                    text: "Sidebar"

                    color: cText
                    font.pixelSize: 24
                    font.bold: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 50

                    radius: 14

                    color: currentPage === 0
                        ? cPrimary
                        : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "Conversión CSV → XLSX"
                        color: cText
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: currentPage = 0
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 50

                    radius: 14

                    color: currentPage === 1
                        ? cPrimary
                        : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "Oracle"
                        color: cText
                        font.pixelSize: 14
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: currentPage = 1
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 50

                    radius: 14

                    color: "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "SharePoint"
                        color: cMuted
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 50

                    radius: 14

                    color: "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "Traducciones"
                        color: cMuted
                    }
                }

                Item {
                    Layout.fillHeight: true
                }
                
            }
        }

        //--------------------------------------------------
        // CONTENIDO
        //--------------------------------------------------

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true

            radius: 28
            color: cSidebar

            StackLayout {
                anchors.fill: parent
                currentIndex: currentPage

                //--------------------------------------------------
                // CSV -> XLSX
                //--------------------------------------------------

                Item {

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 15

                        Text {
                            text: "Conversión CSV a XLSX"

                            color: cText
                            font.pixelSize: 35
                            font.bold: true
                        }

                        Text {
                            text: "Convierte archivos CSV a Excel de forma rápida."
                            color: cMuted
                            font.pixelSize: 14
                        }

                        //--------------------------------------------------
                        // Card archivo
                        //--------------------------------------------------

                        Rectangle {

                            Layout.fillWidth: true
                            Layout.preferredHeight: 230

                            radius: 22
                            color: cCard

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 15

                                Text {
                                    text: "Archivo CSV"
                                    color: cText
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                RowLayout {
                                    Layout.fillWidth: true

                                    TextField {
                                        Layout.fillWidth: true
                                        placeholderText: "Selecciona un archivo CSV"
                                        color: cText
                                        font.pixelSize: 16
                                        implicitHeight: 44
                                        verticalAlignment: Text.AlignVCenter

                                        background: Rectangle {
                                            radius: 14
                                            color: cField
                                            border.color: "#223242"
                                        }
                                    }

                                    Button {
                                        text: "Examinar"

                                        implicitHeight: 44

                                        background: Rectangle {
                                            radius: 14
                                            color: cPrimary
                                        }

                                        contentItem: Text {
                                            text: parent.text
                                            color: "white"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            font.pixelSize: 16
                                        }
                                    }
                                }

                                Button {

                                    text: "Convertir"

                                    Layout.fillWidth: true
                                    implicitHeight: 50

                                    background: Rectangle {
                                        radius: 14
                                        color: cPrimary
                                    }

                                    contentItem: Text {
                                        text: parent.text
                                        color: "white"
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }

                        //--------------------------------------------------
                        // Logs
                        //--------------------------------------------------

                        Rectangle {

                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            radius: 22
                            color: cCard

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 15

                                Text {
                                    text: "Logs"

                                    color: cText
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                TextArea {

                                    Layout.fillWidth: true
                                    Layout.fillHeight: true

                                    placeholderText:
                                        "Aquí aparecerán los mensajes del proceso..."

                                    color: cText

                                    background: Rectangle {
                                        radius: 14
                                        color: cField
                                        border.color: "#223242"
                                    }
                                }
                            }
                        }
                    }
                }

                //--------------------------------------------------
                // Oracle
                //--------------------------------------------------

                Item {

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 30
                        spacing: 20

                        Text {
                            text: "Oracle"

                            color: cText
                            font.pixelSize: 38
                            font.bold: true
                        }

                        Rectangle {

                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            radius: 22
                            color: cCard

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 15

                                Text {
                                    text: "Consulta SQL"
                                    color: cText
                                    font.pixelSize: 18
                                    font.bold: true
                                }

                                TextArea {

                                    Layout.fillWidth: true
                                    Layout.fillHeight: true

                                    placeholderText:
                                        "SELECT * FROM TABLA"

                                    color: cText

                                    background: Rectangle {
                                        radius: 14
                                        color: cField
                                        border.color: "#223242"
                                    }
                                }

                                Button {

                                    text: "Ejecutar Query"

                                    implicitHeight: 50

                                    background: Rectangle {
                                        radius: 14
                                        color: cPrimary
                                    }

                                    contentItem: Text {
                                        text: parent.text
                                        color: "white"
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
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