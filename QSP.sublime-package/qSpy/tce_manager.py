from typing import List
from . import plugtypes as ts

from .tce import TextConstantExtractor, TextConstant
from .moduleqsp import ModuleQSP

class ProjectTextConstantManager:
    """Извлекатель текстовых констант из проекта."""

    def __init__(self, project_scheme:ts.ProjectScheme) -> None:
        self._root: ts.ProjectScheme = project_scheme
        self._files:List[ts.Path] = []

        self._constants: List[TextConstant] = []

    def extract_constants(self) -> List[TextConstant]:
        """Вытаскивает из всех файлов проекта текстовые константы и возвращает в виде списка словарей."""
        self._fill_files_list()
        self._extract_constants()
        return self._constants

    def _fill_files_list(self) -> None:
        """Наполняем список путями ко всем файлам проекта."""
        for instructions in self._root.get('project', []):
            self._upd_files_list_by_module(instructions)

    def _upd_files_list_by_module(self, instruction:ts.QspModule) -> None:
        """Добавляем в список пути к файлам отдельного модуля."""
        qsp_module = ModuleQSP(instruction)
        self._files.extend(qsp_module.files_paths())

    def _extract_constants(self) -> None:
        for file_path in self._files:
            tce = TextConstantExtractor(file_path)
            self._constants.extend(tce.extract_constants())
