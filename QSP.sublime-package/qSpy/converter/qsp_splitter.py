# Sorry my Bad English.
import os
import re

from typing import Dict, List, Literal, Tuple

from .qsp_to_qsps import QspToQspsBuiltinConv, ValidationFormatError
from .qsps_file import QspsFile

from .tps import (
	FileName,
	FolderName,
	LocName,
	Path,
	QspsLine
)

SplitterMode = Literal[
	'game', # QSP-Game format
	'txt'	# qsps-format (txt2gam text-file)
]
FinderMode = Tuple[Literal['game', 'txt'], ...]

PlacementFolder = Path

QProjData = Dict[
	LocName,
	Tuple[PlacementFolder, FileName]
]

_jont = os.path.join
_norm = os.path.normpath

# regexps
OPEN_LOCATION = re.compile(r'\s*?<Location name="(.*?)"/>\s*')
OPEN_FOLDER = re.compile(r'\s*?<Folder name="(.*?)">\s*')
CLOSE_FOLDER = re.compile(r'\s*?<\/Folder>\s*')
COM = re.compile(r'COM\d+', re.IGNORECASE)   # имена локаций QSP регистронезависимы: ловим и `com1`
LPT = re.compile(r'LPT\d+', re.IGNORECASE)
BAD_CHARS = re.compile(r'(&lt;|&gt;|&quot;|[<>*"\\\/:\?\|\'])')

# const
RESERVE_FILE_NAMES = (
	'CON', 'PRN', 'AUX', 'NUL', 'CLOCK$', '_',
)


class QspSplitter():
	"""
		Get QSP-file and .qproj file, convert in qsps
		and split qsps in many files, and replace them
		in other folders by .qproj-file mapping.
	"""
	def __init__(self, mode:SplitterMode = 'game') -> None:
		self._mode:SplitterMode = mode

		# pathes fields:
		self._input_file:Path = ''
		self._root_folder:Path = '' # abs path to folder where sources are lies
		self._qproj_file:Path = '' # path to .qproj-file for QSP-file
		self._output_folder:Path = '' # abs path of output folder for splited files (root fold + file_name)

		# data fields:
		self._qproj_data:QProjData = {}
	
	def split_file(self, input_file:str) -> None:
		""" Split the common file into separate location-files. """
		if not os.path.isfile(input_file):
			print(f'[400] QspSplitter: File {input_file} is not exist.') # TODO: make error
			return

		self._set_pathes(input_file)	
		os.makedirs(self._output_folder, exist_ok=True)

		self._read_qproj() # get output pathes for location placements

		if self._mode == 'game':
			self._split_game()
		else:
			self._split_qsps()

	def _set_pathes(self, input_file:str) -> None:
		""" Set pathes of files by mode """
		input_file = os.path.abspath(input_file)
		self._root_folder, full_file_name = os.path.split(input_file)
		file_name = os.path.splitext(full_file_name)[0]
		self._output_folder = os.path.join(self._root_folder, file_name)
		self._qproj_file = os.path.join(self._root_folder, f"{file_name}.qproj")
		self._input_file = input_file

	def _read_qproj(self) -> None:
		""" Read qproj file and fill dict by folders for locations """
		if not os.path.isfile(self._qproj_file):
			return None
		with open(self._qproj_file,"r",encoding='utf-8-sig') as fp:
			proj_lines = fp.readlines()
		current_folder:FolderName = ''
		for line in proj_lines:
			location = OPEN_LOCATION.match(line)
			if location:
				loc_name:LocName = location.group(1)
				loc_file_name = self.correct_file_name(loc_name)
				output_folder = _norm(_jont(self._output_folder, current_folder))
				self._qproj_data[loc_name] = (output_folder, loc_file_name)
				continue
			folder = OPEN_FOLDER.match(line)
			if folder:
				fold_name = folder.group(1)
				current_folder = self.correct_file_name(fold_name)
				continue
			if CLOSE_FOLDER.match(line):
				current_folder = ''

	def _write_location(self, loc_name:LocName, content_lines:List[QspsLine], count:Dict[Path, int]) -> None:
		""" Write one location to its qsps file: header + content, with dedup over output path. """
		output_lines:List[QspsLine] = [f'QSP-Game {loc_name}\n\n']
		if loc_name in self._qproj_data:
			fold, file = self._qproj_data[loc_name]
		else:
			fold, file = self._output_folder, self.correct_file_name(loc_name)
		base_path = _jont(fold, f'{file}.qsps')
		n = count.get(base_path, 0)                    # старт дедупа с прошлой высокой точки, не с нуля
		output_path = base_path if n == 0 else _jont(fold, f'{file}_{n}.qsps')
		while os.path.isfile(output_path):            # защита от перезаписи: берем первый свободный путь
			n += 1
			output_path = _jont(fold, f'{file}_{n}.qsps')
		count[base_path] = n
		os.makedirs(fold, exist_ok=True)
		output_lines.extend(content_lines)
		with open(output_path, 'w', encoding='utf-8') as fp:
			fp.writelines(output_lines)

	def _split_game(self) -> None:
		""" Split QSP-file, convert it, and write locations as files """
		q = QspToQspsBuiltinConv()
		try:
			q.read_from_file(self._input_file)
			q.split_qsp()
		except ValidationFormatError as e:
			print(e)
			return

		count:Dict[Path, int] = {}

		for location in q.get_locations():
			self._write_location(location['name'], QspToQspsBuiltinConv.convert_location(location), count)

	def _split_qsps(self) -> None:
		""" Split qsps-file and write locations as files """
		q = QspsFile()
		q.read_from_file(self._input_file)
		q.split_to_locations()

		count:Dict[Path, int] = {}

		for location in q.get_locations():
			self._write_location(location.name(), location.get_sources(), count)

	@staticmethod
	def correct_file_name(file_name:str) -> str:
		""" Replace invalid symbols in file name. """
		# Зарезервированные Windows имена регистронезависимы → сверка через .upper()
		if (file_name.upper() in RESERVE_FILE_NAMES or
			COM.match(file_name) or LPT.match(file_name)):
			return f'_{file_name}'
		return BAD_CHARS.sub('_', file_name)

class FinderSplitter():
	"""
		Search and convert n split QSP-files, and/or split qsps-files.
	"""
	def __init__(self, mode:FinderMode = ('game', 'txt')):
		self._folder_path = ''
		self._mode = mode

	def search_n_split(self, folder_path:Path):
		self._folder_path = os.path.abspath(folder_path)
		qsp_files_list:List[Path] = []
		qsps_files_list:List[Path] = []
		for fold_or_file in os.listdir(self._folder_path):
			path = _jont(self._folder_path, fold_or_file)
			if os.path.isfile(path):
				_, file_ext = os.path.splitext(fold_or_file)
				if file_ext in ('.qsp'):
					qsp_files_list.append(path)
				elif file_ext in ('.qsps', '.qsp-txt', '.txt-qsp'):
					qsps_files_list.append(path)
		if 'game' in self._mode and qsp_files_list:
			for file in qsp_files_list:
				QspSplitter('game').split_file(file)
		if 'txt' in self._mode and qsps_files_list:
			for file in qsps_files_list:
				QspSplitter('txt').split_file(file)


