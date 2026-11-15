import os, json
from typing import List
from . import plugtypes as ts
from .const import PROJECT_FILE_NAME, CONVERTER, SCAN_FILES_LOCNAME

class _SchemeProvingError(Exception):

    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message

    def __str__(self) -> str:
        return f"QspProject Error! {self._message}"

class QspProject:
    """ Prepare project to build """


    def __init__(self, args:ts.SchemeArgs, window_folders:List[ts.Path]) -> None:
        self._args:ts.SchemeArgs = args
        self._window_folders:List[ts.Path] = window_folders

        # Default inits.
        self._json:ts.JsonScheme = {} # qsp-project.json dict
        self._root:ts.ProjectScheme = { # hard scheme of project
            'project': [],
            'start': '',
            'player': '',
            'player_error': '',
            'converter': {
                'capi': 'builtin',
                'path': '',
                'args': ''
            },
            'save_temp_files': False,
            'preprocessor': 'Off',
            'assets': [],
            'scans': {}
        }
        self._scheme_is_right:bool = False

        try:
            self._work_dir:ts.Path = ''
            self._point_file:ts.Path = ''

            self._work_dir_init()
            os.chdir(self._work_dir)

            self._project_file:ts.Path = self._project_file_find()

            self._fields_init()
            self._scheme_is_right = True
        except _SchemeProvingError as e:
            print(str(e))

    def get_project_file(self) -> ts.Path:
        """Project file path"""
        return self._project_file

    def get_work_dir(self) -> ts.Path:
        return self._work_dir

    def get_json(self) -> ts.JsonScheme:
        return self._json

    def save_json(self) -> None:
        if not self._project_file: return
        with open(self._project_file, 'w', encoding='utf-8') as fp:
            json.dump(self._json, fp, ensure_ascii=False, indent=4)

    def get_scheme(self) -> ts.ProjectScheme:
        return self._root

    def scheme_is_wrong(self) -> bool:
        return not self._scheme_is_right

    def _work_dir_init(self) -> None:
        """ Work Dir - dir of `qsp-project.json` """
        self._point_file = point_file = self._args.get('point_file', '')

        if not point_file:
            if not self._window_folders:
                # окно без папок и без point_file: рабочий каталог определить нечем (2.9)
                raise _SchemeProvingError(
                    'No folders opened in window and no point_file: work dir is undefined.')
            self._work_dir = self._window_folders[0]
            return

        folder, file_name = os.path.split(point_file)

        if file_name == PROJECT_FILE_NAME or not self._window_folders:
            # if this - project-file, or not opened folders in window (single file)
            self._work_dir = folder
            return

        # point-file exist and folders is open
        for f in self._window_folders:
            try:
                if os.path.commonpath([
                    os.path.abspath(point_file),
                    os.path.abspath(f)
                ]):
                    if os.path.isfile(os.path.join(f, PROJECT_FILE_NAME)):
                        self._work_dir = f
                        return
                    else:
                        # если файл проекта не найден в папке, в которой лежит поинт-файл,
                        # ищем вверх от поинт-файла. Это костыль для старых реализаций.
                        spf = self.search_project_folder(point_file, f)
                        if spf:
                            self._work_dir = spf
                            return
                        else:
                            # файл проекта не найден, хотя мы искали от поинт-файла, однако
                            # поинт-файл принадлежит найденной папке. Значит собираем проект
                            # из всех файлов обнаруженной папки
                            self._work_dir = f
                            return
            except ValueError as e: # если файлы лежат на разных дисках. TODO: убрать вывод в консоль
                print(f'QspProject Error! [203] Different pathes of folder and file. '+
                      f'Error "{str(e)}". path: {point_file}. folder: {f}.')
                continue

        # point-file not in opened folders - this is single file from other project
        self._work_dir = folder

    def _project_file_find(self) -> ts.Path:
        project_file:ts.Path = os.path.join(self._work_dir, PROJECT_FILE_NAME)
        if os.path.isfile(project_file): return project_file
        return ''

    def _fields_init(self) -> None:
        """ Filling the BuildQSP fields from project_file """
        if self._project_file:
            with open(self._project_file, 'r', encoding='utf-8') as fp:
                self._json = json.load(fp)
        # Preprocessor's mode init.
        self._root['preprocessor'] = self._json.get('preprocessor', 'Off')

        # Set converter path and params
        if self._args.get('qsp_mode', '--br') != '--run':
            self._set_converter()
        # Set player path and params
        self._set_player()

        # Save temp-files Mode
        self._root['save_temp_files'] = self._json.get('save_temp_files', False)

        project = self._json.get('project', [])
        if not project:
            # not exist scheme for building
            if self._project_file:
                # project file is broken!
                raise _SchemeProvingError('qsp-project.json is broken. Not found key "project"!')
            elif self._project_file == self._point_file:
                # folders opened, and point and project are not exist.
                self._work_dir_project()
            else:
                # point file exist, project file not exist
                self._single_build_project()
        else:
            # scheme of building is exist. Absing path of modules:
            self._abs_project_pathes(project)

        start = self._json.get('start', '')
        if start:
            self._root['start'] = os.path.abspath(start)
        else:
            self._root['start'] = self._get_first_module()
            self._json['start'] = os.path.relpath(self._root['start'], self._work_dir)

        # SCANS
        if 'scans' in self._json: self._set_scans()

        # ASSETS
        if 'assets' in self._json: self._set_assets()

    def _set_converter(self) -> None:
        from_project = 'converter' in self._json
        source = 'converter in qsp-project.json' if from_project else 'converter_path in QSP.sublime-settings'
        raw_converter = self._json.get('converter', self._args.get('converter_path', ''))
        c_param = ''
        if from_project and isinstance(raw_converter, list):
            if len(raw_converter) != 2:
                raise _SchemeProvingError(f'{source}: expected [path, parameters] with two strings.')
            c_path, c_param = raw_converter
            if not isinstance(c_path, str) or not isinstance(c_param, str):
                raise _SchemeProvingError(f'{source}: expected [path, parameters] with two strings.')
        else:
            c_path = raw_converter
        if raw_converter == CONVERTER:
            return
        path = self._resolve_executable(c_path, source, from_project)
        if path:
            self._root['converter'] = {'capi': 'outer', 'path': path, 'args': c_param}

    def _set_player(self) -> None:
        from_project = 'player' in self._json
        source = 'player in qsp-project.json' if from_project else 'player_path in QSP.sublime-settings'
        player = self._json.get('player', self._args.get('player_path', ''))
        try:
            self._root['player'] = self._resolve_executable(player, source, from_project)
        except _SchemeProvingError as error:
            self._root['player_error'] = str(error)

    def _resolve_executable(self, value:object, source:str, from_project:bool) -> ts.Path:
        if not isinstance(value, str):
            raise _SchemeProvingError(f'{source}: expected a path string.')
        if not value:
            return ''
        if '\x00' in value:
            raise _SchemeProvingError(f'{source}: invalid path {value!r}.')
        path = os.path.expanduser(value)
        if os.path.isabs(path):
            resolved = path
        elif from_project and os.path.isfile(os.path.join(self._work_dir, path)):
            resolved = os.path.join(self._work_dir, path)
        elif os.path.dirname(path) or os.path.splitdrive(path)[0]:
            if not from_project:
                raise _SchemeProvingError(f'{source}: use an absolute path, ~ or a command from PATH: {value!r}.')
            resolved = os.path.join(self._work_dir, path)
        else:
            resolved = self._find_executable_in_path(path)
        if not resolved or not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
            raise _SchemeProvingError(f'{source}: executable not found or not executable: {value!r}.')
        return os.path.abspath(resolved)

    @staticmethod
    def _find_executable_in_path(name:str) -> ts.Path:
        # shutil.which implicitly searches cwd on older Windows Python runtimes.
        suffixes = ['']
        if os.name == 'nt':
            suffixes.extend(ext for ext in os.environ.get('PATHEXT', '.COM;.EXE;.BAT;.CMD').split(os.pathsep) if ext)
        for folder in os.get_exec_path():
            if not folder:
                continue
            for suffix in suffixes:
                candidate = os.path.abspath(os.path.join(folder, name + suffix))
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
        return ''

    def _abs_project_pathes(self, json_proj:List[ts.QspModule]) -> None:
        """ Absolutize pathes of project modules. """
        files_or_folders:bool = False
        r = self._root['project'] = []
        def _x(c:int) -> str:
            return '0'*(4-len(str(c)))+str(c)
        for i, module in enumerate(json_proj):
            # Make module path absolute
            module_name = module.get('module', '')
            if not module_name:
                module_name = f'game_{_x(i)}.qsp'
                print(f'QspProject Error: Key "module" not found. Choose module name "{module_name}".')
            module['module'] = os.path.relpath(module_name, self._work_dir) # relative in json struct
            rm:ts.QspModule = {
                'module': os.path.abspath(module_name),
                'folders': [],
                'files': [],
                'start_qsploc_file': ''
            }
            r.append(rm)
            # Make folder paths absolute
            for folder in module.get('folders', []):
                excl = folder.get('exclude_pathes') or []
                abs_excl = [os.path.abspath(os.path.join(self._work_dir, p)) for p in excl]
                rm['folders'].append({'path': os.path.abspath(folder['path']), 'exclude_pathes': abs_excl})
                files_or_folders = True
            for file in module.get('files', []):
                rm['files'].append({'path': os.path.abspath(file['path'])})
                files_or_folders = True
            start_file = module.get('start_qsploc_file', '')
            if start_file: rm['start_qsploc_file'] = os.path.abspath(start_file)

        if not files_or_folders:
            raise _SchemeProvingError('Not Qsp-module\'s schemes in qsp-project.json.')

    def _single_build_project(self) -> None:
        """ Create QspModule for building of single file. """
        game_name:ts.FileName = os.path.splitext(os.path.basename(self._point_file))[0]
        self._root['project'] = [{
            'module': os.path.join(self._work_dir, f'{game_name}.qsp'),
            'files': [{'path': self._point_file}]
        }]
        self._json['project'] = [{
            'module': os.path.join('.', f'{game_name}.qsp'),
            'files': [{'path': os.path.relpath(self._point_file, self._work_dir)}]
        }]

    def _work_dir_project(self) -> None:
        """ Project build from all work dir. """
        self._root['project'] = [{
            'module': os.path.join(self._work_dir, 'game.qsp'),
            'folders': [{'path': self._work_dir}]
        }]
        self._json['project'] = [{
            'module': os.path.join('.', 'game.qsp'),
            'folders': [{'path': '.'}]
        }]

    def _get_first_module(self) -> ts.Path:
        """Get first game Path in project. """
        return self._root['project'][0].get('module', '') # impossible return empty str

    def _set_scans(self) -> None:
        """ Init location with scanned files. """
        scans = self._json.get('scans', {})
        root_scans = self._root['scans']

        folders:List[ts.Path] = []
        for folder in scans.get('folders', []):
            folders.append(os.path.abspath(folder))

        files:List[ts.Path] = []
        for file in scans.get('files', []):
            files.append(os.path.abspath(file))

        if not (folders or files): return # not folder and files for scan

        root_scans['files'] = files
        root_scans['folders'] = folders

        root_scans['location'] = scans.get('location', SCAN_FILES_LOCNAME)

    def _set_assets(self) -> None:
        assets = self._json.get('assets', [])

        out_assets:List[ts.AssetsConfig] = []
        for resource in assets:
            r = self._abs_resource(resource)
            if r: out_assets.append(r)

        if not out_assets: return

        self._root['assets'] = out_assets

    def _abs_resource(self, res:ts.AssetsConfig) -> ts.AssetsConfig:

        if not 'output' in res: return {}

        folders:List[ts.FolderPath] = []
        for folder in res.get('folders', []):
            folders.append({'path': os.path.abspath(folder['path'])})

        files:List[ts.FilePath] = []
        for file in res.get('files', []):
            files.append({'path':os.path.abspath(file['path'])})

        if not (folders or files): return {}

        out_res:ts.AssetsConfig = {}

        out_res['files'] = files
        out_res['folders'] = folders
        out_res['output'] = os.path.abspath(res['output'])

        return out_res

    @staticmethod
    def search_project_folder(point_file:ts.AbsPath, edge_folder:ts.AbsPath) -> ts.AbsPath:
        """
            Find project-file and return folder path whith project.
            In other return None.
        """
        if not os.path.isfile(point_file): raise _SchemeProvingError(f'File "{point_file} is not exist.')
        pf = os.path.split(point_file)[0]
        while not os.path.isfile(os.path.join(pf, PROJECT_FILE_NAME)):
            if os.path.abspath(pf) == os.path.abspath(edge_folder) or os.path.ismount(pf):
                raise _SchemeProvingError(f'"{PROJECT_FILE_NAME}" not found. Prove path "{point_file}".')
            pf = os.path.split(pf)[0]
        else:
            return pf
