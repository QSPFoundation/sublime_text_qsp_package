import os
import subprocess
from typing import (List, Literal, Dict)

from . import function as qsp
from .qsps_to_qsp import NewQspsFile
import plugtypes as ts
# import time

class ModuleQSP():

	def __init__(self, scheme:ts.QspModule) -> None:

		self.src_qsps_file:List[NewQspsFile] = []

		self.output_qsp:str = None		# path of output QSP-file (module)
		self.output_txt:str = None		# path of temp file in txt2gam format

		# self.code_system = 'utf-8'
		self._converter:ts.Path = 'qsps_to_qsp' # converter qsps -> QSP
		self._conv_args:ts.AppParam = ''	# string of parameters for converting

		self.qsps_code:List[str] = []	# all strings of module code
		# self.start_time = start_time
	
	def set_converter(self, conv:ts.Path, args:ts.AppParam) -> None:
		""" set path to converter, or converter name """
		self._converter = conv
		self._conv_args = args

	def extend_by_file(self, file_path:str) -> None: # file_path:abs_path of file
		""" Add NewQspsFile by file-path """
		if os.path.isfile(file_path):
			src = NewQspsFile()
			src.read_from_file(file_path)
			self.src_qsps_file.append(src)
		else:
			qsp.write_error_log(f'[ModuleQSP:001] File don\'t exist. Prove path {file_path}.')

	def extend_by_folder(self, folder_path:str) -> None:
		""" Add SrcQspsFile-objs by folder-path """
		if not os.path.isdir(folder_path):
			qsp.write_error_log(f'[ModuleQSP:002] Folder don\'t exist. Prove path {folder_path}.')
			return None
		for el in qsp.get_files_list(folder_path):
			file_path = os.path.abspath(el) # TODO: if el is abspath - del absing path of el
			self.extend_by_file(file_path)

	def extend_by_src(self, qsps_lines:List[str]) -> None:
		""" Add NewQspsFile by qsps-src-code strings """
		src = NewQspsFile()
		src.set_file_source(qsps_lines)
		self.src_qsps_file.append(src)

	def set_exit_files(self, game_path:str) -> None:
		"""
			On input QSP-file's path,
			on output QSP-file's abs.path and temporary txt-file's abs path.
		"""
		self.output_qsp = os.path.abspath(game_path)
		self.output_txt = os.path.splitext(self.output_qsp)[0]+".txt"

	def choose_code_system(self) -> str:
		""" utf-8 for built-in converter, utf-16-le for txt2gam """
		# TODO: txt2gam поддерживает utf-8. Можно убрать выбор кодировки.
		return ('utf-8' if self.converter == 'qsps_to_qsp' else 'utf-16-le')


	def preprocess_qsps(self, pponoff:Literal['Hard-off', 'Off', 'On'],
						pp_markers:Dict[str, bool]) -> None:
		""" 
			На данном этапе у нас есть объекты класса NewQspsFile, которые включают в себя список
			строк для каждого файла, т.е. цикл чтения уже завершён. Теперь мы можем обработать эти
			виртуальные файлы, прогнав их через препроцессор.

			pponoff — управление препроцессором main
			pp_markers — переменные и метки
		"""
		if pponoff == 'Hard-off':
			return None
		_met_condition = (lambda f, s:
			(f == 'Off' and  "!@pp:on\n" in s) or (f == 'On' and not "!@pp:off\n" in s))
		for src in self.src_qsps_file:
			if _met_condition(pponoff, (src.get_qsps_line(0), src.get_qsps_line(1))):
				arguments:Dict[str, bool] = {"include":True, "pp":True, "savecomm": False}
				src.preprocess(arguments, pp_markers)

	def src_to_text(self) -> str:
		""" Get outer text of module """
		text:List[str] = []
		for src in self.src_qsps_file:
			text.extend(src.get_source())
			text.append('\n')
		return ''.join(text)

	def save_temp_file(self) -> None:
		""" Save temp file of module before converting by txt2gam, or for checkout. """
		# если папка не создана, нужно её создать
		path_folder = os.path.split(self.output_txt)[0]
		os.makedirs(path_folder, exist_ok=True)
		text = self.src_to_text()
		code_system = self.choose_code_system()
		# необходимо записывать файл в кодировке utf-16le, txt2gam версии 0.1.1 понимает её
		text = text.encode(code_system, 'ignore').decode(code_system,'ignore')
		with open(self.output_txt, 'w', encoding=code_system) as file:
			file.write(text)

	def extract_qsps(self) -> None:
		""" From qsps-files extract sources lines and add to module source """
		for src in self.src_qsps_file:
			self.qsps_code.extend(src.get_source())

	def convert(self, save_temp_file:bool) -> None:
		""" Convert sources and save module to file """
		# start_time = time.time()
		if self.converter == 'qsps_to_qsp':
			qsps_file = NewQspsFile()
			qsps_file.set_file_source(self.qsps_code)
			# print(f'Module.newqsps {time.time() - start_time}, {time.time() - self.start_time}')
			qsps_file.split_to_locations()
			qsps_file.to_qsp()
			# print(f'Module.convert {time.time() - start_time}, {time.time() - self.start_time}')
			qsps_file.save_to_file(self.output_qsp)
			# print(f'Module.save_qsp {time.time() - start_time}, {time.time() - self.start_time}')
			if save_temp_file: self.save_temp_file()
			# print(f'Module.temp {time.time() - start_time}, {time.time() - self.start_time}')
		else:
			self.save_temp_file()
			_run = [self.converter, self.output_txt, self.output_qsp, self.converter_param]
			subprocess.run(_run, stdout=subprocess.PIPE)
			if not save_temp_file:
				os.remove(self.output_txt)
