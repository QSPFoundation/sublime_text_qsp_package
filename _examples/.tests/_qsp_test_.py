import os
# import re
# import json
from typing import Dict, Optional, Union, List, cast, Literal
# import time

# Importing my modules from qSpy package.
from qSpy.builder import BuildQSP
# from qSpy.converter import (
# 	QspToQspsBuiltinConv, QspsToQspBuiltinConv,
# 	QspSplitter, FinderSplitter
# )
# from qSpy.workspace import LocHash, QspWorkspace, WorkspacesPlaces
from qSpy import function as qsp
from qSpy.project import QspProject
# Import constants
from qSpy import const

# My typing
from qSpy import plugtypes as ts
Path = ts.Path
Value = Union[bool, str, int, float, List['Value'], Dict[str, 'Value'], None]
CommandArgs = Optional[Dict[str, Value]]

def build(qsp_mode:ts.QspMode = "--br") -> None:
    # Three commands from arguments.
    argv = {
        'file': '.\\qsp-project.json',
        'file_base_name': 'qsp-project', 'file_extension': 'json', 'file_name': 'qsp-project.json',
        'file_path': '.',

        'folder': '.',
        'packages': 'C:\\Users\\aleks\\AppData\\Roaming\\Sublime Text\\Packages',
        'platform': 'Windows',
        
        'project': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\[lib]\\easy.lib.sublime-project',
        'project_base_name': 'easy.lib', 'project_extension': 'sublime-project',
        'project_name': 'easy.lib.sublime-project', 'project_path': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\[lib]'}
    window_folders:List[Path] = [argv['folder']]

    if not ('file' in argv or window_folders):
        # If not point file or opened folder in window (empty window)
        qsp.write_error_log(const.QSP_ERROR_MSG.NEED_SAVE_FILE)
        return None

    # -----------------------------------------------------------------------
    args:ts.SchemeArgs = {}

    args['point_file'] = os.path.abspath(argv.get('file', '')) # - start point for search `qsp-project.json`
    args['platform'] = cast(Literal['windows'], argv['platform'].lower())
    args['packages_path'] = argv['packages']
    # -----------------------------------------------------------------------

    qsp_proj = QspProject(args, window_folders)
    if qsp_proj.scheme_is_wrong():
        qsp.write_error_log(const.QSP_ERROR_MSG.EMPTY_PROJECT)
        return None

    # old_time = time.time()
    builder = BuildQSP(qsp_proj.get_scheme()) # Initialise of Builder.
    if (qsp_mode in ('--br', '--build')): builder.build_project()
    if (qsp_mode in ('--br', '--run')): builder.run_game()

    if not os.path.isfile(qsp_proj.get_project_file()):
        qsp_proj.save_json()

if __name__ == "__main__":
    os.chdir(os.path.split(__file__)[0])
    build('--build')