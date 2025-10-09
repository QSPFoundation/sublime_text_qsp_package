import re
from typing import (List, Literal, Tuple, Dict, Match, Optional, Callable, Union)

# regular expressions constants
_DUMMY_MATCH = re.compile(r'^\s*$').match('')

_PP_DIRECTIVE_START = re.compile(r'^!@pp:')
_PP_ON_DIRECTIVE = re.compile(r'^on\n$')
_PP_OFF_DIRECTIVE = re.compile(r'^off\n$')
_PP_ONSAVECOMM_DIR = re.compile(r'^savecomm\n$')
_PP_OFFSAVECOMM_DIR = re.compile(r'^nosavecomm\n$')
_PP_ONCONDITION_DIR = re.compile(r'^if\(.*?\)')
_PP_OFFCONDITION_DIR = re.compile(r'^endif\n$')
_PP_VARIABLE_DIR = re.compile(r'^var\(.*?\)')

_SIMPLE_SPECCOM = re.compile(r'!@(?!\<)')
_HARDER_SPECCOM = re.compile(r'!@<')
_DOUBLE_QUOTES = re.compile(r'"')
_SINGLE_QUOTES = re.compile(r"'")
_OPEN_BRACE = re.compile(r'\{')
_CLOSE_BRACE = re.compile(r'\}')

_OPERANDS = re.compile(r'!=|==|\(|\)|\bor\b|\band\b|\bnot\b|<=|>=|<|>')
_LINE_END_AMPERSAND = re.compile(r'\s*?\&\s*?$')

# функция, извлекающая директиву в скобках
def extract_directive(string:str, directive:Literal['var', 'if']) -> str:
	"""	Extract the directive in parentheses. """
	return string.replace(directive, '', 1).strip()[1:-1]

# функция, добавляющая метку и значение
def add_variable(variables:dict, directive:str) -> None:
	""" Add variable and value to variables dictionary. """
	temp = [False, False]
	if "=" in directive:
		# делим по знаку равенства
		direct_list = directive.split("=")
		temp[0] = (variables[direct_list[0]] if direct_list[0] in variables else direct_list[0])
		temp[1] = (variables[direct_list[1]] if direct_list[1] in variables else direct_list[1])
		if direct_list[0] in variables and type(variables[direct_list[0]]) == bool:
			...
		else:
			variables[direct_list[0]] = temp[1]
		if direct_list[1] in variables and type(variables[direct_list[1]]) == bool:
			...
		else:
			variables[direct_list[1]] = temp[1]
	else:
		variables[directive] = True

# функция распарсивает строку условия на элементы
def parse_condition(variables:dict, directive:str) -> None:
	""" Condition Parsing at operands """
	operand_list:List[str] = _OPERANDS.split(directive)
	for operand in operand_list:
		if len(operand_list) > 1:
			operand = operand.strip()
			if operand != "" and (not operand in variables):
				variables[operand] = operand
		elif not operand in variables:
			variables[operand] = False
	return operand_list

# функция, которая проверяет, выполняется ли условие
def met_condition(variables:dict, directive:str) -> bool:
	""" Check if the condition is met. """
	result = dict()
	operands:List[str] = parse_condition(variables, directive)
	# следующий цикл формирует условие с действительными значениями вместо элементов
	for var in operands:
		if (var in directive) and re.search(r'\b'+var+r'\b', directive):
			if type(variables[var]) == str:
				directive = directive.replace(var, f"'{variables[var]}'")
			else:
				directive = directive.replace(var, str(variables[var]))
	directive = directive.replace("''", "'")
	directive = directive.replace('""', '"')
	directive = f"out=(True if {directive} else False)"
	exec(directive, result)
	return result['out']

# функция, которая правильно открывает блок условия
def open_condition(command:str, condition:bool, args:dict) -> None:
	""" Open condition for loop use. """
	instructions:List[str] = re.split(r'\s+', command.strip())
	prev_args:dict = args['if']
	for i in instructions:
		if i == "exclude":
			prev_args["include"] = args["include"]
			args["include"] = not condition
		elif i == "include":
			prev_args["include"] = args["include"]
			args["include"] = condition
		elif i == "nopp":
			prev_args["pp"] = args["pp"]
			args["pp"] = not condition
		elif i == "savecomm":
			prev_args["savecomm"] = args["savecomm"]
			args["savecomm"] = condition
	args["openif"] = True

# функция, которая правильно закрывает условие
def close_condition(args:dict) -> None:
	""" Right closing of condition """
	prev_args = args["if"]
	args["include"] = prev_args["include"]
	args["pp"] = prev_args["pp"]
	args["savecomm"] = prev_args["savecomm"]
	

