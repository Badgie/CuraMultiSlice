
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs 1.3
import QtQuick.Window 2.15

import UM 1.3 as UM
import Cura 1.1 as Cura

UM.Dialog
{
    id: dialog

    title: catalog.i18nc("@title:window", "Multi slicing");
    width: 1000 * screenScaleFactor;
    height: 500 * screenScaleFactor;
    minimumWidth: 400 * screenScaleFactor;
    minimumHeight: 250 * screenScaleFactor;
    color: UM.Theme.getColor("main_background");
    margin: screenScaleFactor * 20

    function trimPath(path) {
        return path.replace("file://", "")
    }

    function appendOutput(strList) {
        console.log(strList)
        for (var s in strList) {
            outputBox.append(strList[s])
            outputScroll.updateScroll()
        }
    }

    function applySettings() {
        manager.setFilePattern(regexText.text.toString())
    }

    GridLayout {
        id: grid
        columns: 2

        ColumnLayout {
            id: leftCol
            Layout.preferredWidth: dialog.width * 0.5

            UM.I18nCatalog {
                id: catalog
                name: "cura"
            }

            // regex input field segment
            ColumnLayout {
                id: regexRow

                Label {
                    id: textAreaLabel
                    text: "File name pattern (default: all .stl files)"
                    font.bold: true
                }

                TextArea {
                    id: regexText;
                    textFormat: TextEdit.PlainText
                    placeholderText: "Regex"
                }
            }

            // input directory selection segment
            ColumnLayout {
                id: inputDirRow
                Layout.minimumWidth: dialog.width * 0.9

                Label {
                    id: inputDirButtonLabel
                    text: "Root directory"
                    font.bold: true
                }

                Button {
                    id: btnSelectDir
                    text: "Select folder"
                    onClicked: selectInputDirectoryDialog.open()
                }

                Label {
                    id: inputDirChoiceRowText
                    text: ""
                    font.italic: true
                }
            }

            // output directory selection segment
            ColumnLayout {
                id: outputDirRow

                Label {
                    id: outputDirButtonLabel
                    text: "Output directory"
                    font.bold: true
                }

                Button {
                    id: btnOutputDir
                    text: "Select folder"
                    onClicked: selectOutputDirectoryDialog.open()
                }

                Label {
                    id: outputDirChoiceRowText
                    text: ""
                    font.italic: true
                }
            }

            // checkbox setting segment
            ColumnLayout {
                id: checkBoxRow

                CheckBox {
                    id: followCheckBox
                    text: "Follow directories"
                    checked: false
                }
            }

            // button segment
            ColumnLayout {
                id: buttonRow

                RowLayout {

                    Button {
                        id: checkButton
                        text: "Check files"
                        onClicked: {
                            applySettings()
                            appendOutput(manager.files)
                        }
                    }

                    Button {
                        id: sliceButton
                        text: "Slice"
                    }
                }
            }
        }

        ColumnLayout {
            ScrollView {
                id: outputScroll
                implicitWidth: dialog.width * 0.45
                implicitHeight: dialog.height * 0.9
                clip: true

                function updateScroll() {
                    ScrollBar.vertical.position = 1.0
                    ScrollBar.vertical.increase()
                }


                TextArea {
                    id: outputBox
                    readOnly: true
                    textFormat: TextEdit.MarkdownText
                    text: "### Output log\n --- \n"
                    color: "white"

                    background: Rectangle {
                        color: UM.Theme.getColor("main_background")
                        border.color: "black"
                        implicitWidth: dialog.width * 0.45
                        implicitHeight: dialog.height * 0.9
                    }
                }
            }
        }
    }

    Item {
        // needs to be in Item otherwise the qml loader dies
        FileDialog {
            id: selectOutputDirectoryDialog
            title: "Select directory"
            selectExisting: true
            selectFolder: true
            folder: StandardPaths.HomeLocation
            onAccepted: {
                outputDirChoiceRowText.text = trimPath(selectOutputDirectoryDialog.folder.toString())
                manager.setOutputPath(trimPath(selectOutputDirectoryDialog.folder.toString()))
            }
        }
    }

    Item {
        // needs to be in Item otherwise the qml loader dies
        FileDialog {
            id: selectInputDirectoryDialog
            title: "Select directory"
            selectExisting: true
            selectFolder: true
            folder: StandardPaths.HomeLocation
            onAccepted: {
                inputDirChoiceRowText.text = trimPath(selectInputDirectoryDialog.folder.toString())
                manager.setInputPath(trimPath(selectInputDirectoryDialog.folder.toString()))
            }
        }
    }
}