import os
from typing import List
from . import plugtypes as ts
from . import function as qsp

from .tce import TextConstantExtractor, TextConstant, ConstFileContainer

class ProjectTextConstantManager:
    """Извлекатель текстовых констант из проекта."""

    def __init__(self, project_scheme:ts.ProjectScheme) -> None:
        self._root: ts.ProjectScheme = project_scheme
        self._files:List[ts.Path] = []

        self._constants: List[TextConstant] = []
        self._const_files: List[ConstFileContainer] = []

        self._cid_counter:int = 0

    def extract_constants(self) -> List[TextConstant]:
        """Вытаскивает из всех файлов проекта текстовые константы и возвращает в виде списка словарей."""
        self._fill_files_list()
        self._extract_constants()
        return self._constants

    def get_const_files(self) -> List[ConstFileContainer]:
        return self._const_files


    def _fill_files_list(self) -> None:
        """Наполняем список путями ко всем файлам проекта."""
        for instruction in self._root.get('project', []):
            self._extends_by_scheme(instruction)

    def _extract_constants(self) -> None:
        for file_path in self._files:
            tce = TextConstantExtractor(file_path, self._cid_counter)
            self._constants.extend(tce.extract_constants())
            self._const_files.append(tce.get_const_container())
            self._cid_counter = tce.cid_counter()

    def _extends_by_scheme(self, instruction:ts.QspModule) -> None:
        """ Extend ModuleQSP by files from instruction """
        for file in instruction.get('files', []):
            self._extend_by_file(file['path'])
        for path in instruction.get('folders', []):
            self._extend_by_folder(path['path'])

    def _extend_by_folder(self, folder_path:str) -> None:
        """ Add SrcQspsFile-objs by folder-path """
        if not os.path.isdir(folder_path):
            qsp.write_error_log(f'[ModuleQSP:002] Folder don\'t exist. Prove path {folder_path}.')
            return None
        for el in qsp.get_files_list(folder_path):
            self._extend_by_file(el)

    def _extend_by_file(self, file_path:ts.Path) -> None: # file_path:abs_path of file
        """ Add QspsFile by file-path """
        if os.path.isfile(file_path):
            self._files.append(file_path)
        else:
            qsp.write_error_log(f'[TceManager:001] File don\'t exist. Prove path {file_path}.')
