import os
import re
from typing import cast, Optional

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.Logger import Logger
from UM.Signal import Signal
from UM.Backend import Backend
from cura.CuraApplication import CuraApplication

from PyQt5.QtCore import QObject, pyqtSlot, pyqtProperty, QUrl, QEventLoop


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

        self._files = []
        self._current_model = ''
        self._current_model_name = ''
        self._current_model_url = None  # type: Optional[QUrl]

        self._write_done = Signal()

        self._loop = QEventLoop()

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

    def _get_files(self, abs_paths: bool = False):
        files = []

        def _files(pattern: str, path: str, depth: int):
            if depth > self._follow_depth:
                return

            for d in os.listdir(path):

                if os.path.isdir(f'{path}/{d}'):
                    _files(pattern, f'{path}/{d}', depth + 1)
                elif re.match(pattern, d):
                    nonlocal files
                    files.append(f'{path}/{d}' if abs_paths else d)

        _files(self._file_pattern, self._input_path, 0)
        return files

    @pyqtProperty(Signal)
    def ready(self):
        return self._ready

    @pyqtProperty(list)
    def filesNames(self):
        return self._get_files()

    @pyqtProperty(list)
    def filesPaths(self):
        return self._get_files(abs_paths=True)

    @pyqtSlot(str)
    def setCurrentModel(self, model: str):
        self._current_model = model

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

    @pyqtSlot()
    def prepare_and_run(self):
        self._files = self.filesPaths
        self._current_model = self._files.pop()
        self._current_model_name = self._current_model.split('/')[-1]
        self._current_model_url = QUrl().fromLocalFile(self._current_model)

        # slice when model is loaded
        CuraApplication.getInstance().fileCompleted.connect(self._slice)

        # write gcode to file when slicing is done
        Backend.Backend.backendStateChange.connect(self._write_gcode)

        # run next iteration when file is written
        self._write_done.connect(self._run_next)

        self._run()

    def _prepare_next(self):
        if len(self._files) == 0:
            self._current_model = None
        else:
            self._current_model = self._files.pop()
            self._current_model_name = self._current_model.split('/')[-1]
            self._current_model_url = QUrl().fromLocalFile(self._current_model)

    @pyqtSlot()
    def _run(self):
        self._load_model_and_slice()

    def _run_next(self):
        self._clear_models()
        self._prepare_next()

        if not self._current_model:
            # reset signal connectors once all models are done
            self.__reset()
            return

        self._load_model_and_slice()

    def _load_model_and_slice(self):
        CuraApplication.getInstance()
        CuraApplication.getInstance().readLocalFile(self._current_model_url)
        self._loop.exec()

    def _clear_models(self):
        CuraApplication.getInstance().deleteAll()

    def _slice(self):
        CuraApplication.getInstance().backend.forceSlice()
        self._loop.exec()

    def _write_gcode(self, state):
        if state == 3:
            with open(f'{self._output_path}/{self._current_model_name}', 'w') as stream:
                res = PluginRegistry.getInstance().getPluginObject("GCodeWriter").write(stream, [])
            if res:
                self._write_done.emit()

    def __reset(self):
        CuraApplication.getInstance().fileCompleted.disconnect(self._slice)
        Backend.Backend.backendStateChange.disconnect(self._write_gcode)
        self._write_done.disconnect(self._run_next)
