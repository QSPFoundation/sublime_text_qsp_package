import os
from typing import List

from . import function as qsp
from .converter.qsps_file import QspsFile
from .converter.tps import (
    QspsLine, Path
)
from .plugtypes import QspModule
# import time

class ModuleQSP():

    def __init__(self, scheme:QspModule) -> None:

        # main settings
        self._scheme:QspModule = scheme

        # self._output_qsp:Path = ''        # path of output QSP-file (module)
        # self._output_txt:Path = ''        # path of temp file in txt2gam format
        # self._set_output_files()

        self._src_files:List[QspsFile] = []
        self._src_files_pathes:List[Path] = []
        self._extends_by_scheme()

        # self.code_system = 'utf-8'

        # self._src_lines:List[QspsLine] = []    # all strings of module code
        # self.start_time = start_time
    
    def extend_by_file(self, file_path:str) -> None: # file_path:abs_path of file
        """ Add QspsFile by file-path """
        if os.path.isfile(file_path):
            src = QspsFile()
            src.read_from_file(file_path)
            self._src_files.append(src)
            self._src_files_pathes.append(file_path)
        else:
            qsp.write_error_log(f'[ModuleQSP:001] File don\'t exist. Prove path {file_path}.')

    def extend_by_folder(self, folder_path:str) -> None:
        """ Add SrcQspsFile-objs by folder-path """
        if not os.path.isdir(folder_path):
            qsp.write_error_log(f'[ModuleQSP:002] Folder don\'t exist. Prove path {folder_path}.')
            return None
        for el in qsp.get_files_list(folder_path):
            self.extend_by_file(el)

    def extend_by_src(self, qsps_lines:List[QspsLine]) -> None:
        """ Add QspsFile by qsps-src-code strings """
        src = QspsFile(qsps_lines)
        self._src_files.append(src)

    def add_qsps_file(self, src:QspsFile) -> None:
        """ Append QspsFile at list of src-files """
        self._src_files.append(src)

    # def _set_output_files(self) -> None:
    #     """
    #         Set output module (game) file path and temp-file (txt) path.
    #     """
    #     self._output_qsp = self._scheme.get('module', '')
    #     self._output_txt = os.path.splitext(self._output_qsp)[0]+".txt"

    def _extends_by_scheme(self) -> None:
        """ Extend ModuleQSP by files from instruction """
        for file in self._scheme.get('files', []):
            self.extend_by_file(file['path'])
        for path in self._scheme.get('folders', []):
            self.extend_by_folder(path['path'])

    def qsps_files(self) -> List[QspsFile]:
        """ Return list of all Qsps-Files. """
        return self._src_files

    def src_to_text(self) -> str:
        """ Get outer text of module """
        text:List[str] = []
        for src in self._src_files:
            text.extend(src.get_src())
            text.append('\n')
        return ''.join(text)

    def src_lines(self) -> List[QspsLine]:
        """ From qsps-files return sources lines and add to module source """
        src_lines:List[QspsLine] = []
        for src in self._src_files:
            src_lines.extend(src.get_src())
        return src_lines

    # def set_src_lines(self, qsps_lines:List[QspsLine]) -> None:
    #     if not qsps_lines: return
    #     self._src_lines = qsps_lines
