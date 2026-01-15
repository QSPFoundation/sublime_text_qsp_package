# Converter qsps-files (only UTF-8) into game files `.qsp`.
# stand `file_path` and run script for getting QSP-format file.

import os
import re

from typing import List, Dict

if __name__ == "__main__":
	from function import (del_first_pref)
	import plugtypes as ts
else:
	from .function import (del_first_pref)
	from . import plugtypes as ts
# import time


# regexps:
LOCATION_START = re.compile(r'^\#\s*(.+)$')
LOCATION_END = re.compile(r'^\-\-(.*)$')

PRINT_STRING = re.compile(r'^\*P\b')
PRINT_LINE = re.compile(r'^\*PL\b')
ACTION_START = re.compile(r'^ACT\b')
ACTION_END = re.compile(r'^END\b')
IMPLICIT_OPERATOR = re.compile(r'^("|\')')

class NewQspsFile():
	"""	qsps-file, separated in locations """
	def __init__(self) -> None:
		# main fields:
		self._locations:List[NewQspLocation] = []
		self._qsps_strings:List[ts.QspsLine] = []				# all strings of file

		# files fields
		self._input_file:ts.Path = ''	# abspath of qsps-file

	def set_file_source(self, file_strings:List[ts.QspsLine]) -> None:
		""" Set source strings of file """
		if not file_strings: return

		self._qsps_strings = file_strings[:]
		# self.line_offsets = []
		# offset = 0
		# for line in self._qsps_strings:
		# 	# self.line_offsets.append(offset)
		# 	offset += len(line)

	def read_from_file(self, input_file:ts.Path) -> None:
		""" Read qsps-file and set source strings """
		if os.path.isfile(input_file):
			self._input_file = input_file
		else:
			print(f'[801] File {input_file} is not exist.')
			return
		# offset = 0
		with open(self._input_file, 'r', encoding='utf-8-sig') as fp:
			for line in fp:	self._qsps_strings.append(line)
				# self.line_offsets.append(offset)
				# offset += len(line)

	def get_source(self) -> List[ts.QspsLine]:
		""" Return sources qsps-lines """
		return self._qsps_strings

	def get_qsps_line(self, qsps_line_number:int) -> ts.QspsLine:
		""" Return one line from source qsps-line """
		return self._qsps_strings[qsps_line_number]

	def get_qsps_lines(self, qsps_line_start:int, qsps_line_end:int) -> List[ts.QspsLine]:
		return self._qsps_strings[qsps_line_start:qsps_line_end]



	def get_qsp(self) -> list:
		""" Return converted QSP-strings """
		return self._game_strings

	def split_to_locations(self) -> None:
		""" Split source strings to locations """
		mode = {
			'location-name': '',
			'open-string': ''}
		location = None
		for i, qsps_line in enumerate(self._qsps_strings):
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
		self._locations.append(location)

	
		# print(f'qsps.converted: {time.time() - start_time}')

	def get_qsplocs(self) -> list:
		""" Return qsp-location for adding to ws """
		qsp_locs = [] # list[list[str, tuple[int, int]]]
		for location in self._locations:
			qsp_locs.append([location.name, location.name_region])
		return qsp_locs

	@staticmethod
	

	def get_locations(self) -> list:
		""" Return list of locaions """
		return self._locations

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
