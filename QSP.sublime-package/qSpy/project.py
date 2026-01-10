import os, json
from typing import cast, List, Union
from . import plugtypes as ts
from .const import PROJECT_FILE_NAME

class QspProject:
    """ Prepare project to build """
    SCAN_FILES_LOCNAME = 'prv_file'

    def __init__(self, args:ts.SchemeArgs, window_folders:List[ts.Path]) -> None:
        self._args:ts.SchemeArgs = args
        self._window_folders:List[ts.Path] = window_folders

        # Default inits.
        self._root:ts.ProjectScheme = {
            'project': [],
            'preprocessor': 'Off',
            'converter': [],
            'save_temp_files': False
        } # qsp-project.json dict

        self._qgc_path:ts.Path = self._get_qgc()
        self._work_dir:ts.Path = ''
        self._point_file:ts.Path = ''
        
        self._work_dir_init()
        os.chdir(self._work_dir)
        self._project_file:ts.Path = self._project_file_find()

        self._fields_init()
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

    def _work_dir_init(self) -> None:
        """ Work Dir - dir of `qsp-project.json` """
        self._point_file = point_file = cast(ts.Path, self._args.get('point_file', ''))

        if not point_file:
            self._work_dir = self._window_folders[0]
            return

        folder, file = os.path.split(point_file)

        if file == PROJECT_FILE_NAME or not self._window_folders:
            # if this - project-file, or not opened folders in window (single file)
            self._project_file = point_file
            self._work_dir = folder
            return
        
        # point-file exist and folders is open
        for f in self._window_folders:
            try:
                if os.path.commonpath([
                    os.path.abspath(point_file),
                    os.path.abspath(f)
                ]):
                    self._work_dir = f
                    return
            except ValueError as e: # если файлы лежат на разных дисках. TODO: убрать вывод в консоль
                print(f'[203] Different pathes of folder and file. '+
                      f'Error "{str(e)}". path: {point_file}. folder: {f}.')
                continue

        # point-file not in opened windows - this is single file from other project
        self._work_dir = folder    

    def _get_qgc(self) -> ts.Path:
        """ Fast converter on Windows. """
        if self._args.get('platform', '') == 'windows':
            qgc_path = os.path.join(cast(ts.Path, self._args['packages_path']),
                'QSP', 'qgc', 'app', 'QGC.exe')
            if os.path.isfile(qgc_path):
                return qgc_path
        return ''

    def _project_file_find(self) -> ts.Path:
        project_file:ts.Path = os.path.join(self._work_dir, PROJECT_FILE_NAME)
        if os.path.isfile(project_file): return project_file
        return ''

    def _fields_init(self) -> None:
        """ Filling the BuildQSP fields from project_file """
        if self._project_file:
            with open(self._project_file, 'r', encoding='utf-8') as fp:
                self._root = json.load(fp)

        # Preprocessor's mode init.
        self._root['preprocessor'] = self._root.get('preprocessor', 'Off')

        # Set converter path and params
        self._set_converter()

        # Save temp-files Mode
        self._root['save_temp_files'] = self._root.get('save_temp_files', False)

        if self._root['project']: # Absolutize pathes of Modules
            self._abs_project()
        elif self._point_file != self._project_file: # prepare file of project
            # list of modules is empty, build single file:
           self._single_build_project()
        else:
            # point file is project file, but list of modules is empty
            # Project Error
            print('QspProject-Error: Not define any QspModule in project.')
            self._root = {}
            return

        if 'start' in self._root:
            self._root['start'] = os.path.abspath(cast(ts.Path, self._root['start']))
        else:
            self._root['start'] = self._get_first_module()

        # SCANS
        # ASSETS
        ...

        
    def _set_converter(self) -> None:
        """Set converter path and params"""
        converter = cast(Union[ts.Path, List[Union[ts.Path, ts.AppParam]]],
            self._root.get('converter', ''))
        if isinstance(converter, ts.Path):
            c_path = os.path.abspath(converter)
            c_param = ''
        else:
            c_path = os.path.abspath(converter[0])
            c_param = converter[1]
        if not os.path.isfile(c_path):
            # users converter - not exist
            if self._root['preprocessor'] == 'Hard-off' and self._qgc_path:
                # preprocessor hard-off, qgc exist
                self._root['converter'] = [self._qgc_path, c_param]
            else:
                # preprocessor off/on or qgc not exist
                self._root['converter'] = ['qsps_to_qsp', '']
        else:
            self._root['converter'] = [c_path, c_param]

    def _abs_project(self) -> None:
        """ Absolutize pathes of project modules. """
        for module in cast(List[ts.QspModule], self._root['project']):
            # Make module path absolute
            module['module'] = os.path.abspath(cast(ts.Path, module['module']))
            # Make folder paths absolute
            for folder in cast(List[ts.FolderPath], module['folders']):
                folder['path'] = os.path.abspath(folder['path'])
            for file in cast(List[ts.FilePath], module['files']):
                file['path'] = os.path.abspath(file['path'])
    
    def _single_build_project(self) -> None:
        """ Create QspModule for building of single file. """
        game_name:ts.FileName = os.path.splitext(os.path.split(self._point_file)[1])[0]
        module_path:ts.Path = os.path.join(self._work_dir, f'{game_name}.qsp')
        self._root['project'] = [{
            'module': module_path,
            'folders': [{'path': self._work_dir}]
        }]

    def _get_first_module(self) -> ts.Path:
        """Get first game Path in project. """
        project = cast(List[ts.QspModule], self._root['project'])
        module = project[0]
        return cast(ts.Path, module['module'])