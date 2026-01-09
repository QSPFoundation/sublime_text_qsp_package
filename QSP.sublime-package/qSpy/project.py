import os, json
from typing import cast, List, Optional
from . import plugtypes as ts
from .const import PROJECT_FILE_NAME

class QspProject:
    """ Prepare project to build """

    def __init__(self, args:ts.SchemeArgs, window_folders:List[ts.Path]) -> None:
        self._args:ts.SchemeArgs = args
        self._window_folders:List[ts.Path] = window_folders

        # Default inits.
        self._root:ts.ProjectScheme = {} # qsp-project.json dict

        self._qgc_path:ts.Path = self._get_qgc()
        self.work_dir:ts.Path = self._work_dir_init()
        # Билдеру для сборки нужна информация
        # список модулей,
        # Путь к альтернативному конвертеру
        # Путь к плееру
        # перенос ассетов
        # обработка препроцессором
        # и другая информация из файла проектов.
        

        ...

    def get_scheme(self) -> ts.ProjectScheme:
        return self._root

    def _work_dir_init(self) -> ts.Path:
        """ work_dir - dir of qsp-project.json """
        point_file = cast(ts.Path, self._args.get('point_file', ''))

        if not point_file:
            return self._window_folders[0]

        folder, file = os.path.split(point_file)

        if file == PROJECT_FILE_NAME or not self._window_folders:
            # if this - project-file, or not opened folders in window (single file)
            return folder
        
        # point-file exist and folders is open
        for f in self._window_folders:
            try:
                if os.path.commonpath([
                    os.path.abspath(point_file),
                    os.path.abspath(f)
                ]): return f
            except ValueError as e: # если файлы лежат на разных дисках. TODO: убрать вывод в консоль
                print(f'[203] Different pathes of folder and file. '+
                      f'Error "{str(e)}". path: {point_file}. folder: {f}.')
                continue

        # point-file not in opened windows - this is single file from other project
        return folder      

    def _get_qgc(self) -> ts.Path:
        """ Fast converter on Windows. """
        if self._args.get('platform', '') == 'windows':
            qgc_path = os.path.join(cast(ts.Path, self._args['packages_path']),
                'QSP', 'qgc', 'app', 'QGC.exe')
            if os.path.isfile(qgc_path):
                return qgc_path
        return ''
