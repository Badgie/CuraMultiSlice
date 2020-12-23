
import QtQuick 2.7
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.2

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

    // remove the url bit of the input path - for output formatting
    function trimPath(path) {
        return path.replace("file://", "")
    }

    // append a list of strings to the output log - used to print a list of file names
    function appendOutput(strList) {
        // if we don't have any elements, notify and return
        if (strList.length == 0) {
            outputBox.append("Found 0 files, please try again")
            outputBox.append("-----")
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

    // apply all settings applied in the GUI and try to validate
    function applySettings() {
        manager.set_file_pattern(regexText.text.toString())
        manager.set_follow_dirs(followCheckBox.checked)
        manager.set_follow_depth(followDepthField.text.toString())
        manager.set_preserve_dirs(preserveDirsCheckBox.checked)
        manager.set_input_path(trimPath(selectInputDirectoryDialog.folder.toString()))
        manager.set_output_path(trimPath(selectOutputDirectoryDialog.folder.toString()))
        return manager.validate_input
    }

    // main runner
    function run() {
        manager.prepare_and_run()
    }

    Item {
        // custom signal connections
        Connections {
            target: manager

            // on error signals, set the message as the text on the error popup and display it
            function onError(msg) {
                if (errorPopupText.text === "") {
                    errorPopupText.text = msg
                    errorPopup.open()
                }
            }

            // on log signals, append the message to the output log
            function onLog(msg) {
                outputBox.append(msg)
                outputScroll.updateScroll()
            }

            // stuff to do when everything is done
            function onProcessingDone() {
                sliceButton.visible = true
                cancelButton.visible = false
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

                TextField {
                    id: regexText;
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
                        font.bold: true
                    }

                    Label {
                        id: followDepthLabel
                        text: "Max depth (default: 0):"
                        visible: followCheckBox.checked
                        font.bold: true
                    }

                    TextField {
                        id: followDepthField
                        placeholderText: "depth"
                        visible: followCheckBox.checked
                        color: UM.Theme.getColor("text")
                        // if top is set to 10, any two digit number is valid input
                        // also avoids recursion exceptions
                        validator: IntValidator {bottom: 0; top: 9;}

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
                    font.bold: true
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
                            if (applySettings()) appendOutput(manager.files_names);
                        }
                    }

                    Button {
                        id: sliceButton
                        text: "Slice"
                        visible: true
                        onClicked: {
                            if (applySettings()) {
                                sliceButton.visible = false
                                cancelButton.visible = true
                                run();
                            }
                        }
                    }

                    Button {
                        id: cancelButton
                        text: "Cancel"
                        visible: false
                        onClicked: {
                            sliceButton.visible = true
                            cancelButton.visible = false
                            manager.stop_multi_slice()
                        }
                    }

                    Button {
                        id: closeButton
                        text: "Close"
                        onClicked: {
                            dialog.close()
                        }
                    }
                }
            }
        }

        // output log segment
        ColumnLayout {
            ScrollView {
                id: outputScroll
                implicitWidth: dialog.width * 0.45
                implicitHeight: dialog.height * 0.9
                clip: true

                function updateScroll() {
                    /*
                        set the scroll view position to the end of the contents

                        without the increase() call it will scroll past the text - the call ensures
                        that the last line of the text is always at the bottom
                    */
                    ScrollBar.vertical.position = 1.0
                    ScrollBar.vertical.increase()
                }

                TextArea {
                    id: outputBox
                    readOnly: true
                    textFormat: TextEdit.PlainText
                    text: "Output log\n-----"
                    color: UM.Theme.getColor("text")
                    wrapMode: TextEdit.Wrap

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
        // output directory selection
        FileDialog {
            id: selectOutputDirectoryDialog
            title: "Select directory"
            selectExisting: true
            selectFolder: true

            onAccepted: {
                outputDirChoiceRowText.text = trimPath(selectOutputDirectoryDialog.folder.toString())
            }

            onRejected: {
                outputDirChoiceRowText.text = trimPath(selectOutputDirectoryDialog.folder.toString())
            }
        }
    }

    Item {
        // needs to be in Item otherwise the qml loader dies
        // input directory selection
        FileDialog {
            id: selectInputDirectoryDialog
            title: "Select directory"
            selectExisting: true
            selectFolder: true

            onAccepted: {
                inputDirChoiceRowText.text = trimPath(selectInputDirectoryDialog.folder.toString())
            }

            onRejected: {
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