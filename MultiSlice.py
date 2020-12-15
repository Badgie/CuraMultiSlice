import os
import re
from typing import cast, Optional
from pathlib import Path

from UM.i18n import i18nCatalog
from UM.Extension import Extension
from UM.PluginRegistry import PluginRegistry
from UM.Logger import Logger
from UM.Signal import Signal
from UM.Backend import Backend

from cura.CuraApplication import CuraApplication

from PyQt5.QtCore import QObject, pyqtSlot, pyqtProperty, QUrl, QEventLoop, pyqtSignal


catalog = i18nCatalog("cura")


class MultiSlicePlugin(QObject, Extension):

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)

        # add menu items in extensions menu
        self.setMenuName(catalog.i18nc("@item:inmenu", "Multi slicing"))
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Configure and run"), self._show_popup)

        self._view = None

        self._input_path = ''
        self._output_path = ''
        self._follow_dirs = False
        self._preserve_dirs = False
        self._file_pattern = r'.*.stl'
        self._follow_depth = 0

        self._files = []
        self._current_model = ''
        self._current_model_name = ''
        self._current_model_url = None  # type: Optional[QUrl]

        self._write_done = Signal()

        # event loop that allows us to wait for a signal
        self._loop = QEventLoop()

    # signal to handle output log messages
    log = pyqtSignal(str, name='log')

    def _log_msg(self, msg: str):
        """
        Emits a message to the logger signal
        """
        self.log.emit(msg)

    def _create_view(self):
        """
        Create plugin view dialog
        """
        path = os.path.join(
            cast(str, PluginRegistry.getInstance().getPluginPath('MultiSlice')),
            'MultiSliceView.qml')
        self._view = CuraApplication.getInstance().createQmlComponent(path, {'manager': self})

    def _show_popup(self):
        """
        Show plugin view dialog
        """
        if self._view is None:
            self._create_view()
            if self._view is None:
                Logger.log('e', 'Could not create QML')

        self._view.show()

    def _get_files(self, abs_paths: bool = False):
        """
        Recursively collect files from input dir relative to follow depth

        :param abs_paths: whether or not to collect absolute paths
        """
        files = []

        def _files(pattern: str, path: str, depth: int):
            # skip if we exceeded recursion depth
            if depth > self._follow_depth:
                return

            for d in os.listdir(path):

                # if we reached a directory, do recursive call
                if os.path.isdir(f'{path}/{d}'):
                    _files(pattern, f'{path}/{d}', depth + 1)
                # if we reached a file, check if it matches file pattern and add to list if so
                elif re.match(pattern, d):
                    nonlocal files
                    files.append(f'{path}/{d}' if abs_paths else d)

        _files(self._file_pattern, self._input_path, 0)
        return files

    @pyqtProperty(list)
    def files_names(self):
        return self._get_files()

    @pyqtProperty(list)
    def files_paths(self):
        return self._get_files(abs_paths=True)

    @pyqtSlot(str)
    def set_input_path(self, path: str):
        self._input_path = path

    @pyqtSlot(str)
    def set_output_path(self, path: str):
        self._output_path = path

    @pyqtSlot(bool)
    def set_follow_dirs(self, follow: bool):
        self._follow_dirs = follow

    @pyqtSlot(bool)
    def set_preserve_dirs(self, preserve: bool):
        self._preserve_dirs = preserve

    @pyqtSlot(str)
    def set_file_pattern(self, regex: str):
        if regex:
            try:
                re.compile(regex)
                self._file_pattern = regex
            except re.error:
                self._log_msg(f'Regex string \"{regex}\" is invalid, using default: '
                              f'{self._file_pattern}')

    @pyqtSlot(str)
    def set_follow_depth(self, depth: str):
        if depth:
            try:
                self._follow_depth = int(depth)
            except ValueError:
                self._log_msg(f'Depth value \"{depth}\" is invalid, using default: '
                              f'{self._follow_depth}')

    @pyqtSlot()
    def prepare_and_run(self):
        """
        Do initial setup for running and start
        """
        self._files = self.files_paths
        self._log_msg(f'Found {len(self._files)} files')
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
        """
        Prepare next model. If we don't have any models left to process, just set current to None.
        """
        if len(self._files) == 0:
            self._current_model = None
        else:
            self._log_msg(f'{len(self._files)} file(s) to go')
            self._current_model = self._files.pop()
            self._current_model_name = self._current_model.split('/')[-1]
            self._current_model_url = QUrl().fromLocalFile(self._current_model)

    def _run(self):
        """
        Run first iteration
        """
        self._load_model_and_slice()

    def _run_next(self):
        """
        Run subsequent iterations
        """
        self._log_msg('Clearing build plate and preparing next model')
        self._clear_models()
        self._prepare_next()

        if not self._current_model:
            self._log_msg('Found no more models. Done!')
            # reset signal connectors once all models are done
            self.__reset()
            return
        self._load_model_and_slice()

    def _load_model_and_slice(self):
        """
        Read .stl file into Cura and wait for fileCompleted signal
        """
        self._log_msg(f'Loading model {self._current_model_name}')
        CuraApplication.getInstance().readLocalFile(self._current_model_url)
        self._loop.exec()

    def _clear_models(self):
        """
        Clear all models on build plate
        """
        CuraApplication.getInstance().deleteAll()

    def _slice(self):
        """
        Begin slicing models on build plate and wait for backendStateChange to signal state 3,
        i.e. processing done
        """
        self._log_msg('Slicing...')
        CuraApplication.getInstance().backend.forceSlice()
        self._loop.exec()

    def _write_gcode(self, state):
        """
        Write sliced model to file in output dir and emit signal once done
        """
        if state == 3:
            file_name = self._current_model_name.replace('.stl', '.gcode')

            if self._preserve_dirs:
                rel_path = self._current_model.replace(self._input_path, '')
                path = '/'.join(x for x in f'{self._output_path}/{rel_path}'.split('/')[:-1])
                Path(path).mkdir(parents=True, exist_ok=True)
            else:
                path = self._output_path

            self._log_msg(f'Writing gcode to file {file_name}')
            self._log_msg(f'Saving to directory: {path}')

            with open(f'{path}/{file_name}', 'w') as stream:
                res = PluginRegistry.getInstance().getPluginObject("GCodeWriter").write(stream, [])

            if res:
                self._write_done.emit()

    def __reset(self):
        """
        Reset all signal connectors to allow running subsequent processes without several
        connector calls
        """
        CuraApplication.getInstance().fileCompleted.disconnect(self._slice)
        Backend.Backend.backendStateChange.disconnect(self._write_gcode)
        self._write_done.disconnect(self._run_next)