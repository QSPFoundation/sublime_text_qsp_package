# python 3.8
import os
from typing import Dict, List, Literal, Optional

from .tools import QSP_CODREMOV
from .tps import (
	Action, MultilineDesc, Path, FileName, QspLocation, GamePassword,
	QspsChar, GameChar, GameLine, QspsLine
)
CharCache = Dict[GameChar, QspsChar]
Encoding = Literal['utf-16-le', 'utf-8-sig', 'utf-8', 'cp1251']

class ValidationFormatError(ValueError):

	def __init__(self, encoding: str, message: str = "") -> None:
		full_message = f"[{encoding}] {message}" if message else encoding
		super().__init__(full_message)
		self.encoding = encoding

class QspToQspsBuiltinConv():
	"""Converter ".qsp" game files into qsps-files. Based on converter by Werewolf in JS.
	stand `game-file` and run script for getting qsps-format file"""

	_char_cache:CharCache = {}
	_cp1251_cache:CharCache = {}

	def __init__(self) -> None:
		self._input_file:Path = ""
		self._output_folder:Path = ""  # output folder
		self._file_name:FileName = ""  # file name without extension
		self._output_file:Path = ""  # output file

		self._location_count:int = 0 # number of locations
		self._locations:List[QspLocation] = [] # list of locations
		self._password:GamePassword = "No"  # password

		self._game_lines:List[GameLine] = [] # qsp source text
		self._qsps_lines:List[QspsLine] = []  # qsps text

		self._encoding:Encoding = 'utf-16-le'
		# self._cache:CharCache = self._char_cache
		self._encode_handler = QspToQspsBuiltinConv.decode_qsp_line


	def convert_file(self, input_file:Path='') -> Path:
		""" Read qsp-file, convert and save to qsps-file. Return path to qsps-file. """
		if not os.path.isfile(input_file):
			print(f'Incorrect file path. {input_file}')
			return ''
		try:
			self.read_from_file(input_file)
		except ValidationFormatError as e:
			print(e)
			return ''
		self.split_qsp()
		self.to_qsps()
		self.save_to_file()
		return self._output_file

	def read_from_file(self, input_file:Path='') -> None:
		""" Read qsp-file and set qsp-source text. """
		if not os.path.isfile(input_file):
			print(f'Incorrect file path. {input_file}')
			return
		self._set_pathes(input_file)
		encodings:List[Encoding] = ['utf-16-le', 'utf-8-sig', 'utf-8', 'cp1251']
		for enc in encodings:
			try:
				with open(self._input_file, 'r', encoding=enc) as fp:
					self._game_lines = list(fp) # при ошибке присваивание не произойдёт
				if enc == 'cp1251' and self._game_lines and self._game_lines[0].startswith('п»ї'):
					raise UnicodeDecodeError(
						'cp1251', b'\xef\xbb\xbf', 0, 3,
						'UTF-8 BOM detected while decoding as cp1251'
					)
				if self._game_lines and not self._game_lines[0].startswith('QSPGAME'):
					raise ValidationFormatError(enc,
						f"Header is not QSPGAME while decoding as {self._game_lines[0][:7]}"
					)
				self._encoding = enc
				if enc == 'cp1251': self._encode_handler = QspToQspsBuiltinConv.decode_cp1251_qsp_line
				return
			except UnicodeDecodeError as e:
				print(e)
				continue
		print('Unknown game encoding! Use txt2gam utilities for conversion.')

	def save_to_file(self, output_file:Path='') -> None:
		""" Save qsps-text to file. """
		if not output_file:
			output_file = self._output_file
		with open(output_file, 'w', encoding='utf-8') as file:
			file.writelines(self._qsps_lines)

	def _set_pathes(self, input_file:str) -> None:
		""" Set input file, output file and output folder. """
		self._input_file = os.path.abspath(input_file)
		self._output_folder, base_name = os.path.split(self._input_file)
		self._file_name = os.path.splitext(base_name)[0]
		self._output_file = os.path.join(self._output_folder, self._file_name+'.qsps')

	def set_qsp_source_text(self, qsp_source_text:str) -> None:
		""" Set qsp-source text. """
		self.qsp_source_text = qsp_source_text

	def split_qsp(self) -> None:
		""" Split qsp-source on locations and decode them. """
		qsp_lines = self._game_lines[:]
		header:GameLine = qsp_lines[0][0:7] # header pop
		if header != 'QSPGAME':
			print(f'Old qsp format is not support. Use Quest Generator for converting game in new format.')
			return

		if qsp_lines[-1].strip() == '': qsp_lines.pop()
		self._password = self._decode_string(qsp_lines[2][:-1])
		self._location_count = self._decode_int(qsp_lines[3][:-1])
		i = 4
		while (i < len(qsp_lines)):
			location_name = self._decode_string(qsp_lines[i][:-1])
			location_desc = self._decode_string(qsp_lines[i+1][:-1])
			location_code = self._decode_string(qsp_lines[i+2][:-1])
			i += 3
			actions:List[Action] = []
			actions_count = self._decode_int(qsp_lines[i][:-1])
			i += 1
			for _ in range(actions_count):
				action_image = self._decode_string(qsp_lines[i][:-1])
				action_name = self._decode_string(qsp_lines[i+1][:-1])
				action_code = self._decode_string(qsp_lines[i+2][:-1])
				actions.append({
					"image": action_image,
					"name": action_name,
					"code": action_code.splitlines(keepends=True)
				})
				i += 3
			self._locations.append({
				"name": location_name,
				"desc": location_desc,
				"run_to_visit": location_code.splitlines(keepends=True),
				"actions": actions
			})

	def to_qsps(self) -> List[QspsLine]:
		""" Convert all game's locations to qsps-format. """
		if not self._locations:
			print('QSP-Game is not formed. Prove QSP-file.') # TODO: Error
			return []

		_cl = QspToQspsBuiltinConv.convert_location
		self._qsps_lines.append(f"QSP-Game {self._file_name}\n")
		self._qsps_lines.append(f"Число локаций: {self._location_count}\n")
		self._qsps_lines.append(f"Пароль на исходном файле: {self._password}\n")
		self._qsps_lines.append('\n')
		for loc in self._locations:
			self._qsps_lines.extend(QspToQspsBuiltinConv.convert_location(loc))
		return self._qsps_lines

	def get_locations(self) -> List[QspLocation]:
		""" Get loactions list """
		return self._locations

	def get_location(self, index:int) -> QspLocation:
		""" Get location by index. """
		return self._locations[index]

	def get_location_by_name(self, name:str) -> Optional[QspLocation]:
		""" Get location by name. """
		for loc in self._locations:
			if loc['name'] == name:
				return loc
		return None

	@staticmethod
	def base_is_exist(location:QspLocation) -> bool:
		""" Check if base description and actions are exist. """
		return bool(location['actions'] or location['desc'])

	@staticmethod
	def convert_location(location:QspLocation) -> List[QspsLine]:
		""" Convert location to qsps-format. Return qsps-lines. """
		qsps_lines:List[QspsLine] = []
		qsps_lines.append(f"# {location['name']}\n")
		if bool(location['actions'] or location['desc']):
			qsps_lines.append("! BASE\n")
			qsps_lines.extend(QspToQspsBuiltinConv.convert_description(location['desc']))
			qsps_lines.extend(QspToQspsBuiltinConv.convert_actions(location['actions']))
			qsps_lines.append("! END BASE\n")
		if location['run_to_visit']:
			loc_code = ''.join(location['run_to_visit']).replace('\r\n','\n')
			qsps_lines.append(f"{loc_code}\n")
		qsps_lines.append(f"-- {location['name']} {'-' * 33}\n\n")
		return qsps_lines

	@staticmethod
	def convert_description(description:MultilineDesc) -> List[QspsLine]:
		""" Convert base description to qsps-format. """
		if not description:
			return []
		_eqs = QspToQspsBuiltinConv.escape_qsp_string

		# TODO: replace \r\n by \n, replace ' by '', wrap to *p '...'
		desc_lines = description.split('\r\n')
		last_line = desc_lines.pop()
		qsps_lines = ["*P '"]
		qsps_lines.extend([f"{_eqs(l)}\n" for l in desc_lines])
		qsps_lines.append(f"{_eqs(last_line)}'\n")
		return qsps_lines

	@staticmethod
	def convert_actions(actions:List[Action]) -> List[QspsLine]:
		""" Convert all location's actions to qsps-format. """
		if not actions:
			return []
		try:
			qsps_lines:List[QspsLine] = []
			for action in actions:
				qsps_lines.extend(QspToQspsBuiltinConv.convert_action(action))
			return qsps_lines
		except:
			print(actions)
			return []

	@staticmethod
	def convert_action(action:Action) -> List[QspsLine]:
		""" Convert base action to qsps-format. """
		qsps_lines:List[QspsLine] = []
		_eqs = QspToQspsBuiltinConv.escape_qsp_string
		indent = '\t'
		name = _eqs(action['name'])
		image = (f", '{_eqs(action['image'])}':" if action['image'] else ':')
		qsps_lines.append(f"ACT '{name}'{image}\n")
		qsps_lines.extend([
			(f"{indent}{line}").replace('\r\n', '\n')
			for line in action['code']])
		if qsps_lines[-1][-1] == '\n': qsps_lines.append(f'{indent}') # crutching format for txt2gam
		qsps_lines.append('\nEND\n')
		return qsps_lines

	@staticmethod
	def escape_qsp_string(qsp_string:str) -> str:
		""" Escape-sequence for qsp-string. """
		return qsp_string.replace("'", "''")

	def _decode_int(self, qsp_line:str) -> int:
		""" Decode qsp-line to int. """
		return int(self._encode_handler(qsp_line))

	def _decode_string(self, qsp_line:str) -> str:
		""" Decode qsp-line to string. """
		return self._encode_handler(qsp_line)

	@staticmethod
	def decode_qsp_line(qsp_line:GameLine) -> QspsLine:
		""" Decode qsp-line. """
		cache = QspToQspsBuiltinConv._char_cache
		exit_lines:List[QspsLine] = []
		_decode_char = QspToQspsBuiltinConv.decode_char

		for char in qsp_line:
			if char not in cache:
				cache[char] = _decode_char(char)
			exit_lines.append(cache[char])
		return ''.join(exit_lines)

	@staticmethod
	def decode_char(point:GameChar) -> QspsChar:
		return (chr(QSP_CODREMOV) if ord(point) == -QSP_CODREMOV else chr(ord(point) + QSP_CODREMOV))

	@staticmethod
	def decode_cp1251_qsp_line(qsp_line:GameLine) -> QspsLine:
		""" Decode qsp-line. """
		cache = QspToQspsBuiltinConv._cp1251_cache
		exit_lines:List[QspsLine] = []
		_decode_char = QspToQspsBuiltinConv.decode_cp1251_char

		for char in qsp_line:
			if char not in cache:
				cache[char] = _decode_char(char)
			exit_lines.append(cache[char])
		return ''.join(exit_lines)

	@staticmethod
	def decode_cp1251_char(point:GameChar) -> QspsChar:
		b = point.encode('cp1251')[0]
		if b == (-QSP_CODREMOV) & 0xFF:
			return chr(QSP_CODREMOV)
		out_b = (b + QSP_CODREMOV) & 0xFF
		return bytes((out_b,)).decode('cp1251')
