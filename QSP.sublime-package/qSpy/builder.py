import os
import shutil 
import subprocess
import json
from typing import Callable, Union, Tuple, Optional, List, cast

# Importing my modules.
from . import function as qsp
from .moduleqsp import ModuleQSP
from .preprocessor import QspsPP
from .const import CONVERTER
# import time

import plugtypes as ts

Path = ts.Path

class BuildQSP():
	"""
		Procedure of building is need of global name-space, but it is wrong.
		If we make the class ex, we can use class instance fields as global name-space.
		Class BuildQSP — is a name-space for procedure scripts.
	"""
	def __init__(self, project_scheme:ts.ProjectScheme) -> None:

		# Default inits.
		self._root:ts.ProjectScheme = project_scheme # qsp-project.json dict

		# Converter's fields init
		_CONV = cast(List[Union[ts.Path, ts.AppParam]],
					self._root.get('converter', [CONVERTER, '']))
		self._converter:ts.Path = _CONV[0]
		self._conv_args:ts.AppParam = _CONV[1]

		# QGC settings
		self._qgc_plugin:ts.Path = ''
		self._root_folder_qgc:ts.Path = ''
		qgc = cast(bool, self._root.get('qgc', False))

		# Built-in preprocessor
		pp_switch = cast(ts.PpMode, self._root.get('preprocessor'))
		if pp_switch != 'Hard-off':
			self._preprocessor = QspsPP(pp_switch)
			qgc = False
		else:
			self._preprocessor = None

		self._build_handler:Callable[[ts.QspModule], None] = self._qsps_build
		if qgc:
			self._build_handler = self._qgc_build
			exe_fold = os.path.split(_CONV[0])[0] # folder of converter
			self._root_folder_qgc = os.path.split(exe_fold)[0]
			self._qgc_plugin = os.path.join(self._root_folder_qgc, 'plugins', 'a_txt2gam.dll')
		
		# Scanned files proves location
		self._scans = cast(ts.ScansConfig, self._root.get('scans', {}))
		self._scan_files_qsps:List[ts.QspsLine] = []	# location body

		self.assets:List[ts.AssetsConfig] = []

		self._modules_pathes:List[ts.Path] = []

	def build_project(self) -> None:
		print('Build project.')
		assets = cast(List[ts.AssetsConfig], self._root.get('assets', []))
		if assets: self._copy_assets(assets)

		if self._scans: self._create_scans_loc()
		# Build QSP-files.
		self._build_qsp_files()

	def run_game(self) -> None:
		print('Run file in player')
		# Run Start QSP-file.
		# TODO: proving the player is exist
		self.run_qsp_files()

	def get_start_module(self) -> str:
		""" Get file what run in player after building """
		if self.need_build_file():
			# Start-file is not defined, but list of module-files is exist.
			self.start_module_path = self.modules_paths[0]
			qsp.write_error_log(f'[101] Start-file is wrong. Used «{self.start_module_path}» for run.')
		if self.need_point_file():
			# Start-file is not defined, list of build-files is not exist, but run point_file.
			self.start_module_path = self.modes['point_file']
		return self.start_module_path
		
	def _copy_assets(self, assets:List[ts.AssetsConfig]) -> None:
		""" Copy assets from folder and files to output folder """
		for resource in assets:
			self._copy_res(resource)
		
	def _copy_res(self, resource:ts.AssetsConfig):
		""" Copy assets to one output folder """
		output = cast(ts.Path, resource['output'])
		if not os.path.isdir(output): qsp.safe_mk_fold(output)
		for folder in cast(List[ts.FolderPath], resource.get('folders',[])):
			old_fold = folder['path']
			fold_name:ts.FolderName = os.path.split(old_fold)[1]
			new_fold:ts.Path = os.path.join(output, fold_name)
			if os.path.isdir(new_fold):	shutil.rmtree(new_fold)
			shutil.copytree(old_fold, new_fold)
		for file in cast(List[ts.FilePath], resource.get('files', [])):
			old_file = file['path']
			file_name:ts.FileName = os.path.split(old_file)[1]
			new_file:ts.Path = os.path.join(output, file_name)					
			shutil.copy2(old_file, new_file)
	
	def _create_scans_loc(self) -> None:
		""" Prepare and creation location-function of scanned files """
		# start_time = time.time()
		found_files:List[ts.Path] = [] # Absolute files paths.
		start_file = cast(ts.Path, self._root.get('start', ''))
		start_file_folder:ts.FolderName = os.path.split(start_file)[0]
		scans = cast(ts.ScansConfig, self._root['scans'])
		func_name = cast(ts.LocName, scans['location'])

		for folder in cast(List[ts.Path], scans['folders']):
			# Iterate through the folders, comparing the paths with start_file,
			# to understand if the folder lies deeper relative to it.
			if os.path.commonpath([start_file_folder, folder]) == start_file_folder:
				# Folder relative to path.
				found_files.extend(qsp.get_files_list(folder, filters=[]))
			else:
				# Folder is not relative to path. Is error.
				qsp.write_error_log(f'[102] Folder «{folder}» is not in the project.')

		for file in cast(List[ts.Path], scans['files']):
			if os.path.commonpath([start_file_folder, file]) == start_file_folder:
				found_files.append(file)
			else:
				qsp.write_error_log(f'[103] File «{file}» is not in the project.')

		qsp_file_body:List[ts.QspsLine] = [
			f'# {func_name}\n',
			'$args[0] = $args[0]\n',
			'$args[1] = "\n']

		for file in found_files:
			qsp_file_body.append(f'[{os.path.relpath(file, start_file_folder)}]\n')

		qsp_file_body.extend([
			'"\n',
			'result = iif(instr($args[1],"[<<$args[0]>>]")<>0, 1, 0)\n',
			f'- {func_name}\n'])

		self._scan_files_qsps = qsp_file_body

	def _build_qsp_files(self) -> None:
		# start_time = time.time()
		project = cast(List[ts.QspModule], self._root['project'])
		# Get instructions list from 'project'.
		for instruction in project:
			self._build_handler(instruction)

	def _qsps_build(self, instruction:ts.QspModule) -> None:
		qsp_module = ModuleQSP(instruction)
		if self._scans:
			qsp_module.extend_by_src(self._scan_files_qsps)
			self._scans = {}

		# Build TXT2GAM-file
		# preprocessor work if not Hard-off mode
		if self._preprocessor:
			qsp_module.preprocess_qsps(self.root['preprocessor'])
		qsp_module.extract_qsps()
		# Convert TXT2GAM at `.qsp`
		qsp_module.convert(self.save_temp_files)
		if os.path.isfile(qsp_module.output_qsp):
			self.modules_paths.append(qsp_module.output_qsp)		

	def _qgc_build(self, instruction:ts.QspModule) -> None:
		# prepare parameters
		i:List[ts.Path] = [] # pathes to source files and folders
		# cc_path = os.path.join(root_folder_qgc, 'plugins', 'a_remove_comments.dll')
		start_qsploc_file:ts.Path = ''
		for file in cast(List[ts.FilePath], instruction['files']):
			i.append(os.path.abspath(file['path']))
		if i: start_qsploc_file = i[0]
		for path in cast(List[ts.FolderPath], instruction['folders']):
			i.append(os.path.abspath(path['path']))
		if not start_qsploc_file: start_qsploc_file = qsp.get_files_list(i[0])[0]

		if self._scans:
			scan_files_path = os.path.join(self._root_folder_qgc, 'prv_file.qsps')
			with open(scan_files_path, 'w', encoding='utf-8') as fp:
				fp.writelines(self._scan_files_qsps)
			i.append(scan_files_path)
			self._scans = {}

		module_path:ts.Path = os.path.abspath(cast(ts.Path, instruction['module']))
		params:List[str] = []
		params.append(f'"{self._converter}"')
		params.append(f' -m a -r -p "{self._qgc_plugin}" -o "{module_path}" -qp4st')
		params.append(' -e "qsps" -i ')
		params.extend(f'"{i_}"' for i_ in i)
		if start_qsploc_file: params.append(f' -im "{start_qsploc_file}"')

		# Build TXT2GAM-file
		proc = subprocess.run(''.join(params), stdout=subprocess.PIPE, shell=True)
		if proc.returncode != 0:
			msg = f'Error of QGC #{proc.returncode}. '
			msg += 'If this Error will be repeat, change "converter" to "qsps_to_qsp".'
			qsp.write_error_log(msg)

		if os.path.isfile(module_path):
			self._modules_pathes.append(module_path)

	def run_qsp_files(self) -> None:
		if not os.path.isfile(self.player):
			qsp.write_error_log(f'[106] Path at player is wrong. Prove path «{self.player}».')
			return None
		
		start_file = self.get_start_module()

		if not os.path.isfile(start_file):
			qsp.write_error_log(f'[107] Start-file is wrong. Don\'t start the player.')
		else:
			proc = subprocess.Popen([self.player, start_file])
			# This instruction kill the builder after 100 ms.
			# It necessary to close process in console window,
			# but player must be open above console.
			try:
				proc.wait(0.1)
			except subprocess.TimeoutExpired:
				pass

	def need_point_file(self) -> bool:
		"""
			Return True if:
			- start-file not defined
			- point file is '.qsp'
		"""
		return all((
			(not 'start' in self.root) or (not os.path.isfile(self.start_module_path)),
			os.path.splitext(self.modes['point_file'])[1] == '.qsp'))

	def need_build_file(self) -> bool:
		""" 
			Return True if:
			- start-file is not define
			- modules path's list not empty
		"""
		return all((
			(not 'start' in self.root) or (not os.path.isfile(self.start_module_path)),
			self.modules_paths))
	
	def create_point_project(self, project_folder:str, point_file:str) -> None:
		project_dict = self.get_point_project(point_file, self.player)
		project_json = json.dumps(project_dict, indent=4)
		project_file_path = os.path.join(project_folder, 'qsp-project.json')

		self.root = project_dict
		with open(project_file_path, 'w', encoding='utf-8') as file:
			file.write(project_json)
			
		qsp.write_error_log(f'[108] File «{project_file_path}» was created.')

	def print_mode(self) -> None:
		""" Print builder's work mode. """
		if self.modes['build'] and self.modes['run']:
			print("Build and Run Mode")
		elif self.modes['build']:
			print("Build Mode")
		elif self.modes['run']:
			print("Run Mode")

	@staticmethod
	def project_file_is_need(project_folder:str, point_file:str, player_path:str) -> bool:
		"""
			Return True if:
			- project-file not found,
			- point file is '.qsps', 
			- player-path is right.
		"""
		return all((
			project_folder is None,
			os.path.splitext(point_file)[1] == '.qsps',
			os.path.isfile(player_path))) # TODO: Зачем проверять корректность плеера???
			# его можно проверить в момент запуска. Игра может быть собрана, но не запущена

	@staticmethod
	def get_point_project(point_file:str, player:str) -> dict:
		"""	Create standart structure of project-file for start from point_file. """
		game_name = os.path.splitext(os.path.split(point_file)[1])[0]+'.qsp'
		project_dict = {
			"project":
			[
				{
					"module": game_name,
					"files":
					[
						{"path": point_file}
					]
				}
			],
			"start": game_name,
			"player": player
		}
		return project_dict

