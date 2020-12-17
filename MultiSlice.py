import os
import re
from typing import Optional, List, Union
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
    """
    A plugin for Ultimaker Cura that allows the user to load, slice, and export .gcode files
    for a series of model files based on an input directory and a regex file pattern to search for.
    See README.md for an example.

    Settings:
    :param self._file_pattern
        :GUI "File name pattern"
        :default r'.*.stl' (all .stl files)

        RegEx that defines the files that should be searched for. Only files matching this pattern
        are added to the list of files.

    :param self._input_path
        :GUI "Root directory"
        :default None

        The directory that will be walked when searching for files.

    :param self._output_path
        :GUI "Output directory"
        :default None

        The directory that .gcode files will be written to.

    :param self._follow_dirs
        :GUI "Follow directories
        :default False

        Whether or not to walk through directories found in self._input_path as well.

    :param self._follow_depth
        :GUI "Max depth"
        :default 0

        The maximum depth to walk when following directories. The root directory is treated as
        depth 0.

    :param self._preserve_dirs
        :GUI: "Preserve directories in output
        :default False

        Whether or not to produce the same folder structure in the output directory as found in
        the root directory.
    """

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)

        # add menu items in extensions menu
        self.setMenuName(catalog.i18nc("@item:inmenu", "Multi slicing"))
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Configure and run"), self._show_popup)

        self._view = None  # type: Optional[QObject]

        # user options
        self._file_pattern = r'.*.stl'
        self._input_path = ''  # type: Union[Path, str]
        self._output_path = ''  # type: Union[Path, str]
        self._follow_dirs = False
        self._follow_depth = 0  # type: Optional[int]
        self._preserve_dirs = False

        self._files = []
        self._current_model = ''  # type: Union[Path, str]
        self._current_model_suffix = ''
        self._current_model_name = ''
        self._current_model_url = None  # type: Optional[QUrl]

        # gcode writer signal
        self._write_done = Signal()

        # event loop that allows us to wait for a signal
        self._loop = QEventLoop()

    # signal to handle output log messages
    log = pyqtSignal(str, name='log')

    def _log_msg(self, msg: str) -> None:
        """
        Emits a message to the logger signal
        """
        self.log.emit(msg)

    # signal to handle error messages
    error = pyqtSignal(str, name='error')

    def _send_error(self, msg: str) -> None:
        """
        Emits an error message to display in an error popup
        """
        self.error.emit(msg)

    # signal to send when processing is odne
    processingDone = pyqtSignal(name='processingDone')

    def _signal_done(self) -> None:
        """
        Signals to the frontend that the current session is finished
        """
        self.processingDone.emit()

    def _create_view(self) -> None:
        """
        Create plugin view dialog
        """
        path = Path(PluginRegistry.getInstance().getPluginPath('MultiSlice')) / 'MultiSliceView.qml'
        self._view = CuraApplication.getInstance().createQmlComponent(str(path), {'manager': self})

    def _show_popup(self) -> None:
        """
        Show plugin view dialog
        """
        if self._view is None:
            self._create_view()
            if self._view is None:
                Logger.log('e', 'Could not create QML')

        self._view.show()

    def _get_files(self, abs_paths: bool = False) -> List[Union[Path, str]]:
        """
        Recursively collect files from input dir relative to follow depth

        :param abs_paths: whether or not to collect absolute paths
        """
        files = []

        def _files(pattern: str, path: Path, depth: int):
            # skip if we exceeded recursion depth
            if depth > self._follow_depth:
                return

            try:
                for d in path.iterdir():

                    # if we reached a directory, do recursive call
                    if d.is_dir():
                        _files(pattern, d, depth + 1)
                    # if we reached a file, check if it matches file pattern and add to list if so
                    elif d.is_file() and re.match(pattern, d.name):
                        nonlocal files
                        files.append(d if abs_paths else d.name)

            except PermissionError:
                # if we can't read the current step, notify and skip
                self._log_msg(f'Could not access directory {str(path)}, reason: permission denied. '
                              f'Skipping.')
                return

        _files(self._file_pattern, self._input_path, 0)
        return files

    @pyqtProperty(list)
    def files_names(self) -> List[str]:
        """
        Retrieve names of all files matching settings
        """
        return self._get_files() or []

    @pyqtProperty(list)
    def files_paths(self) -> List[Path]:
        """
        Retrieve paths of all files matching settings
        """
        return self._get_files(abs_paths=True) or []

    @pyqtSlot(str)
    def set_input_path(self, path: str) -> None:
        """
        Set input path if valid
        """
        if path and os.path.isdir(path):
            self._input_path = Path(path)

    @pyqtSlot(str)
    def set_output_path(self, path: str) -> None:
        """
        Set output path if valid
        """
        if path and os.path.isdir(path):
            self._output_path = Path(path)

    @pyqtSlot(bool)
    def set_follow_dirs(self, follow: bool) -> None:
        """
        Set follow directories option
        """
        self._follow_dirs = follow

    @pyqtSlot(bool)
    def set_preserve_dirs(self, preserve: bool) -> None:
        """
        Set preserve directories option
        """
        self._preserve_dirs = preserve

    @pyqtSlot(str)
    def set_file_pattern(self, regex: str) -> None:
        """
        Set regex file pattern option if present, otherwise preserve default
        """
        if regex:
            self._file_pattern = regex

    @pyqtSlot(str)
    def set_follow_depth(self, depth: str) -> None:
        """
        Set follow depth option if present, otherwise preserve default
        """
        if depth:
            self._follow_depth = depth

    @pyqtProperty(bool)
    def validate_input(self) -> bool:
        """
        Try and validate applicable(bool options obviously don't need to be validated) options.
        Emit error and return false if any fail.
        """
        # file pattern should be valid regex
        try:
            re.compile(self._file_pattern)
        except re.error:
            self._send_error(f'Regex string \"{self._file_pattern}\" is not a valid regex. '
                             f'Please try again.')
            return False

        # input path should be a valid path
        if type(self._input_path) is str or not self._input_path.is_dir():
            self._send_error(f'Input path \"{self._input_path}\" is not a valid path. '
                             f'Please try again.')
            return False

        # output path should be a valid path
        if type(self._output_path) is str or not self._output_path.is_dir():
            self._send_error(f'Output path \"{self._output_path}\" is not a valid path. '
                             f'Please try again.')
            return False

        # follow depth should be an int
        try:
            self._follow_depth = int(self._follow_depth)
        except ValueError:
            self._send_error(f'Depth value \"{self._follow_depth}\" is not a valid integer. '
                             f'Please try again.')
            return False

        return True

    @pyqtSlot()
    def prepare_and_run(self) -> None:
        """
        Do initial setup for running and start
        """
        self._files = self.files_paths

        # don't proceed if no files are found
        if len(self._files) is 0:
            self._log_msg('Found 0 files, please try again')
            self._log_msg('-----')
            self._signal_done()
            return

        self._log_msg(f'Found {len(self._files)} files')
        self._prepare_model()

        # slice when model is loaded
        CuraApplication.getInstance().fileCompleted.connect(self._slice)

        # write gcode to file when slicing is done
        Backend.Backend.backendStateChange.connect(self._write_gcode)

        # run next model when file is written
        self._write_done.connect(self._run_next)

        self._clear_models()

        self._run()

    def _prepare_next(self) -> None:
        """
        Prepare next model. If we don't have any models left to process, just set current to None.
        """
        # if we don't have any files left, set current model to none
        # current model is checked in function _run_next()
        if len(self._files) == 0:
            self._current_model = None
        else:
            self._log_msg(f'{len(self._files)} file(s) to go')
            self._prepare_model()

    def _prepare_model(self) -> None:
        """
        Perform necessary actions and field assignments for a given model
        """
        self._current_model = self._files.pop()
        self._current_model_suffix = self._current_model.suffix
        self._current_model_name = self._current_model.name
        self._current_model_url = QUrl().fromLocalFile(str(self._current_model))

    def _run(self) -> None:
        """
        Run first iteration
        """
        self._load_model_and_slice()

    def _run_next(self) -> None:
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
            self._signal_done()
            return

        self._load_model_and_slice()

    def _load_model_and_slice(self) -> None:
        """
        Read .stl file into Cura and wait for fileCompleted signal
        """
        self._log_msg(f'Loading model {self._current_model_name}')
        CuraApplication.getInstance().readLocalFile(self._current_model_url)
        # wait for Cura to signal that it completed loading the file
        self._loop.exec()

    def _clear_models(self) -> None:
        """
        Clear all models on build plate
        """
        CuraApplication.getInstance().deleteAll()

    def _slice(self) -> None:
        """
        Begin slicing models on build plate and wait for backendStateChange to signal state 3,
        i.e. processing done
        """
        self._log_msg('Slicing...')
        CuraApplication.getInstance().backend.forceSlice()
        # wait for CuraEngine to signal that slicing is done
        self._loop.exec()

    def _write_gcode(self, state) -> None:
        """
        Write sliced model to file in output dir and emit signal once done
        """
        # state = 3 = process is done
        if state == 3:
            # ensure proper file suffix
            file_name = self._current_model_name.replace(self._current_model_suffix, '.gcode')

            # construct path relative to output directory using input path structure if we are
            # following directories
            # otherwise just dump it into the output directory
            if self._preserve_dirs:
                rel_path = self._current_model.relative_to(self._input_path)
                path = (self._output_path / rel_path).parent / file_name
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                path = self._output_path / file_name

            self._log_msg(f'Writing gcode to file {file_name}')
            self._log_msg(f'Saving to directory: {str(path)}')

            with path.open(mode='w') as stream:
                res = PluginRegistry.getInstance().getPluginObject("GCodeWriter").write(stream, [])

            # GCodeWriter notifies success state with bool
            if res:
                self._write_done.emit()

    def __reset(self) -> None:
        """
        Reset all signal connectors to allow running subsequent processes without several
        connector calls
        """
        CuraApplication.getInstance().fileCompleted.disconnect(self._slice)
        Backend.Backend.backendStateChange.disconnect(self._write_gcode)
        self._write_done.disconnect(self._run_next)

    @pyqtSlot()
    def stop_multi_slice(self) -> None:
        """
        Stop the session currently running
        """
        self._log_msg("Cancel signal emitted, stopping Multislice")
        self.__reset()
        self._loop.exit()
