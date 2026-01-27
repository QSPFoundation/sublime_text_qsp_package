# Converter qsps-files (only UTF-8) into game files `.qsp`.
# stand `file_path` and run script for getting QSP-format file.

import os
import re

from typing import List, Optional

from .tps import (
	Path,
	QspsLine,
	LocFindMode
)
from .qsp_location import QspLoc
from .tools import parse_string

# regexps:
LOCATION_START = re.compile(r'^\#\s*(.+)\s*$')
LOCATION_END = re.compile(r'^\-\-(.*)$')

PRINT_STRING = re.compile(r'^\*P\b')
PRINT_LINE = re.compile(r'^\*PL\b')
ACTION_START = re.compile(r'^ACT\b')
ACTION_END = re.compile(r'^END\b')
IMPLICIT_OPERATOR = re.compile(r'^("|\')')

class QspsFile():
	"""	qsps-file entity, separated in locations """
	def __init__(self, qsps_line:Optional[List[QspsLine]] = None) -> None:
		# main fields:
		self._locations:List[QspLoc] = []
		self._src_lines:List[QspsLine] = qsps_line if qsps_line else []				# all strings of file

		# files fields
		self._input_file:Path = ''	# abspath of qsps-file

	def add_src_lines(self, file_strings:List[QspsLine]) -> None:
		""" Add source-lines at end of QspsFile. """
		if not file_strings: return
		self._src_lines.extend(file_strings)

	def set_src_lines(self, file_strings:List[QspsLine]) -> None:
		""" Add source-lines at end of QspsFile. """
		if not file_strings: return
		self._src_lines = file_strings

	def read_from_file(self, input_file:Path) -> None:
		""" Read qsps-file and set source strings """
		if os.path.isfile(input_file):
			self._input_file = input_file
		else:
			print(f'[801] File {input_file} is not exist.')
			return
		with open(self._input_file, 'r', encoding='utf-8-sig') as fp:
			for line in fp:	self._src_lines.append(line)

	def get_src(self) -> List[QspsLine]:
		""" Return sources qsps-lines """
		return self._src_lines

	def get_src_line(self, qsps_line_number:int) -> QspsLine:
		""" Return one line from source qsps-line """
		return self._src_lines[qsps_line_number]

	def get_src_lines(self, qsps_line_start:int, qsps_line_end:int) -> List[QspsLine]:
		return self._src_lines[qsps_line_start:qsps_line_end]

	def split_to_locations(self) -> None:
		""" Split source strings to locations """
		mode:LocFindMode = {
			'loc_name': '',
			'quote': [],
			'src_lines': []}
		for qsps_line in self._src_lines:
			if mode['loc_name'] == '': # open string work only in open location
				match = LOCATION_START.search(qsps_line)
				if match:
					# open location
					mode['loc_name'] = match.group(1).replace('\r', '')
				else:
					# если локация ещё не открыта, пропускаем строки
					pass
			elif not mode['quote'] and LOCATION_END.search(qsps_line):
				# close location
				self._locations.append(QspLoc(mode['loc_name'], mode['src_lines']))
				mode['loc_name'] = ''
				mode['src_lines'].clear()
			else:
				parse_string(qsps_line, mode)
				mode['src_lines'].append(qsps_line)

	def append_location(self, location:QspLoc) -> None:
		""" Add location in QspsFile """
		self._locations.append(location)

	def get_locations(self) -> List[QspLoc]:
		""" Return list of locaions """
		return self._locations
