# python 3.8
import os

# constants:
QSP_CODREMOV = 5 # type: int # constant


class QspToQsps():
	"""Converter ".qsp" game files into qsps-files. Based on converter by Werewolf in JS.
	stand `game-file` and run script for getting qsps-format file"""

	def __init__(self) -> None:
		self.input_file = "" # type: str
		self.output_folder = "" # type: str # output folder
		self.file_name = "" # type: str # file name without extension
		self.output_file = "" # type: str # output file

		self.location_count = 0 # type: int # number of locations
		self.locations = [] # type: list # list of locations
		self.qsp_source_text = '-' * 7 # type: str # qsp source text
		self.qsps_text = "" # type: str # qsps text
		self.pasword = "" # type: str # password

	def convert_file(self, input_file:str) -> str:
		""" Read qsp-file, convert and save to qsps-file. Return path to qsps-file. """
		if os.path.isfile(input_file):
			self.read_from_file(input_file)
			self.split_qsp()
			self.to_qsps()
			self.save_to_file()
			return self.output_file
		else:
			print(f'File {input_file} is not exist.')

	def read_from_file(self, input_file:str=None) -> None:
		""" Read qsp-file and set qsp-source text. """
		if input_file and os.path.isfile(input_file):
			self.set_input_file(input_file)
		if self.input_file:
			with open(self.input_file, 'r', encoding='utf-16le') as file:
				self.qsp_source_text = file.read()

	def save_to_file(self, output_file:str=None) -> None:
		""" Save qsps-text to file. """
		if not output_file:
			output_file = self.output_file
		with open(output_file, 'w', encoding='utf-8') as file:
			file.write(self.qsps_text)

	def set_input_file(self, input_file:str) -> None:
		""" Set input file, output file and output folder. """
		self.input_file = os.path.abspath(input_file)
		self.output_folder, file_full_name = os.path.split(self.input_file)
		self.file_name = os.path.splitext(file_full_name)[0]
		self.output_file = os.path.join(self.output_folder, self.file_name+'.qsps')

	def set_qsp_source_text(self, qsp_source_text:str) -> None:
		""" Set qsp-source text. """
		self.qsp_source_text = qsp_source_text

	def split_qsp(self) -> None:
		""" Split qsp-source on locations and decode them. """
		header = self.qsp_source_text[0:7]
		if header != 'QSPGAME':
			print(f'Old qsp format is not support. Use Quest Generator for converting game in new format.')
		else:
			qsp_lines = self.qsp_source_text.split('\n')
			if qsp_lines[-1] == '': qsp_lines.pop()
			self.password = QspToQsps.decode_string(qsp_lines[2])
			self.location_count = QspToQsps.decode_int(qsp_lines[3])
			i = 4
			while (i < len(qsp_lines)):
				location_name = QspToQsps.decode_string(qsp_lines[i])
				location_desc = QspToQsps.decode_string(qsp_lines[i+1])
				location_code = QspToQsps.decode_string(qsp_lines[i+2])
				i += 3
				actions = []
				actions_count = QspToQsps.decode_int(qsp_lines[i])
				i += 1
				for _ in range(actions_count):
					action_image = QspToQsps.decode_string(qsp_lines[i])
					action_name = QspToQsps.decode_string(qsp_lines[i+1])
					action_code = QspToQsps.decode_string(qsp_lines[i+2])
					i += 3
					actions.append({
						"image": action_image,
						"name": action_name,
						"code": action_code
					})
				self.locations.append({
					"name": location_name,
					"description": location_desc,
					"code": location_code,
					"actions": actions
				})

	def to_qsps(self) -> str:
		""" Convert all game's locations to qsps-format. """
		if not self.locations:
			return 'QSP-Game is not formed. Prove QSP-file.'
		else:
			_cl = QspToQsps.convert_location
			self.qsps_text = f"QSP-Game {self.file_name}\nЧисло локаций: {self.location_count}\n"
			self.qsps_text += f"Пароль на исходном файле: {self.password}\n"
			self.qsps_text += '\n\n'.join([''.join(_cl(l)) for l in self.locations])
			return self.qsps_text+'\n\n'
		
	def get_locations(self) -> list:
		""" Get loactions list """
		return self.locations
		
	def get_location(self, index:int) -> dict:
		""" Get location by index. """
		return self.locations[index]
	
	def get_location_by_name(self, name:str) -> dict:
		""" Get location by name. """
		for loc in self.locations:
			if loc['name'] == name:
				return loc
		return None
	
	@staticmethod
	def base_is_exist(location:dict) -> bool:
		""" Check if base description and actions are exist. """
		return location['actions'] or location['description']

	@staticmethod
	def convert_location(location:dict) -> list:
		""" Convert location to qsps-format. Return qsps-lines. """
		qsps_lines = []
		qsps_lines.append(f"# {location['name']}\n")
		if QspToQsps.base_is_exist(location):
			qsps_lines.append("! BASE\n")
			qsps_lines.append(f"{QspToQsps.convert_description(location['description'])}")
			qsps_lines.append(f"{QspToQsps.convert_actions(location['actions'])}")
			qsps_lines.append("! END BASE\n")
		loc_code = location['code'].replace('\r\n','\n')
		qsps_lines.append(f"{loc_code}\n")
		qsps_lines.append(f"-- {location['name']} " + ("-" * 33))
		return qsps_lines

	@staticmethod
	def convert_description(description:str) -> str:
		""" Convert base description to qsps-format. """
		if not description:
			return ''
		else:
			_eqs = QspToQsps.escape_qsp_string
			desc_lines = description.split('\r\n')
			last_line = desc_lines.pop()
			qsps_lines = ["*p '"]
			qsps_lines.extend([(f"{_eqs(l)}\n") for l in desc_lines])
			qsps_lines.append(f"{_eqs(last_line)}'\n")
			return ''.join(qsps_lines)

	@staticmethod
	def convert_actions(actions:list) -> str:
		""" Convert all location's actions to qsps-format. """
		if not actions:
			return ''
		else:
			try:
				return '\n'.join([QspToQsps.convert_action(action) for action in actions])+'\n'
			except:
				print(actions)

	@staticmethod
	def convert_action(action:dict) -> str:
		""" Convert base action to qsps-format. """
		qsps_text = f"ACT '{QspToQsps.escape_qsp_string(action['name'])}'"
		image = (f", '{QspToQsps.escape_qsp_string(action['image'])}':" if action['image'] else ':')
		qsps_text += image
		qsps_text += ('\n\t'+'\n\t'.join(action['code'].split('\r\n')) if action['code'] else '')
		qsps_text += '\nEND'
		return qsps_text

	@staticmethod
	def escape_qsp_string(qsp_string:str) -> str:
		""" Escape-sequence for qsp-string. """
		return qsp_string.replace("'", "''")

	@staticmethod
	def decode_int(qsp_line:str) -> int:
		""" Decode qsp-line to int. """
		return int(QspToQsps.decode_qsp_line(qsp_line))

	@staticmethod
	def decode_string(qsp_line:str) -> str:
		""" Decode qsp-line to string. """
		return QspToQsps.decode_qsp_line(qsp_line)
	
	@staticmethod
	def decode_qsp_line(qsp_line:str) -> str:
		""" Decode qsp-line. """
		exit_lines = []
		_decode_char = lambda t, v: (chr(v) if ord(t) == -v else chr(ord(t) + v))
		for char in qsp_line:
			exit_lines.append(_decode_char(char, QSP_CODREMOV))
		return ''.join(exit_lines)

		
def main():
	import time
	old_time = time.time()

	qsp_to_qsps = QspToQsps()
	qsp_to_qsps.convert_file('..\\..\\[examples]\\examples_qsp_to_qsps\\driveex.qsp')

	new_time = time.time()
	print(new_time - old_time)

if __name__ == "__main__":
	# 
	main()
	# if you need choose converter for decode gamepass:
	print(QspToQsps.decode_string(f'2230/4.31'))
