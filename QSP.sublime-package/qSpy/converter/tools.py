# auxiable tools
from typing import List
from .tps import (
    QspsLine,
    ParseStringMode, Char
)

# constants:
QSP_CODREMOV = 5 # const of cyphering

def parse_string(qsps_line:QspsLine, mode:ParseStringMode) -> None:
    """ Parse opened string for location code and return open string chars.

        Модель слоёв стека `mode['quote']`:
        - внутри `"..."` / `'...'` фигурные скобки не учитываются;
        - внутри `{...}` кавычки и апострофы учитываются (свои слои стека);
        - фигурные скобки могут быть вложенными друг в друга.
        """
    for char in qsps_line:
        if not mode['quote']:
            if char in ('"', '\'', '{'): mode['quote'].append(char)
        elif mode['quote'][-1] == '{':
            if char in ('{', '"', '\''): mode['quote'].append(char)
            elif char == '}': mode['quote'].pop()
        elif char == mode['quote'][-1]:
            mode['quote'].pop()

def del_first_pref(lines:List[str]) -> List[str]:
	"""
		Delete first preformatted symbols from start of lines
	"""
	common:List[Char] = []
	for chars in zip(*lines):
		if len(set(chars)) == 1 and chars[0] in (' ', '\t'):
			common.append(chars[0])
		else:
			break
	if not common: return lines
	return [line[len(common):] for line in lines]
