
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
    height: 550 * screenScaleFactor;
    minimumWidth: 400 * screenScaleFactor;
    minimumHeight: 250 * screenScaleFactor;
    color: UM.Theme.getColor("main_background");
    margin: screenScaleFactor * 20

    function trimPath(path) {
        return path.replace("file://", "")
    }

    function appendOutput(strList) {
        if (strList.length == 0) {
            outputBox.append("Found 0 files, please try again")
            return
        }

        for (var s in strList) {
            outputBox.append(strList[s])
        }
        outputBox.append("-----")
        outputBox.append("Found " + strList.length + " files")
        outputBox.append("Click Slice to start slicing")
        outputBox.append("-----")
        outputScroll.updateScroll()
    }

    function applySettings() {
        manager.set_file_pattern(regexText.text.toString())
        manager.set_follow_dirs(followCheckBox.checked)
        manager.set_follow_depth(followDepthField.text.toString())
        manager.set_preserve_dirs(preserveDirsCheckBox.checked)
        manager.set_input_path(trimPath(selectInputDirectoryDialog.folder.toString()))
        manager.set_output_path(trimPath(selectOutputDirectoryDialog.folder.toString()))
    }

    function run() {
        manager.prepare_and_run()
    }

    Item {
        Connections {
            target: manager
            function onError(msg) {
                if (errorPopupText.text === "") {
                    errorPopupText.text = msg
                    errorPopup.open()
                }
            }
        }
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
                    placeholderText: "regex"
                    color: UM.Theme.getColor("text")

                    background: Rectangle {
                        color: UM.Theme.getColor("main_background")
                        border.color: "black"
                        implicitWidth: dialog.width * 0.45
                    }
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

                RowLayout {
                    CheckBox {
                        id: followCheckBox
                        text: "Follow directories"
                        checked: false
                    }

                    Label {
                        id: followDepthLabel
                        text: "Max depth (default: 0):"
                        visible: followCheckBox.checked
                    }

                    TextArea {
                        id: followDepthField
                        placeholderText: "depth"
                        visible: followCheckBox.checked
                        color: UM.Theme.getColor("text")

                        background: Rectangle {
                            color: UM.Theme.getColor("main_background")
                            border.color: "black"
                            implicitWidth: dialog.width * 0.05
                        }
                    }
                }

                CheckBox {
                    id: preserveDirsCheckBox
                    text: "Preserve directories in output"
                    visible: followCheckBox.checked
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
                            appendOutput(manager.files_names)
                        }
                    }

                    Button {
                        id: sliceButton
                        text: "Slice"
                        onClicked: {
                            applySettings()
                            run()
                        }
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

                Connections {
                    target: manager
                    function onLog(msg) {
                        outputBox.append(msg)
                        outputScroll.updateScroll()
                    }
                }

                TextArea {
                    id: outputBox
                    readOnly: true
                    textFormat: TextEdit.PlainText
                    text: "Output log\n-----"
                    color: UM.Theme.getColor("text")
                    wrapMode: TextEdit.WordWrap

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
            }
        }
    }

    Item {
        // error popup
        Popup {
            id: errorPopup
            width: dialog.width * 0.5
            height: dialog.height * 0.2
            x: errorPopup.width / 2
            y: errorPopup.height / 2

            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

            onClosed: {
                errorPopupText.text = ""
            }

            contentItem: ColumnLayout {

                Text {
                    id: errorPopupText
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                    text: ""
                }

                Button {
                    id: popupCloseButton
                    text: "Close"
                    Layout.alignment: Qt.AlignHCenter
                    onClicked: {
                        errorPopup.close()
                    }
                }
            }
        }
    }
}