# Sorry my Bad English.
import os
import re

if __name__=="__main__":
	from qsp_to_qsps import QspToQsps
	from qsps_to_qsp import NewQspsFile
else:
	from .qsp_to_qsps import QspToQsps
	from .qsps_to_qsp import NewQspsFile

class QspSplitter():
	"""
		Get QSP-file and .qproj file, convert in qsps
		and split qsps in many files, and replace them
		in other folders by .qproj-file mapping.
	"""
	def __init__(self) -> None:
		self.mode:str = 'game' # Literally 'game' or 'txt' (QSP or qsps -files)

		# pathes fields:
		self.qsp_game_path:str = '' # abs path to QSP-file
		self.root_folder_path:str = '' # abs path to folder where sources are lies
		self.file_name:str = '' # QSP or qsps -file name without extension
		self.file_ext:str = '' # QSP or qsps -file extension
		self.qsp_project_file:str = '' # path to .qproj-file for QSP-file
		self.output_folder:str = '' # abs path of output folder for splited files (root fold + file_name)

		self.qsps_file:str = '' # abs path to qsps-file
		
		# data fields:
		self.qsp_to_qsps:QspToQsps = None # object for converting game to qsps
		self.qproj_data:dict = {} # dict[location_name: (placement_folder, file_name)]

	def set_mode(self, new_mode:str) -> None:
		""" Set mode of splitting """
		self.mode = new_mode

	def choose_mode(self, file_ext:str=None) -> None:
		""" Choose mode by extension of file """
		if file_ext: self.file_ext = file_ext
		if self.file_ext in ('.qsp'):
			self.mode = 'game'
		elif self.file_ext in ('.qsps', '.qsp-txt', '.txt-qsp'):
			self.mode = 'txt'

	def set_input_file(self, input_file:str) -> None:
		""" Set pathes of files by mode """
		input_file = os.path.abspath(input_file)
		self.root_folder_path, full_file_name = os.path.split(input_file)
		self.file_name, self.file_ext = os.path.splitext(full_file_name)
		self.output_folder = os.path.join(self.root_folder_path, self.file_name)
		self.qsp_project_file = os.path.join(self.root_folder_path, self.file_name+".qproj")
		if self.mode == 'game':
			self.qsp_game_path = input_file
		elif self.mode == 'txt':
			self.qsps_file = input_file
	
	def split_file(self, input_file:str, mode:str='game') -> None:
		""" Split the common file into separate location-files. """
		if os.path.isfile(input_file):
			self.set_mode(mode)
			self.set_input_file(input_file)
		else:
			print(f'[400] QspSplitter: File {input_file} is not exist.')
			return None
		if self.mode in ('game', 'txt'):
			os.makedirs(self.output_folder, exist_ok=True)
			self.read_qproj() # get output pathes for location placements
			if self.mode == 'game':
				self.split_game()
			else:
				self.split_qsps()
		else:
			print(f'[401] QspSplitter: mode is not setted.')

	@staticmethod
	def replace_bad_symbols(file_name:str) -> str:
		""" Replace invalid symbols in file name. """
		regex = re.compile(r'(&lt;|&gt;|&quot;|[<>*"\\\/:\?|\'])')
		return regex.sub('_', file_name)

	def read_qproj(self) -> None:
		""" Read qproj file and fill dict by folders for locations """
		OPEN_LOCATION = re.compile(r'\s*?<Location name="(.*?)"/>')
		OPEN_FOLDER = re.compile(r'\s*?<Folder name="(.*?)">')
		CLOSE_FOLDER = re.compile(r'\s*?<\/Folder>')
		if not os.path.isfile(self.qsp_project_file):
			return None
		with open(self.qsp_project_file,"r",encoding='utf-8-sig') as fp:
			proj_lines = fp.readlines()
		current_folder = ''
		for line in proj_lines:
			location = OPEN_LOCATION.match(line)
			folder = OPEN_FOLDER.match(line)
			if location:
				loc_name = location.group(1)
				loc_file_name = self.replace_bad_symbols(loc_name)
				if not current_folder:
					output_folder = self.output_folder
				else:
					output_folder = os.path.join(self.output_folder, current_folder)
				self.qproj_data[loc_name] = (output_folder, loc_file_name)
			elif folder:
				fold_name = folder.group(1)
				current_folder = self.replace_bad_symbols(fold_name)
			elif CLOSE_FOLDER.match(line):
				current_folder = ''

	def split_game(self) -> None:
		""" Split QSP-file, convert it, and write locations as files """
		if self.mode != 'game' or not os.path.isfile(self.qsp_game_path):
			return None
		q = self.qsp_to_qsps = QspToQsps()
		q.read_from_file(self.qsp_game_path)
		q.split_qsp()
		count = {}
		for location in q.get_locations():
			output_lines = []
			loc_name = location['name']
			output_lines.append(f'QSP-Game {loc_name}\n\n')
			if loc_name in self.qproj_data:
				fold, file = self.qproj_data[loc_name]
			else:
				fold, file = self.output_folder, loc_name
			file = self.replace_bad_symbols(file)
			output_path = os.path.join(fold, file + '.qsps')
			if not output_path in count: count[output_path] = 0
			if os.path.isfile(output_path):
				count[output_path] += 1
				output_path = os.path.join(fold, f'{file}_{count[output_path]}.qsps')
			os.makedirs(fold, exist_ok=True)
			output_lines.extend(QspToQsps.convert_location(location))
			with open(output_path, 'w', encoding='utf-8') as fp:
				fp.writelines(output_lines)

	def split_qsps(self) -> None:
		""" Split qsps-file and write locations as files """
		if self.mode != 'txt' or not os.path.isfile(self.qsps_file):
			return None
		q = NewQspsFile()
		q.read_from_file(self.qsps_file)
		q.split_to_locations()
		count = {}
		for location in q.get_locations():
			output_lines = []
			loc_name = location.name
			output_lines.append(f'QSP-Game {loc_name}\n\n')
			if loc_name in self.qproj_data:
				fold, file = self.qproj_data[loc_name]
			else:
				fold, file = self.output_folder, loc_name
			output_path = os.path.join(fold, file + '.qsps')
			if not output_path in count: count[output_path] = 0
			if os.path.isfile(output_path):
				count[output_path] += 1
				output_path = os.path.join(fold, f'{file}_{count[output_path]}.qsps')
			os.makedirs(fold, exist_ok=True)
			output_lines.extend(location.get_sources())
			with open(output_path, 'w', encoding='utf-8') as fp:
				fp.writelines(output_lines)