def find_speccom_scope(string_line:str) -> Tuple[Optional[str], str, Match[str], str]:
	""" Find in string scopes of special comments """
	maximal = len(string_line)+1
	mini_data_base:Dict[str, list] = {
		"scope-name": [
			'simple-speccom',
			'strong-speccom',
			'apostrophe',
			'quote',
			'brace-open',
			'brace-close'
		],
		"scope-regexp":
		[
			_SIMPLE_SPECCOM.search(string_line),
			_HARDER_SPECCOM.search(string_line),
			_DOUBLE_QUOTES.search(string_line),
			_SINGLE_QUOTES.search(string_line),
			_OPEN_BRACE.search(string_line),
			_CLOSE_BRACE.search(string_line)
		],
		"scope-instring":
		[]
	}
	for i, _ in enumerate(mini_data_base['scope-name']):
		match_in:Match[str] = mini_data_base['scope-regexp'][i]
		mini_data_base['scope-instring'].append(match_in.start(0) if match_in else maximal)
	minimal:int = min(mini_data_base['scope-instring'])
	if minimal != maximal:
		i:int = mini_data_base['scope-instring'].index(minimal)
		scope_type:str = mini_data_base['scope-name'][i]
		scope_regexp_obj:Match[str] = mini_data_base['scope-regexp'][i]
		scope:str = scope_regexp_obj.group(0)
		q:int = scope_regexp_obj.start(0)
		prev_line:str = string_line[0:q]
		post_line:str = string_line[q+len(scope):]
		return scope_type, prev_line, scope_regexp_obj, post_line
	else:
		return None, '', _DUMMY_MATCH, string_line


def pp_string(text_lines:List[str], string:str, args:dict) -> None:
	""" обработка строки. Поиск спецкомментариев """
	if not args["include"]:
		# Режим добавления строк к результирующему списку отключен,
		# это значит, что строку можно игнорировать.
		return None
	result = string # по умолчанию строка целиком засылается в список
	if args["include"] and args['pp'] and not args['savecomm']:
		# обработка нужна только если выполняются три условия:
		# 1. режим добавления строк включен;
		# 2. препроцессор включен;
		# 3. сохранение спецкомментариев отключено
		correspondence_table:dict = {
			# scope_type: quote-type
			'apostrophe': 'apostrophes',
			'quote': 'quotes',
			'brace-open': 'brackets'
		}
		# TODO: Данная функция просто проверяет количество кавычек, но эта реализация автоматически
		# TODO: ошибочна, так как простое " ' " ' ломает её. Количество кавычек чётное, но кавычка
		# TODO: должна быть открыта, и спецкомментарий удалять нельзя. Возможно, стоит пересмотреть
		# TODO: положение функции parse_string, перенести её в модуль function, и затем импортировать сюда.
		_double_quotes:Callable[[str], bool] = (lambda x:
			x.count('"') % 2 == 0 and x.count("'") % 2 == 0 and x.count('{') <= x.count('}'))
		
		def _head_tail_fill(result_list:List[str],
					  split_str:Tuple[Optional[str], str, Match[str], str]) -> Tuple[str, str]:
			_, prev_text, scope_regexp_obj, post_text = split_str
			result_list.append(prev_text + scope_regexp_obj.group(0))
			return post_text

		result_list:List[str] = []
		while len(string) > 0:
			split_str = scope_type, prev_text, _, post_text = find_speccom_scope(string)
			if not args["openquote"]:
				if scope_type in ('apostrophe', 'quote', 'brace-open'):
					args["openquote"] = True
					args["quote"] = correspondence_table[scope_type]
					string = _head_tail_fill(result_list, split_str)
				elif scope_type == "brace-close":
					string = _head_tail_fill(result_list, split_str)
				elif scope_type in ("simple-speccom", 'strong-speccom'): # спецкомментарий
					if not _double_quotes(post_text):
						string = _head_tail_fill(result_list, split_str)
					elif scope_type == 'simple-speccom': # число кавычек чётное
						result_list.append(_LINE_END_AMPERSAND.sub('', prev_text) + '\n')
						break
					else:
						return None
				else:
					result_list.append(string)
					break
			elif scope_type is not None:
				if args["quote"] == correspondence_table.get(scope_type, None):
					args["openquote"] = False
					args["quote"] = ""
				string = _head_tail_fill(result_list, split_str)
			else:
				result_list.append(string)
				break
		result = ''.join(result_list)
	
	if args["openquote"] or result.split(): # если открыты кавычки, или это не пустая строка
		text_lines.append(result)

