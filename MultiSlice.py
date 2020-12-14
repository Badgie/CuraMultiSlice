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
        self._follow_depth = 1

    def _createView(self):
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
            try:
                re.compile(regex)
                self._file_pattern = regex
            except re.error:
                print(f'Regex string \"{regex}\" is invalid, using default: {self._file_pattern}')

    @pyqtSlot(str)
    def setFollowDepth(self, depth: str):
        if depth:
            try:
                self._follow_depth = int(depth)
            except ValueError:
                print(f'Depth value \"{depth}\" is invalid, using default: {self._follow_depth}')
