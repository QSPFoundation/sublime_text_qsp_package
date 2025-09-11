import os, json

import re

from dataclasses import dataclass
from typing import (List, Literal, Tuple, Dict, Match, Optional, Callable)



# unknowns
_NON_SPACE = re.compile(r'\S+')

# quotes
_APOSTROPH = re.compile(r"'")
_QUOTE = re.compile(r'"')
_BRACE_OPEN = re.compile(r'\{')
_BRACE_CLOSE = re.compile(r'\}')

# statements
_STAR_P = re.compile(r'\*P\b', re.IGNORECASE)
_STAR_PL = re.compile(r'\*PL\b', re.IGNORECASE)
_STAR_NL = re.compile(r'\*NL\b', re.IGNORECASE)
_ACT_OPEN = re.compile(r'\bACT\b', re.IGNORECASE)
_IF_OPEN = re.compile(r'\bIF\b', re.IGNORECASE)
_LOOP_OPEN = re.compile(r'\bLOOP\b', re.IGNORECASE)

_WS = re.compile(r'[ \t]+')
_MWS = re.compile(r'[ \t\n\r]+')

@dataclass
class QspScope:
	name: str
	region: Tuple[int, int]
	parent: 'QspScope'
	daughters: List['QspScope']

@dataclass
class QspToken:
	name: str
	instr: int
	match: re.Match
	region_offset: int

@dataclass
class QspScopeCommand:
	cmd: Literal['find-end', 'ignore', 'new-scope', 'close-scope']
		# close - close the scope
		# ignore - move peek after token
		# new-scope - open daughter-scope
	token: QspToken
	peek_offset: int


class BaseAnalyser:
	""" анализатор Базовых действий и описания. """
	def __init__(self, base_qsps:str) -> None:
		self.base_qsps:str = base_qsps
		self.base_region:Tuple[int, int] = (0, len(base_qsps)-1)
		self.peek:int = self.base_region[0]

	def analyse(self) -> None:
		""" Анализирует базовое описание и действия, представленные в виде QSPS-кода. """
		current_scope = QspScope('base', self.base_region, None, [])
		while self.peek < len(self.base_qsps):
			finded = self._parse(current_scope)
			if finded is None:
				# TODO: выдать предупреждение
				break
			if finded.cmd == 'find-end':
				# Токены не найдены. Значит в qsps-коде ошибка, либо файл кончился
				self.peek = self.base_region[1]+1
				break
			elif finded.cmd == 'ignore':
				# Это игнорируемый набор символов. Т.е. его не включаем в дерево разбора
				# просто перемещаем пик
				self.peek = finded.peek_offset
			elif finded.cmd == 'new-scope':
				# Открываем новый скоуп
				token = finded.token
				self.peek = finded.peek_offset
				scope_name = token.name
				scope_region = (self.peek, self.base_region[1]) # окончание региона не известно
				scope_parent = current_scope
				current_scope = QspScope(scope_name, scope_region, scope_parent, [])
				scope_parent.daughters.append(current_scope)
			elif finded.cmd == 'close-scope':
				# закрываем скоуп
				...

	def _parse(self, scope:QspScope) -> QspScopeCommand:
		"""Данная функция запускает тот или иной парсер в зависимости от типа скоуп. """
		_parse = None
		if scope.name == 'base':
			_parse = self._parse_base
		if _parse is not None:
			return _parse()
		return None
		

	def _parse_base(self) -> QspScopeCommand:
		""" запуск основного поиска """
		# список токенов для поиска:
		tokens = {
			# ignored scopes tokens
			'spaces': _MWS, # spaces

			# new scopes tokens
			'quote-implicit-statement': _QUOTE, # "
			'apostroph-implicit-statement': _APOSTROPH, # '
			'star-p-statement': _STAR_P, # *p
			'star-pl-statement': _STAR_PL, # *pl
			'star-nl-statement': _STAR_NL, # *nl
			'act-statement': _ACT_OPEN, # act
			'if-statement': _IF_OPEN, # if
			'brace-implicit-statement': _BRACE_OPEN, # {
			'loop-statement': _LOOP_OPEN, # loop
			'unknown-statement': _NON_SPACE # unknown
		}
		# поиск токена
		region = (self.peek, self.base_region[1])
		token = self._token_search(tokens, region)
		if token is None:
			# Если токен не найден, для base это означает, что оно кончилось
			# в этом случае вместо
			return QspScopeCommand('find-end', None, None)
		elif token.name == 'spaces':
			# игнорируем пробелы
			return QspScopeCommand('ignore', token, token.match.end(0) + token.region_offset)
		else:
			# все токены операторов открывают новый скоуп
			return QspScopeCommand('new-scope', token, token.match.start(0) + token.region_offset)
	
	def _token_search(self, tokens:Dict[str, re.Pattern], region:Tuple[int, int]) -> None:
		""" Поиск токена по региону. """
		string = self._cut_region(region)
		rc = region[0]
		minimal = len(string)+1
		last_token = QspToken('', minimal, None)
		for token_name, pattern in tokens.items():
			match = pattern.search(string)
			if match is not None:
				# найден токен. Обновляем минимальное значение
				minimal = min(last_token.instr, match.start(0))
				# если минимальное значение обновилось, обновляем последний токен
				if minimal != last_token.instr:
					last_token = QspToken(token_name, minimal, match, rc)
				elif minimal == last_token.instr:
					# токены на одной позиции. Сравниваем по длине
					if len(match.group(0)) > len(last_token.match.group(0)):
						last_token = QspToken(token_name, minimal, match, rc)
					elif len(match.group(0)) == len(last_token.match.group(0)):
						# если токены на одной позиции и с одинаковой длиной, значит это ошибка!!!
						raise ValueError(f'Совпадение токенов: {last_token.name} и {token_name}')
		if last_token.instr != len(string)+1:
			return last_token
		return None

	def _cut_region(self, region:Tuple[int, int]) -> str:
		""" Вырезает из текста указанный регион """
		return self.base_qsps[region[0]:region[1]+1]