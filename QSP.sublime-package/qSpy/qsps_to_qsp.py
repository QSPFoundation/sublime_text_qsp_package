# Converter qsps-files (only UTF-8) into game files `.qsp`.
# stand `file_path` and run script for getting QSP-format file.

import os
import re
import concurrent.futures
from typing import List, Dict

if __name__ == "__main__":
	from function import (del_first_pref)
	from pp import pp_this_lines
else:
	from .function import (del_first_pref)
	from .pp import pp_this_lines
# import time

# constants:
QSP_CODREMOV = 5 # const of cyphering
# regexps:
LOCATION_START = re.compile(r'^\#\s*(.+)$')
LOCATION_END = re.compile(r'^\-\-(.*)$')
BASE_OPEN = re.compile(r'^\! BASE$')
BASE_CLOSE = re.compile(r'^\! END BASE$')
PRINT_STRING = re.compile(r'^\*P\b')
PRINT_LINE = re.compile(r'^\*PL\b')
ACTION_START = re.compile(r'^ACT\b')
ACTION_END = re.compile(r'^END\b')
IMPLICIT_OPERATOR = re.compile(r'^("|\')')

class NewQspLocation():
	"""
		qsp-locations from qsps-file
	"""
	def __init__(self, name:str, code:list=None) -> None:
		""" Initialise QSP-location """
		self.name:str = name							# location name qsps
		self.name_region:tuple = ()	# tuple[start, end] # location name in regions
		self.code:list = ([] if code == None else code)	# location code qsps
		self.base_code:list = []	# base code (qsps lines of base acts and desc)
		self.base_description:str = '' # concatenate strings of base descs in text-format
		self.base_actions:list = [] # list of base actions dicts
			# actions format
			# {
			# 	'image': '',
			# 	'name': '',
			#	'code': []
			# }
		self.encode_name:str = ''	# decode in QSP-format location name
		self.encode_desc:str = ''	# decode in QSP-format location description
		self.encode_actions:list = [] # list of decode in QSP-format location actions
		self.encode_code:str = ''	# decode in QSP-format location code

		self.char_cache = {}		

	def change_name(self, new_name:str) -> None:
		""" Set location name """
		self.name = new_name

	def change_region(self, new_region:tuple) -> None:
		""" Set location name region """
		self.name_region = new_region

	def change_code(self, new_code:list) -> None:
		""" Set location code. """
		self.code = new_code

	def change_cache(self, new_cache:dict) -> None:
		self.char_cache = new_cache

	def add_code_line(self, code_line:str) -> None:
		self.code.append(code_line)

	def encode(self) -> None:
		""" Decode parts of location. """
		self.encode_name = NewQspsFile.encode_qsps_line(self.name, self.char_cache)
		self.encode_desc = NewQspsFile.encode_qsps_line(self.base_description, self.char_cache)
		self.encode_code = NewQspsFile.encode_qsps_line((''.join(self.code))[:-1].replace('\n', '\r\n'), self.char_cache)
		for action in self.base_actions:
			encode_action_lines = []
			encode_action_lines.append(NewQspsFile.encode_qsps_line(action['image'], self.char_cache))
			encode_action_lines.append('\n')
			encode_action_lines.append(NewQspsFile.encode_qsps_line(action['name'], self.char_cache))
			encode_action_lines.append('\n')
			action_code = ''.join(del_first_pref(action['code']))
			encode_action_lines.append(NewQspsFile.encode_qsps_line(action_code[:-1].replace('\n', '\r\n'), self.char_cache))
			encode_action_lines.append('\n')
			self.encode_actions.append(''.join(encode_action_lines))

	def get_qsp(self) -> list:
		""" Get QSP-format location """
		qsp = []
		qsp.append(self.encode_name + '\n')
		qsp.append(self.encode_desc + '\n')
		qsp.append(self.encode_code + '\n')
		qsp.append(NewQspsFile.encode_qsps_line(str(len(self.encode_actions)), self.char_cache) + '\n')
		qsp.extend(self.encode_actions)
		return qsp

	def extract_base(self) -> None:
		""" Extract base from location code """
		mode = {
			'open-base': False,
			'open-string': '',
		}
		base_lines = []
		for i, qsps_line in enumerate(self.code[:]):
			if mode['open-base']:
				self.code[i] = None # remove from other code
				if mode['open-string'] == '' and BASE_CLOSE.search(qsps_line):	
					mode['open-base'] = False
					break
				base_lines.append(qsps_line)
				NewQspsFile.parse_string(qsps_line, mode)
				continue
			if mode['open-string'] == '' and BASE_OPEN.search(qsps_line):
				mode['open-base'] = True
				self.code[i] = None
			else:
				NewQspsFile.parse_string(qsps_line, mode)

		if base_lines: self.base_code = base_lines
		self.code = [line for line in self.code if line is not None]

	def split_base(self) -> None:
		""" Split base code to description and actions """
		def _string_to_desc(line:str, mode:dict, opened:str) -> None:
			need = ('"', "'") # ожидаем кавчки
			valid = (" ", "\t") # допустимые символы
			new_line = '\n' if opened in ('open-pl', 'open-implicit') else ''
			base_description_chars = []
			for i, char in enumerate(line):
				if mode[opened]:
					if char != mode['open-string']:
						base_description_chars.append(char)
					elif (i < len(line)-1 and line[i+1] == mode['open-string']):
						continue
					elif (i > 0 and line[i-1] == mode['open-string']):
						# символ кавычки экранирован,значит его тоже можно в описание
						base_description_chars.append(char)
					else: # char = open-string и соседние символы другие
						# закрываем набранное
						base_description_chars.append(new_line)
						mode[opened] = False
						mode['open-string'] = ''
						break
				else:
					# пока не открыт набор в описание
					if char in need:
						# нашли ожидаемый символ, открываем набор
						mode['open-string'] = char
						mode[opened] = True
					elif not char in valid:
						# найден недопустимый символ
						break
			self.base_description += ''.join(base_description_chars)

		def _string_to_act(line:str, mode:dict, base_act_buffer:dict) -> None:
			need = ('"', "'") # ожидаем кавчки
			valid = (" ", "\t") # допустимые символы
			stage = 'need name'
			for i, char in enumerate(line):
				if mode['action-name']:
					# название найдено, набираем
					if char != mode['open-string']:
						base_act_buffer['name'] += char
					elif (i < len(line)-1 and line[i+1] == mode['open-string']):
						continue
					elif (i > 0 and line[i-1] == mode['open-string']):
						# символ кавычки экранирован,значит его тоже можно в описание
						base_act_buffer['name'] += char
					else: # char = open-string и соседние символы другие
						# закрываем набранное
						mode['action-name'] = False
						mode['open-string'] = ''
						stage = 'need prev image'
						need = (",", ':')
						valid = (" ", "\t")
				elif mode['action-image']:
					# изображение найдено, набираем
					if char != mode['open-string']:
						base_act_buffer['image'] += char
					elif (i < len(line)-1 and line[i+1] == mode['open-string']):
						continue
					elif (i > 0 and line[i-1] == mode['open-string']):
						# символ кавычки экранирован,значит его тоже можно в описание
						base_act_buffer['image'] += char
					else: # char = open-string и соседние символы другие
						# закрываем набранное
						mode['action-image'] = False
						mode['open-string'] = ''
						stage = 'need code'
						need = (':')
						valid = (" ", "\t")
				elif stage == 'need name':
					# поиск названия действия
					if char in need:
						# найдено вхождение строки
						mode['open-string'] = char
						mode['action-name'] = True
					elif not char in valid:
						# недопустимый символ, игнорируем действие
						break
				elif stage == 'need prev image':
					# ищем запятую перед вторым аргументом
					if char == ",":
						stage = "need image"
						need = ("'", '"')
						valid = (" ", "\t")
						continue
					elif char == ":":
						# набор названия и изображения кончился, набираем код
						mode['action-code'] = True
						break
					elif not char in valid:
						# действие кривое, прерываем
						base_act_buffer = _empty_buffer()
						break
				elif stage == 'need image':
					if char in need:
						mode['action-image'] = True
						mode['open-string'] = char
					elif not char in valid:
						base_act_buffer = _empty_buffer()
						break
				elif stage == 'need code':
					if char == ':':
						mode['action-code'] = True
						break
					elif not char in valid:
						mode['action-code'] = False
						base_act_buffer = _empty_buffer()
						break

		def _all_modes_off(mode:dict) -> None:
			return (mode['open-string'] == ''
				and not mode['open-pl']
				and not mode['open-p']
				and not mode['open-implicit']
				and not mode['action-name']
				and not mode['action-image']
				and not mode['action-code'])

		def _empty_buffer() -> dict:
			return {
				'name': '',
				'image': '',
				'code': []
			}
		
		mode = {
			'open-string': '',
			'open-pl': False,
			'open-p': False,
			'open-implicit': False,
			'action-name': False,
			'action-image': False,
			'action-code': False}

		base_act_buffer = _empty_buffer()

		for line in self.base_code:
			if _all_modes_off(mode):
				if IMPLICIT_OPERATOR.match(line):
					_string_to_desc(line, mode, 'open-implicit')
				elif PRINT_LINE.match(line):
					# строка с командой вывода текста
					_string_to_desc(line[3:], mode, 'open-pl')					
				elif PRINT_STRING.match(line):
					_string_to_desc(line[2:], mode, 'open-p')
				elif  ACTION_START.match(line):
					_string_to_act(line[3:], mode, base_act_buffer)
				else:
					NewQspsFile.parse_string(line, mode)
			elif mode['open-pl']:
				_string_to_desc(line, mode, 'open-pl')
			elif mode['open-p']:
				_string_to_desc(line, mode, 'open-p')
			elif mode['open-implicit']:
				_string_to_desc(line, mode, 'open-implicit')
			elif mode['action-code']:
				if mode['open-string'] == '' and ACTION_END.match(line):
					# найдено окончание кода, закрываем
					mode['action-code'] = False
					self.base_actions.append(base_act_buffer.copy())
					base_act_buffer = _empty_buffer()
				else:
					base_act_buffer['code'].append(line)
					NewQspsFile.parse_string(line, mode)
			elif mode['action-image'] or mode['action-name']:
				# переносы строк в названиях и изображениях базовых действий недопустимы
				mode['action-name'] = False
				mode['action-image'] = False
				base_act_buffer = _empty_buffer()
				NewQspsFile.parse_string(line, mode)
			elif mode['open-string']:
				NewQspsFile.parse_string(line, mode)

	def get_sources(self) -> list:
		""" Return qsps-lines of location code, description and actions """
		_eqs = NewQspLocation.escape_qsp_string
		qsps_lines = []
		qsps_lines.append(f"# {self.name}\n")
		if self.base_description or self.base_actions:
			qsps_lines.append("! BASE\n")
			if self.base_description:
				qsps_lines.append(f"*P '{_eqs(self.base_description)}'\n")
			if self.base_actions:
				for action in self.base_actions:
					open_act = f"ACT '{_eqs(action['name'])}'"
					open_act += (f", '{_eqs(action['image'])}':" if action['image'] else ':')
					qsps_lines.append(open_act)
					qsps_lines.extend(['\n'+line for line in action['code']] if action['code'] else [])
					qsps_lines.append('END\n')
			qsps_lines.append("! END BASE\n")
		qsps_lines.extend(self.code)
		qsps_lines.append(f"-- {self.name} " + ("-" * 33))
		return qsps_lines
	
	@staticmethod
	def escape_qsp_string(qsp_string:str) -> str:
		""" Escape-sequence for qsp-string. """
		return qsp_string.replace("'", "''")

