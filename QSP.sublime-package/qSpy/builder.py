import os#, json
import shutil
import subprocess
from typing import Callable, List, Optional

# Importing my modules.
from . import function as qsp
from .moduleqsp import ModuleQSP
from .preprocessor import QspsPP
from .converter import QspsToQspBuiltinConv, QspsToQspOuterConv, QspsFile
from .const import SCAN_FILES_LOCNAME
from . import plugtypes as ts

# from .preprocessor.pp_ast_printer import AstPrinter
import time

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

		self._save_temp_files:bool = self._root.get('save_temp_files', False)

		# Converter's fields init
		conv = self._root['converter']
		self._conv_api = conv['capi']
		self._conv_path = conv['path']
		self._conv_args = conv['args']

		self._build_handler:Callable[[ts.QspModule], None] = self._qsps_build

		# QGC settings
		self._root_folder_qgc:ts.Path = ''
		self._qgc_plugin:ts.Path = ''

		self._converter = {'builtin': QspsToQspBuiltinConv}.get(self._conv_api, QspsToQspOuterConv)

		# Built-in preprocessor
		pp_switch = self._root['preprocessor']
		self._preprocessor = QspsPP(pp_switch) if pp_switch != 'Hard-off' else None

		# Scanned files proves location
		self._scans = self._root['scans']
		self._scan_file:Optional[QspsFile] = None

		self._start_module = self._root['start']

		self.assets:List[ts.AssetsConfig] = []

	def build_project(self) -> None:
		print(f'Build project. {self._conv_api.upper()} mode.')
		assets = self._root['assets']
		if assets: self._copy_assets(assets)

		if self._scans: self._create_scans_loc()
		# Build QSP-files.
		old = time.time()
		self._build_qsp_modules()
		print(f'Elapsed {time.time() - old}')

	def run_game(self) -> None:
		print('Run file in player.')
		# Run Start QSP-file.
		# TODO: proving the player is exist
		self._run_qsp_file()

	def _run_qsp_file(self) -> None:
		player = self._root.get('player', '')
		if not os.path.isfile(player):
			qsp.write_error_log(f'[106] Path at player is wrong.')
			return

		if not os.path.isfile(self._start_module):
			qsp.write_error_log(f'[107] Start-file "{self._start_module}" is wrong. Don\'t start the game.')
			return
		proc = subprocess.Popen([player, self._start_module])
		# This instruction kill the builder after 100 ms.
		# It necessary to close process in console window,
		# but player must be open above console.
		try:
			proc.wait(0.1)
		except subprocess.TimeoutExpired:
			pass

	def _copy_assets(self, assets:List[ts.AssetsConfig]) -> None:
		""" Copy assets from folder and files to output folder """
		for resource in assets:
			self._copy_res(resource)

	def _copy_res(self, resource:ts.AssetsConfig):
		""" Copy assets to one output folder """
		output = resource.get('output', '')
		if not os.path.isdir(output): qsp.safe_mk_fold(output)
		for folder in resource.get('folders',[]):
			old_fold = folder['path']
			fold_name:ts.FolderName = os.path.split(old_fold)[1]
			new_fold:ts.Path = os.path.join(output, fold_name)
			if os.path.isdir(new_fold):	shutil.rmtree(new_fold)
			shutil.copytree(old_fold, new_fold)
		for file in resource.get('files', []):
			old_file = file['path']
			file_name:ts.FileName = os.path.split(old_file)[1]
			new_file:ts.Path = os.path.join(output, file_name)
			shutil.copy2(old_file, new_file)

	def _create_scans_loc(self) -> None:
		""" Prepare and creation location-function of scanned files """
		# start_time = time.time()
		found_files:List[ts.Path] = [] # Absolute files paths.
		start_file = self._root['start']
		start_file_folder:ts.Path = os.path.split(start_file)[0]
		scans = self._scans
		func_name = scans.get('location', SCAN_FILES_LOCNAME)

		for folder in scans.get('folders', []):
			# Iterate through the folders, comparing the paths with start_file,
			# to understand if the folder lies deeper relative to it.
			if os.path.commonpath([start_file_folder, folder]) == start_file_folder:
				# Folder relative to path.
				found_files.extend(qsp.get_files_list(folder, filters=[]))
			else:
				# Folder is not relative to path. Is error.
				qsp.write_error_log(f'[102] Folder «{folder}» is not in the project.')

		for file in scans.get('files', []):
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
			f'-- {func_name} {"-"*33}\n'])

		self._scan_file = QspsFile(qsp_file_body)

	def _build_qsp_modules(self) -> None:
		# start_time = time.time()
		project = self._root['project']
		# Get instructions list from 'project'.
		for instruction in project:
			self._build_handler(instruction)

	def _qsps_build(self, instruction:ts.QspModule) -> None:
		""" Builtin preprocessor, builtin or outer converter (not qgc) """
		qsp_module = ModuleQSP(instruction)
		module_path = instruction.get('module', '')

		if self._scan_file and module_path == self._start_module:
			qsp_module.add_qsps_file(self._scan_file)
			self._scan_file = None

		# preprocessor work if not Hard-off mode
		if self._preprocessor:
			for src_file in qsp_module.qsps_files():
				src_file.set_src_lines(self._preprocessor.pp_this_lines(src_file.get_src()))
				if self._preprocessor.errored(): print(f'^^^^^^ Error in file: "{src_file.file_path()}"')

		if instruction.get('start_qsploc_file', ''):
			qsp_module.restand_first_loc()

		src_lines = qsp_module.src_lines()

		converter = self._converter(module_path,
									self._save_temp_files, self._conv_path, self._conv_args)
		converter.convert_lines(src_lines)
		converter.save_to_file()
		converter.handle_temp_file()
