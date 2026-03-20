import os
import json
from typing import List, cast, Literal
# import time
if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
# Importing my modules from qSpy package.
from qSpy.tce_manager import ProjectTextConstantManager, TextConstantExtractor
from qSpy import plugtypes as ts
from qSpy.project import QspProject

def main():
    argv = {
            'file': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\Denny VS Badboys\\qsp-project.json',
            'file_base_name': 'qsp-project', 'file_extension': 'json', 'file_name': 'qsp-project.json',
            'file_path': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\Denny VS Badboys',

            'folder': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\Denny VS Badboys',
            'packages': 'C:\\Users\\aleks\\AppData\\Roaming\\Sublime Text\\Packages',
            'platform': 'Windows',

            'project': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\Denny VS Badboys\\avs.project.sublime-project',
            'project_base_name': 'avs.project', 'project_extension': 'sublime-project',
            'project_name': 'avs.project.sublime-project', 'project_path': 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\Denny VS Badboys'}
    window_folders:List[ts.Path] = [argv['folder']]

    # -----------------------------------------------------------------------
    args:ts.SchemeArgs = {}

    args['point_file'] = os.path.abspath(argv.get('file', '')) # - start point for search `qsp-project.json`
    args['platform'] = cast(Literal['windows'], argv['platform'].lower())
    args['packages_path'] = argv['packages']
    # -----------------------------------------------------------------------

    qsp_proj = QspProject(args, window_folders)
    if qsp_proj.scheme_is_wrong():
        print('Scheme is wrong')

    tcem = ProjectTextConstantManager(qsp_proj.get_scheme())
    consts = tcem.extract_constants()
    files = tcem.get_const_files()

    output_file = os.path.join(os.path.split(args['point_file'])[0], 'const_output.json')
    const_file = os.path.join(os.path.split(args['point_file'])[0], 'const_file.json')

    with open(output_file, 'w', encoding= 'utf-8') as fp:
        json.dump(consts, fp, indent=4, ensure_ascii=False)

    with open(const_file, 'w', encoding= 'utf-8') as fp:
        json.dump(files, fp, indent=4, ensure_ascii=False)

def one():
    # denny = 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\Denny VS Badboys\\[source]\\qsps\\00_start.qsps'
    dialog = 'D:\\my\\GameDev\\QuestSoftPlayer\\games\\[lib]\\easy.dialog\\[source]\\_interpretator\\start.qsps'
    tce = TextConstantExtractor(dialog)

    with open('const_output.json', 'w', encoding= 'utf-8') as fp:
        json.dump(tce.extract_constants(), fp, ensure_ascii=False)

    with open('const_file.json', 'w', encoding= 'utf-8') as fp:
        json.dump(tce.get_const_container(), fp, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