class NewQspsFile():
	"""	qsps-file, separated in locations """
	def __init__(self) -> None:
		"""	initialise """
		# main fields:
		self.locations:List[NewQspLocation] = []	# list[NewQspLocation]
		self.src_strings:List[str] = []				# all strings of file
		self.line_offsets = []
		self.converted_strings:list[str] = []		# output converted strings

		# files fields
		self.input_file:str = ''	# abspath of qsps-file
		self.output_folder:str = ''	# output folder name
		self.file_name:str = ''		# file name without extension
		self.output_file:str = ''	# output gamefile path

		# cache fields
		self.char_cache = {}

	def set_input_file(self, input_file:str) -> None:
		""" Set input file and pathes of outputs """
		self.input_file = os.path.abspath(input_file)
		self.output_folder, file_full_name = os.path.split(self.input_file)
		self.file_name = os.path.splitext(file_full_name)[0]
		self.output_file = os.path.join(self.output_folder, self.file_name+".qsp")
		
	def set_file_source(self, file_strings:list=None) -> None:
		""" Set source strings of file """
		if not file_strings: return

		self.src_strings = file_strings[:]
		self.line_offsets = []
		offset = 0
		for line in self.src_strings:
			self.line_offsets.append(offset)
			offset += len(line)

	def get_source(self) -> list:
		""" Return sources qsps-lines """
		return self.src_strings

	def get_qsps_line(self, qsps_line_number:int) -> str:
		""" Return one line from source qsps-line """
		return self.src_strings[qsps_line_number]

	def get_qsps_lines(self, qsps_line_start:int, qsps_line_end:int) -> List[str]:
		return self.src_strings[qsps_line_start:qsps_line_end]

	def convert_file(self, input_file:str) -> None:
		""" Convert qsps-file to qsp-file """
		if not os.path.isfile(input_file): return
		
		self.read_from_file(input_file)
		self.split_to_locations()
		self.to_qsp()
		self.save_to_file()
		
	def read_from_file(self, input_file:str=None) -> None:
		""" Read qsps-file and set source strings """
		if input_file and os.path.isfile(input_file):
			self.set_input_file(input_file)
		if self.input_file:
			offset = 0
			with open(self.input_file, 'r', encoding='utf-8-sig') as fp:
				for line in fp:
					self.src_strings.append(line)
					self.line_offsets.append(offset)
					offset += len(line)
		else:
			print(f'[801] File {self.input_file} is not exist.')

	def save_to_file(self, output_file:str=None) -> None:
		""" Save qsps-text to file. """
		if not output_file:
			output_file = self.output_file
		with open(output_file, 'w', encoding='utf-16le') as file:
			file.writelines(self.converted_strings)

	def get_qsp(self) -> list:
		""" Return converted QSP-strings """
		return self.converted_strings
	
	def preprocess(self, args:Dict[str, bool], pp_variables:Dict[str, bool]) -> None:
		""" Preprocessor of qsps-sources. Run only before splitting! """
		if self.locations: return None # локации уже существуют, файл обработан
		self.src_strings = pp_this_lines(self.src_strings, args, pp_variables)

	def split_to_locations(self) -> None:
		""" Split source strings to locations """
		mode = {
			'location-name': '',
			'open-string': ''}
		location = None
		for i, qsps_line in enumerate(self.src_strings):
			if mode['location-name'] == '': # open string work only in open location
				match = LOCATION_START.search(qsps_line)
				if match:
					# open location
					locname = match.group(1).replace('\r', '')
					location = NewQspLocation(locname)
					location.change_cache(self.char_cache)
					region_start = match.start(1) + self.line_offsets[i]
					region_end = region_start + len(match.group(1).strip())
					location.change_region((region_start, region_end))
					self.append_location(location)
					mode['location-name'] = locname
				else:
					self.parse_string(qsps_line, mode)
			elif mode['open-string'] == '' and LOCATION_END.search(qsps_line):
				# close location
				mode['location-name'] = ''
				if location:
					location.extract_base()
					location.split_base()
			else:
				self.parse_string(qsps_line, mode)
				location.add_code_line(qsps_line)

	def append_location(self, location:NewQspLocation) -> None:
		""" Add location in NewQspsFile """
		self.locations.append(location)

	def to_qsp(self) -> None:
		""" Convert NewQspsFile to QSP-format """
		if self.converted_strings:
			print('[301] Already converted.')
			raise Exception('[301] Already converted.')
		# header of qsp-file
		self.converted_strings.append('QSPGAME\n')
		self.converted_strings.append('qsps_to_qsp SublimeText QSP Package\n')
		self.converted_strings.append(self.encode_qsps_line('No', self.char_cache)+'\n')
		self.converted_strings.append(self.encode_qsps_line(str(len(self.locations)), self.char_cache)+'\n')
		# decode locations
		_decode_location = lambda l: l.encode()
		with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
			for location in self.locations:
				executor.submit(_decode_location, location)
		for location in self.locations:
			self.converted_strings.extend(location.get_qsp())
		# print(f'qsps.converted: {time.time() - start_time}')

	def get_qsplocs(self) -> list:
		""" Return qsp-location for adding to ws """
		qsp_locs = [] # list[list[str, tuple[int, int]]]
		for location in self.locations:
			qsp_locs.append([location.name, location.name_region])
		return qsp_locs

	@staticmethod
	def parse_string(qsps_line:str, mode:dict) -> None:
		""" Parse opened string for location code """
		for char in qsps_line:
			if mode['open-string'] == '':
				# string not open
				if char in ('"', '\'', '{'):
					mode['open-string'] = char
			else:
				if char in ('"', '\'') and mode['open-string'][-1] == char:
					mode['open-string'] = mode['open-string'][:-1]
				elif char == '}' and mode['open-string'][-1] == '{':
					mode['open-string'] = mode['open-string'][:-1]
				elif char == '{':
					mode['open-string'] += char

	@staticmethod
	def encode_char(point:str) -> str:
		""" Encode char. """
		return chr(-QSP_CODREMOV) if ord(point) == QSP_CODREMOV else chr(ord(point) - QSP_CODREMOV)

	@staticmethod
	def encode_qsps_line(qsps_line:str='', cache:dict=None) -> str:
		""" Decode qsps_line to qsp_coded_line """
		exit_line = []
		_encode_char = NewQspsFile.encode_char
		if cache is not None:
			for point in qsps_line:
				if point not in cache:
					cache[point] = _encode_char(point)
				exit_line.append(cache[point])
		else:
			for point in qsps_line:
				exit_line.append(_encode_char(point))
		return ''.join(exit_line)

	def get_locations(self) -> list:
		""" Return list of locaions """
		return self.locations

def test_dnaray():
	import time
	times_list = []
	for i in range(25):
		old_time = time.time()
		qsps = NewQspsFile()
		qsps.convert_file('D:\\dna.txt')
		new_time = time.time()
		times_list.append(old_time - new_time)
		print(new_time - old_time)
	print('mid: ', sum(times_list)/len(times_list))

def main():
	import time
	old_time = time.time()
	qsps = NewQspsFile()
	qsps.convert_file('D:\\game.qsps')
	new_time = time.time()
	print(new_time - old_time)

if __name__ == "__main__":
	main()
