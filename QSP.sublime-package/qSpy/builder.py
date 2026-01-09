import os
import shutil 
import subprocess
import json
from typing import Dict, Optional, Union, List, Literal, cast

# Importing my modules.
from . import function as qsp
from .moduleqsp import ModuleQSP
# import time

Path = str # file or folder path
FileName = str
LocName = str
QspsLine = str

BuilderArgs = Dict[
	Literal['build', 'run', 'point_file', 'qgc_path'],
	Union[bool, str]
]

FolderPath = Dict[Literal['path'], Path]
FilePath = Dict[Literal['path'], Path]
QspModule = Dict[
	Literal['module', 'folders', 'files'],
	Union[FileName, List[FolderPath], List[FilePath]]
]
AssetsConfig = Dict[
	Literal['output', 'folders', 'files'],
	Union[Path, List[FolderPath], List[FilePath]]
]
ScansConfig = Dict[
	Literal['location', 'folders', 'files'],
	Union[LocName, List[Path]]
]
QspProject = Dict[
	Literal[
		'project', 'start', 'converter', 'player', 'save_temp_files',
		'preprocessor', 'assets', 'scans'
	],
	Union[
		str,
		bool,
		FileName,
		Path,
		List[QspModule],
		List[AssetsConfig],
		ScansConfig
	]
]