def pp_this_file(file_path:str, args:dict, variables:dict = None) -> str:
	""" Preprocessing of input file and Returns output text. """
	with open(file_path, 'r', encoding='utf-8') as pp_file:
		file_lines = pp_file.readlines() # получаем список всех строк файла
	result_lines = pp_this_lines(file_lines, args, variables)
	return ''.join(result_lines)

def pp_this_lines(file_lines:List[str], args:Dict[str, bool], variables:Dict[str, bool] = None) -> List[str]:
	""" List of lines Preprocessing. Return list of lines after preprocesing. """
	# стандартные значения, если не указаны:
	if not variables: variables = { "Initial": True, "True": True, "False": False }
	result_text:List[str] = [] # результат обработки: список строк
	arguments:Dict[str, Union[bool, Dict[str, bool]]] = {
		# словарь режимов (текущих аргументов):
		"include": True, # пока включен этот режим, строки добавляются в результат
		"pp": True, # пока включен этот режим, строки обрабатываются парсером
		"openif": False, # отметка о том, что открыт блок условия
		"savecomm": False, # отметка о том, что не нужно удалять специальные комментарии
		"openquote": False, # отметка, что были открыты кавычки
		"quote": "", # тип открытых кавычек
		"if": { "include": True, "pp": True, "savecomm": False } # список инструкций до выполнения блока условий
	}
	arguments.update(args)
	for line in file_lines:
		if _PP_DIRECTIVE_START.match(line): # проверяем является ли строка командой
			comm_list = line.split(':')# распарсим команду
			if arguments["pp"]: # только при включенном препроцессоре выполняются все команды.
				# проверяем, что за команда
				if _PP_ON_DIRECTIVE.match(comm_list[1]) or _PP_OFF_DIRECTIVE.match(comm_list[1]):
					# !@pp:on или !@pp:off
					pp_string(result_text, line, arguments)
				elif _PP_ONSAVECOMM_DIR.match(comm_list[1]): # !@pp:savecomm
					arguments["savecomm"] = True
				elif _PP_OFFSAVECOMM_DIR.match(comm_list[1]): # !@pp:nosavecomm
					arguments["savecomm"] = False
				elif _PP_OFFCONDITION_DIR.match(comm_list[1]): # !@pp:endif
					close_condition(arguments)
				elif _PP_VARIABLE_DIR.match(comm_list[1]): # !@pp:var(layer=123)
					directive = extract_directive(comm_list[1], 'var')
					add_variable(variables, directive)
				elif _PP_ONCONDITION_DIR.match(comm_list[1]): # !@pp:if(layer==45):off
					directive = extract_directive(comm_list[1], 'if') # получаем содержимое скобок
					condition = met_condition(variables, directive) # проверяем условие
					open_condition(comm_list[2], condition, arguments)
				else: # запись !@pp: отдельной строкой без команды не включается в выходной файл
					pass
			elif _PP_OFFCONDITION_DIR.match(comm_list[1]):
				close_condition(arguments)
			else:
				result_text.append(line)
		else: # если это не команда, обрабатываем строку
			pp_string(result_text, line, arguments)
	if arguments["openif"]:
		close_condition(arguments)
	return result_text

def _autotest():
	""" Autotest will works if all files are exists. """
	import time
	args={"include":True, "pp":True, "savecomm":False} # глобальные значения
	source_file_path = "../../[examples]/example_preprocessor/pptest.qsps"
	autotest_file_path = "../../[examples]/example_preprocessor/for_autotest.qsps"
	with open(source_file_path, 'r', encoding='utf-8') as pp_file:
		input_lines = pp_file.readlines()
	if True:
		old_time = time.time()
		output_lines = pp_this_lines(input_lines, args)
		new_time = time.time()
	print(f'Time of preprocessing: {new_time - old_time}')
	with open(autotest_file_path, 'r', encoding='utf-8') as pp_file:
		autotest_lines = pp_file.readlines()
	s = len(output_lines)
	a = len(autotest_lines)
	for i in range(max(a, s)):
		if i > s-1:
			print('Missing lines: ', autotest_lines[i:])
			return None
		elif i > a-1:
			print('Extra lines:', output_lines[i:])
			return None
		elif output_lines[i] != autotest_lines[i]:
			print('Lines don\'t match', [output_lines[i], autotest_lines[i]])
			return None
	print('Autotest is ok!')

# main
def main():
	args={"include":True, "pp":True, "savecomm":False} # глобальные значения
	source_file_path = "../../[examples]/example_preprocessor/pptest.qsps"
	output_file_path = "../../[examples]/example_preprocessor/output.qsps"
	output_text = pp_this_file(source_file_path, args)
	with open(output_file_path, 'w', encoding='utf-8') as fp:
		fp.write(output_text)

if __name__ == '__main__':
    _autotest()