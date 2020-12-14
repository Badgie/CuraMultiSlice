import os
import re
from typing import cast

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.Logger import Logger
from cura.CuraApplication import CuraApplication

from PyQt5.QtCore import QObject, pyqtSlot, pyqtProperty


catalog = i18nCatalog("cura")


class MultiSlicePlugin(QObject, Extension):

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)
        self.setMenuName(catalog.i18nc("@item:inmenu", "Multi slicing"))
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Configure and run"), self.showPopup)

        self._view = None

        self._input_path = ''
        self._output_path = ''
        self._follow_dirs = False
        self._file_pattern = r'.*.stl'

    def _createView(self):
        """Creates the view used by show popup.
        The view is saved because of the fairly aggressive garbage collection.
        """
        # Create the plugin dialog component
        path = os.path.join(
            cast(str, PluginRegistry.getInstance().getPluginPath("MultiSlice")),
            "MultiSliceView.qml")
        self._view = CuraApplication.getInstance().createQmlComponent(path, {"manager": self})

    def showPopup(self):
        if self._view is None:
            self._createView()
            if self._view is None:
                Logger.log('e', 'Could not create QML')
        self._view.show()

    @pyqtProperty(list)
    def files(self):
        files = []
        print(self._file_pattern)
        print(self._follow_dirs)
        for d in os.listdir(self._input_path):
            if os.path.isdir(f'{self._input_path}/{d}'):
                files += [x for x in os.listdir(f'{self._input_path}/{d}')
                          if re.match(self._file_pattern, x)]
        return files

    @pyqtSlot(str)
    def setInputPath(self, path: str):
        if path:
            self._input_path = path

    @pyqtSlot(str)
    def setOutputPath(self, path: str):
        self._output_path = path

    @pyqtSlot(bool)
    def setFollowDirs(self, follow: bool):
        self._follow_dirs = follow

    @pyqtSlot(str)
    def setFilePattern(self, regex: str):
        if regex:
            self._file_pattern = regex

    @pyqtSlot()
    def getFileModel(self):
        return self._file_model