class BuildQSP():
	"""
		Procedure of building is need of global name-space, but it is wrong.
		If we make the class ex, we can use class instance fields as global name-space.
		Class BuildQSP — is a name-space for procedure scripts.
	"""
	def __init__(self, modes:BuilderArgs) -> None:
		# Init main fields:
		self.modes:BuilderArgs = modes										 	 # Arguments from sys. Modes of build.
		self.converter:str = ('qgc' if modes.get('qgc_path') else 'qsps_to_qsp') # Converter application path (exe in win).
		self.converter_param:str = ''											 # Converter's parameters (key etc.)
		self.player:str = 'C:\\Program Files\\QSP Classic 5.9.4\\bin\\qspgui.exe'# Player application path (exe in win)

		# Default inits.
		self.root:QspProject = {} # qsp-project.json dict
		self.save_temp_files:bool = False	# save temporary qsps-files or not
		self.modules_paths:List[Path] = []	# Output files' paths (QSP-files, modules)
		self.start_module_path:Path = ''	# File, that start in player.
		self.work_dir:Optional[Path] = None	# workdir - is dir of qsp-project.json

		# self.start_time = time.time()

		self.assets:List[AssetsConfig] = []
		# Scanned files proves location
		self.scan_the_files:bool = False		# Marker of scanning files
		self.scan_files_locname:Optional[LocName] = None	# location name
		self.scan_files_locbody:List[QspsLine] = []	# location body
		self.SCANFILES_LOCNAME = 'prv_file' # constanta of standart locname

		# Init work dir.
		self.work_dir_init()
		
		if self.work_dir is not None:
			# Reinit main fields and init other fields.
			self.fields_init()

	def work_dir_init(self) -> None:
		"""
			Initialise of workdir. If qsp-project.json is not exist,
			workdir sets at dir of point file.
		"""
		# start_time = time.time()
		point_file = cast(Path, self.modes['point_file'])
		project_folder:Path = qsp.search_project_folder(point_file)

		if self.project_file_is_need(project_folder, point_file, self.player):
			# If project_folder is not found, but other
			# conditional is right, generate the new project-file.
			project_folder = os.path.split(point_file)[0]
			self.create_point_project(project_folder, point_file)

		self.set_work_dir(project_folder)

	def set_work_dir(self, work_dir:Optional[Path]=None) -> None:
		""" Set self.work_dir and change work dir """
		self.work_dir = work_dir
		# Change work dir:
		if self.work_dir is not None:
			os.chdir(self.work_dir)

	def fields_init(self) -> None:
		""" Filling the BuildQSP fields from project_file """
		# start_time = time.time()
		if not self.root: # self.root is empty
			# Deserializing project-file:
			project_json = os.path.join(self.work_dir, 'qsp-project.json')
			with open(project_json, 'r', encoding='utf-8') as project_file:
				self.root = json.load(project_file)

		# Get paths to converter and player (not Default)
		if 'converter' in self.root:
			converter = self.root['converter']
			_is_file = lambda path: os.path.isfile(os.path.abspath(path))
			if type(converter) == str:
				if _is_file(converter):
					self.converter = os.path.abspath(converter)
				elif converter == 'qsps_to_qsp':
					self.converter = converter
				self.converter_param = ''
			elif type(converter) == list and _is_file(converter[0]):
				self.converter  = os.path.abspath(converter[0])
				self.converter_param = (converter[1] if len(converter)>1 else '')

		if 'player' in self.root:
			if os.path.isfile(os.path.abspath(self.root['player'])):
				self.player = os.path.abspath(self.root['player'])

		# Save temp-files Mode:
		if ('save_temp_files' in self.root):
			self.save_temp_files = self.root['save_temp_files']

		# Preprocessor's mode init.
		self.root['preprocessor'] = self.root.get('preprocessor', 'Off')

		if ('assets' in self.root):
			self.assets = self.root['assets']

		# Location's of scaned files name init.
		if ('scans' in self.root) and ('start' in self.root):
			# mode is switchon, if folders or files adding
			if 'folders'in self.root['scans'] or 'files' in self.root['scans']:
				self.scan_the_files = True
			# choose name of location
			if 'location' in self.root['scans']:
				self.scan_files_locname = self.root['scans']['location']
			else:
				self.scan_files_locname = self.SCANFILES_LOCNAME
			# if 'destination' in self.root['scans']:
			# 	self.scanned_files_qsps = self.root['scans']['destination']
			# else:
			# 	self.scanned_files_qsps = None

		if 'start' in self.root:
			# Start-file defined. Get from define.
			self.start_module_path = os.path.abspath(self.root['start'])

	def build_and_run(self) -> None:
		self.print_mode()

		if self.modes['build']:
			if self.assets is not None:
				self.copy_assets()

			if self.scan_the_files:
				# Generate location with files-list.
				self.create_scans_loc()
			# Build QSP-files.
			self.build_qsp_files()

		if self.modes['run']:
			# Run Start QSP-file.
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
		
	def copy_assets(self) -> None:
		""" Copy assets from folder and files to output folder """
		for resource in self.assets:
			self.copy_res(resource)
		
	def copy_res(self, resource):
		if not 'output' in resource:
			return
		output = os.path.abspath(resource['output'])
		if not os.path.isdir(output):
			qsp.safe_mk_fold(output)
		if 'folders' in resource:
			for folder in resource['folders']:
				old_fold = os.path.abspath(folder['path'])
				fname = os.path.split(old_fold)[1]
				new_fold = os.path.join(output, fname)
				if os.path.isdir(new_fold):
					shutil.rmtree(new_fold)
				shutil.copytree(old_fold, new_fold)
		if 'files' in resource:
			for file in resource['files']:
				old_file = os.path.abspath(file['path'])
				fname = os.path.split(old_file)[1]
				new_file = os.path.join(output, fname)					
				shutil.copy2(old_file, new_file)
	
	
	def create_scans_loc(self) -> None:
		""" Prepare and creation location-function of scanned files """
		# start_time = time.time()
		found_files = [] # Absolute files paths.
		start_file_folder = os.path.split(self.start_module_path)[0]
		scans = self.root['scans']
		func_name = self.scan_files_locname

		if 'folders' in scans:
			for folder in scans['folders']:
				# Iterate through the folders, comparing the paths with start_file,
				# to understand if the folder lies deeper relative to it.
				sf, f = qsp.compare_paths(start_file_folder, os.path.abspath(folder))
				if sf == '.' or sf == '':
					# Folder relative to path.
					found_files.extend(qsp.get_files_list(folder, filters=[]))
				else:
					# Folder is not relative to path. Is error.
					qsp.write_error_log(f'[102] Folder «{folder}» is not in the project.')

		if 'files' in scans:
			for file in scans['files']:
				sf, f = qsp.compare_paths(start_file_folder,os.path.abspath(file))
				if sf == '':
					found_files.append(os.path.abspath(file))
				else:
					qsp.write_error_log(f'[103] File «{file}» is not in the project.')

		qsp_file_body = [
			f'# {func_name}\n',
			'$args[0] = $args[0]\n',
			'$args[1] = "\n']

		for file in found_files:
			sf, f = qsp.compare_paths(start_file_folder, os.path.abspath(file))
			qsp_file_body.append(f'[{f}]\n')

		qsp_file_body.extend([
			'"\n',
			'result = iif(instr($args[1],"[<<$args[0]>>]")<>0, 1, 0)\n',
			f'- {func_name}\n'])

		self.scan_files_locbody = qsp_file_body

	def build_qsp_files(self):
		# start_time = time.time()
		pp_markers:Dict[str, bool] = {'Initial':True, 'True':True, 'False':False} # Preproc markers, variables.
		project:List[Dict[str, Union[str, list]]] = self.root['project']
		# Get instructions list from 'project'.
		_CONV:str = self.converter
		_PPMODE:str = self.root['preprocessor']
		for instruction in project:
			if _CONV == 'qgc' and _PPMODE == 'Hard-off':
				self.qgc_build(instruction, project)
			elif _CONV == 'qgc':
				self.converter = 'qsps_to_qsp'
				self.qsps_build(instruction, pp_markers, project)
			else:
				self.qsps_build(instruction, pp_markers, project)

	def qsps_build(self, instruction:dict, pp_markers:Dict[str, bool], project:dict) -> None:
		qsp_module = ModuleQSP()
		qsp_module.set_converter(self.converter, self.converter_param)
		if 'files' in instruction:
			for file in instruction['files']:
				qsp_module.extend_by_file(os.path.abspath(file['path']))
		if 'folders' in instruction:
			for path in instruction['folders']:
				qsp_module.extend_by_folder(os.path.abspath(path['path']))
		if ('files' not in instruction) and ('folders' not in instruction):
			qsp_module.extend_by_folder(self.work_dir) # if not pathes, scan all current folder
		if self.scan_the_files:
			qsp_module.extend_by_src(self.scan_files_locbody)
			self.scan_the_files = False
		if 'module' in instruction:
			qsp_module.set_exit_files(instruction['module'])
		else:
			qsp_module.set_exit_files(f'game{project.index(instruction)}.qsp')
			qsp.write_error_log(f'[104] Key «module» not found. Choose export name {qsp_module.output_qsp}.')

		# Build TXT2GAM-file
		# preprocessor work if not Hard-off mode
		if self.root['preprocessor'] != 'Hard-off':
			qsp_module.preprocess_qsps(self.root['preprocessor'], pp_markers)
		qsp_module.extract_qsps()
		# Convert TXT2GAM at `.qsp`
		qsp_module.convert(self.save_temp_files)
		if os.path.isfile(qsp_module.output_qsp):
			self.modules_paths.append(qsp_module.output_qsp)		

	def qgc_build(self, instruction:dict, project:dict) -> None:
		# prepare parameters
		i = [] # pathes to source files and folders
		folder_to_conv = os.path.split(self.modes['qgc_path'])[0]
		root_folder_qgc = os.path.split(folder_to_conv)[0]
		plugin_path = os.path.join(root_folder_qgc, 'plugins', 'a_txt2gam.dll')
		# cc_path = os.path.join(root_folder_qgc, 'plugins', 'a_remove_comments.dll')
		start_qsploc_file = None
		if 'files' in instruction:
			for file in instruction['files']:
				i.append(os.path.abspath(file['path']))
		if i: start_qsploc_file = i[0]
		if 'folders' in instruction:
			for path in instruction['folders']:
				i.append(os.path.abspath(path['path']))
		if ('files' not in instruction) and ('folders' not in instruction):
			i.append(self.work_dir) # if not pathes, scan all current folder
		if start_qsploc_file is None: start_qsploc_file = qsp.get_files_list(i[0])[0]

		if self.scan_the_files:
			scan_files_path = os.path.join(folder_to_conv, 'prv_file.qsps')
			with open(scan_files_path, 'w', encoding='utf-8') as fp:
				fp.writelines(self.scan_files_locbody)
			i.append(scan_files_path)
			self.scan_the_files = False

		if 'module' in instruction:
			module_path = os.path.abspath(instruction['module'])
		else:
			module_path = os.path.abspath(f'game{project.index(instruction)}.qsp')
			qsp.write_error_log(f'[105] Key «module» not found. Choose export name {module_path}.')

		params = '"' +self.modes['qgc_path']+ '"'
		params += f' -m a -r -p "{plugin_path}" -o "{module_path}" -qp4st'
		params += ' -e "qsps" -i ' + ' '.join([f'"{i_}"' for i_ in i])
		if start_qsploc_file is not None: params += f' -im "{start_qsploc_file}"'		

		# Build TXT2GAM-file
		proc = subprocess.run(params, stdout=subprocess.PIPE, shell=True)
		if proc.returncode != 0:
			msg = f'Error of QGC #{proc.returncode}. '
			msg += 'If this Error will be repeat, change "converter" to "qsps_to_qsp".'
			qsp.write_error_log(msg)

		if os.path.isfile(module_path):
			self.modules_paths.append(module_path)

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