class FinderSplitter():
	"""
		Search and convert n split QSP-files, and/or split qsps-files.
	"""
	def __init__(self):
		self.folder_path = ''
		self.mode = 'both' # 'game', 'txt' or 'both' mode

	def search_n_split(self, folder_path:str, mode='both'):
		self.folder_path = os.path.abspath(folder_path)
		self.mode = mode
		qsp_files_list = []
		qsps_files_list = []
		for fold_or_file in os.listdir(self.folder_path):
			path = os.path.join(self.folder_path, fold_or_file)
			if os.path.isfile(path):
				_, file_ext = os.path.splitext(fold_or_file)
				if file_ext in ('.qsp'):
					qsp_files_list.append(path)
				elif file_ext in ('.qsps', '.qsp-txt', '.txt-qsp'):
					qsps_files_list.append(path)
		if self.mode in ('game', 'both') and qsp_files_list:
			for file in qsp_files_list:
				QspSplitter().split_file(file, mode='game')
		if self.mode in ('txt', 'both') and qsps_files_list:
			for file in qsps_files_list:
				QspSplitter().split_file(file, mode='txt')
	
	def change_mode(self, new_mode:str) -> None:
		""" Change mode of find and split  """
		self.mode = new_mode


# functions for testing
def main():
	import time
	old_time = time.time()

	QspSplitter().split_file('..\\..\\[examples]\\examples_splitter\\driveex.qsp')

	new_time = time.time()
	print(new_time - old_time)

	QspSplitter().split_file('..\\..\\[examples]\\examples_splitter\\basesex.qsps', mode='txt')

	old_time = time.time()
	print(old_time - new_time)

def find_n_split():
	import time
	old_time = time.time()

	FinderSplitter().search_n_split('..\\..\\[examples]\\examples_finder', mode='game')

	new_time = time.time()
	print(new_time - old_time)

if __name__=="__main__":
	# local start of script
	find_n_split()