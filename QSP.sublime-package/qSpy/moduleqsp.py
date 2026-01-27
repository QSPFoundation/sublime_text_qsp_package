import os
import subprocess
from typing import List, Literal, Dict, cast

from . import function as qsp
from .converter.qsps_file import QspsFile
from .converter.tps import (
    QspsLine
)
import plugtypes as ts
# import time

class ModuleQSP():

    def __init__(self, scheme:ts.QspModule) -> None:

        # main settings
        self._scheme:ts.QspModule = scheme

        self._output_qsp:ts.Path = ''        # path of output QSP-file (module)
        self._output_txt:ts.Path = ''        # path of temp file in txt2gam format
        self._set_output_files()

        self._src_files:List[QspsFile] = []
        self._extends_by_scheme()

        # self.code_system = 'utf-8'

        self._src_lines:List[QspsLine] = []    # all strings of module code
        # self.start_time = start_time
    
    def extend_by_file(self, file_path:str) -> None: # file_path:abs_path of file
        """ Add QspsFile by file-path """
        if os.path.isfile(file_path):
            src = QspsFile()
            src.read_from_file(file_path)
            self._src_files.append(src)
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

    def _set_output_files(self) -> None:
        """
            Set output module (game) file path and temp-file (txt) path.
        """
        self._output_qsp = cast(ts.Path, self._scheme['module'])
        self._output_txt = os.path.splitext(self._output_qsp)[0]+".txt"

    def _extends_by_scheme(self) -> None:
        """ Extend ModuleQSP by files from instruction """
        for file in cast(List[ts.FilePath], self._scheme['files']):
            self.extend_by_file(file['path'])
        for path in cast(List[ts.FolderPath], self._scheme['folders']):
            self.extend_by_folder(path['path'])

    # def choose_code_system(self) -> str:
    #     """ utf-8 for built-in converter, utf-16-le for txt2gam """
    #     # TODO: txt2gam поддерживает utf-8. Можно убрать выбор кодировки.
    #     return ('utf-8' if self.converter == 'qsps_to_qsp' else 'utf-16-le')

    def qsps_files(self) -> List[QspsFile]:
        """ Return list of all Qsps-Files. """
        return self._src_files

    def src_to_text(self) -> str:
        """ Get outer text of module """
        text:List[str] = []
        for src in self.src_qsps_file:
            text.extend(src.get_source())
            text.append('\n')
        return ''.join(text)

    def save_temp_file(self) -> None:
        """ Save temp file of module before converting by txt2gam, or for checkout. """
        # если папка не создана, нужно её создать
        path_folder = os.path.split(self.output_txt)[0]
        os.makedirs(path_folder, exist_ok=True)
        text = self.src_to_text()
        code_system = self.choose_code_system()
        # необходимо записывать файл в кодировке utf-16le, txt2gam версии 0.1.1 понимает её
        text = text.encode(code_system, 'ignore').decode(code_system,'ignore')
        with open(self.output_txt, 'w', encoding=code_system) as file:
            file.write(text)

    def src_lines(self) -> List[QspsLine]:
        """ From qsps-files return sources lines and add to module source """
        self._src_lines.clear()
        for src in self._src_files:
            self._src_lines.extend(src.get_src())
        return self._src_lines

    def set_src_lines(self, qsps_lines:List[QspsLine]) -> None:
        if not qsps_lines: return
        self._src_lines = qsps_lines

    def convert(self, save_temp_file:bool) -> None:
        """ Convert sources and save module to file """

        # TODO:
            # Converter REPLACE TO BUILDER!!! ????? Подумать!!!
        # TODO:

        # start_time = time.time()
        if self.converter == 'qsps_to_qsp':
            qsps_file = QspsFile()
            qsps_file.set_file_source(self.qsps_code)
            # print(f'Module.newqsps {time.time() - start_time}, {time.time() - self.start_time}')
            qsps_file.split_to_locations()
            qsps_file.to_qsp()
            # print(f'Module.convert {time.time() - start_time}, {time.time() - self.start_time}')
            qsps_file.save_to_file(self.output_qsp)
            # print(f'Module.save_qsp {time.time() - start_time}, {time.time() - self.start_time}')
            if save_temp_file: self.save_temp_file()
            # print(f'Module.temp {time.time() - start_time}, {time.time() - self.start_time}')
        else:
            self.save_temp_file()
            _run = [self.converter, self.output_txt, self.output_qsp, self.converter_param]
            subprocess.run(_run, stdout=subprocess.PIPE)
            if not save_temp_file:
                os.remove(self.output_txt)
