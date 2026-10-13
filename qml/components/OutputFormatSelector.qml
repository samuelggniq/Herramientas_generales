import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ContentCard {
    id: outSelector

    property var controller: null
    property string outputFormat: "xlsx"
    property string csvDelimiter: ","
    property string csvEncoding: "utf-8-sig"

    Layout.fillWidth: true
    implicitHeight: col.implicitHeight + 28

    function cleanUrl(rawUrl) {
        var str = rawUrl.toString()
        if (str.indexOf("file:///") === 0) {
            str = str.substring(8)
        } else if (str.indexOf("file://") === 0) {
            str = str.substring(7)
        }
        return decodeURIComponent(str)
    }

    FolderDialog {
        id: folderDialog
        title: "Seleccionar carpeta de salida"
        onAccepted: {
            if (outSelector.controller) {
                outSelector.controller.setOutputDir(outSelector.cleanUrl(selectedFolder))
            }
        }
    }

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            Text {
                text: "💾 Formato de Salida:"
                color: "#edf2f7"
                font.pixelSize: 14
                font.bold: true
            }

            StyledComboBox {
                id: fmtCombo
                implicitWidth: 165
                implicitHeight: 34
                model: ["Excel (.xlsx)", "CSV (.csv)"]
                onActivated: {
                    outSelector.outputFormat = currentIndex === 0 ? "xlsx" : "csv"
                }
            }

            RowLayout {
                visible: outSelector.outputFormat === "csv"
                spacing: 8

                Text {
                    text: "Separador CSV:"
                    color: "#8b9fb2"
                    font.pixelSize: 12
                }

                StyledComboBox {
                    implicitWidth: 140
                    implicitHeight: 34
                    model: ["Coma (,)", "Punto y coma (;)", "Tabulador (\\t)", "Barra vertical (|)"]
                    onActivated: {
                        var m = {
                            "Coma (,)": ",",
                            "Punto y coma (;)": ";",
                            "Tabulador (\\t)": "\t",
                            "Barra vertical (|)": "|"
                        }
                        outSelector.csvDelimiter = m[currentText] || ","
                    }
                }

                Text {
                    text: "Codificación:"
                    color: "#8b9fb2"
                    font.pixelSize: 12
                }

                StyledComboBox {
                    implicitWidth: 130
                    implicitHeight: 34
                    model: ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
                    onActivated: {
                        outSelector.csvEncoding = currentText
                    }
                }
            }

            Item { Layout.fillWidth: true }

            Text {
                text: outSelector.controller ? ("Carpeta: " + outSelector.controller.outputDir) : ""
                color: "#8b9fb2"
                font.pixelSize: 11
                elide: Text.ElideMiddle
                Layout.maximumWidth: 260
            }

            ActionButton {
                isPrimary: false
                text: "Carpeta..."
                implicitHeight: 32
                onClicked: folderDialog.open()
            }
        }
    }
}

