from typing import Callable, Dict, List, Tuple
import json


ScanHandler = Callable[[str], None]
HandlerStack = List[ScanHandler]

Char = str
CharsStack = List[Char]
QspsLine = str
QspsLines = List[QspsLine]

if __name__ == "__main__":
    from base_tokens import BaseToken as Tkn
    from base_tokens import BaseTokenType as tt
else:
    from .base_tokens import BaseToken as Tkn
    from .base_tokens import BaseTokenType as tt

class BaseScaner:
    """ Scanner of Base block of location. """
    _STMT_DELIMITERS = (
        "\"", "'", "{", "}", "[", "]", "(", ")",
        "&", "!", '\n', ' ', '\t', '?', ':',
        '>', '<', '=', '*', '+', '-', '/', '\\', ';', '\0')

    _KEYWORDS:Dict[str, tt] = {
        "act": tt.ACT_STMT,
        "end": tt.END_STMT,
        "if": tt.IF_STMT,
        "*p": tt.STAR_P_STMT,
        "*pl": tt.STAR_PL_STMT,
        "*nl": tt.STAR_NL_STMT,
        "loop": tt.LOOP_STMT,
    }
    def __init__(self, qsps_lines: List[QspsLine]) -> None:
        self._src_lines = qsps_lines

        self._tokens: List[Tkn] = [] # список токенов

        self._current:int = 0 # указатель на текущий символ в строке

        self._cur_line:QspsLine = '' # значение текущей строки
        self._line_len:int = 0 # длина текущей строки
        self._line_num:int = 0 # номер текущей строки
        
        self._start_lexeme:Tuple[int, int] = (0, 0) # начало текущей лексемы (строка, позиция)

        self._scan_funcs:HandlerStack = [self._base_scan]
        self._prepend_chars:CharsStack = [] # ожидаемые символы в обратном порядке

        self._curlexeme:List[str] = []

    def get_tokens(self) -> List[Tkn]:
        return self._tokens

    def scan_tokens(self) -> None:
        """ Find all dir-tokens in the file. """
        for j, line in enumerate(self._src_lines):
            self._line_num = j
            self._cur_line = line
            self._scan_line(line)
            
        if self._curlexeme and self._scan_funcs:
            self._logic_error(f'no clean handler stack [{self._scan_funcs[-1].__name__}]')

        self._tokens.append(Tkn(tt.EOF, "", (-1, -1)))

    def _scan_line(self, line:str) -> None:
        """ Find all tokens in the line. """
        self._line_len = len(line)
        for i, c in enumerate(line):
            self._current = i
            print([i,c, self._scan_funcs[-1].__name__],)
            if not self._curlexeme:
                # если лексема пуста (начало новой лексемы), устанавливаем начало
                self._set_start_lexeme()
            self._curlexeme.append(c)
            # print(c, self._scan_funcs[-1].__name__)
            self._scan_funcs[-1](c)

    def _base_scan(self, c:Char) -> None:
        """Поиск всяких токенов"""
        cn = self._current
        if cn == 0 and c in (' ', '\t'):
            # поглощаем токен преформатирования
            self._scan_funcs.append(self._preformatter_expect)
        elif c in (' ', '\t'):
            self._curlexeme.clear() # пробелы не учитываем
        elif c == '"':
            # поглощение литерала строки
            self._scan_funcs.append(self._quote_string_literal_expect)
        elif c == "'":
            self._scan_funcs.append(self._apostrophe_string_literal_expect)
        elif c == "{":
            self._add_token(tt.LEFT_BRACE)
        elif c == "}":
            self._add_token(tt.RIGHT_BRACE)
        elif c == "[":
            self._add_token(tt.LEFT_BRACKET)
        elif c == "]":
            self._add_token(tt.RIGHT_BRACKET)
        elif c == "(":
            self._add_token(tt.LEFT_PAREN)
        elif c == ")":
            self._add_token(tt.RIGHT_PAREN)
        elif c == "&":
            self._add_token(tt.AMPERSAND)
        elif c == '\n':
            self._add_token(tt.NEWLINE)
        elif c in (' ', '\t'):
            pass
        elif c == "!":
            self._add_token(tt.EXCLAMATION_SIGN)
        elif c == ":":
            self._add_token(tt.THEN)

        # Identifiers    
        elif self._is_alnum(c):
            self._scan_funcs.append(self._identifier_expect)
        elif self._cur_line[cn:cn+2].lower() == '*p' and self._word_edges(cn, cn+2):
            self._add_expected_chars('p')
            self._scan_funcs.append(self._identifier_expect)
        elif self._cur_line[cn:cn+3].lower() == '*pl' and self._word_edges(cn, cn+2):
            self._add_expected_chars('pl')
            self._scan_funcs.append(self._identifier_expect)
        elif self._cur_line[cn:cn+3].lower() == '*nl' and self._word_edges(cn, cn+2):
            self._add_expected_chars('nl')
            self._scan_funcs.append(self._identifier_expect)
        elif c in self._STMT_DELIMITERS:
            self._add_token(tt.DELIMITER)
        elif (not self._next_in_line() in self._STMT_DELIMITERS and
              not self._current_is_last_in_line()):
            self._scan_funcs.append(self._raw_base_line_expect)
        else:
            self._add_token(tt.RAW_TEXT)
        

    def _identifier_expect(self, c:Char) -> None:
        """ Сборка идентификатора директивы препроцессора. """
        # Если следующий символ не буква, не цифра и не символ подчёркивания, закрываем
        next_char = self._next_in_line()
        print([c, next_char])
        if not self._is_alnum(next_char):
            print('\n')
            ttype:tt = self._KEYWORDS.get(''.join(self._curlexeme), tt.IDENTIFIER)
            self._add_token(ttype)
            self._scan_funcs.pop()

    def _quote_string_literal_expect(self, c:Char) -> None:
        """Поглощение литерала строки"""
        if c == '"':
            if self._next() == c:
                # Если за текущим символом идёт символ конца строки, поглощаем escape последовательность
                self._add_expected_chars('"')
                self._scan_funcs.append(self._escape_expect)
                return
            self._add_token(tt.QUOTE_STRING)
    
    def _apostrophe_string_literal_expect(self, c:Char) -> None:
        """Поглощение литерала строки"""
        if c == "'":
            if self._next() == c:
                # Если за текущим символом идёт символ конца строки, поглощаем escape последовательность
                self._add_expected_chars("'")
                self._scan_funcs.append(self._escape_expect)
                return
            self._add_token(tt.APOSTROPHE_STRING)

    def _preformatter_expect(self, c:Char) -> None:
        """ Поглощение пробелов в начале строки """
        if not self._next_in_line() in (' ', '\t'):
            self._add_token(tt.PREFORMATTER)
            self._scan_funcs.pop()

    def _escape_expect(self, c:Char) -> None:
        need = self._prepend_chars.pop()
        if need != c:
            self._error(f"escape_expect: expected '{need}', got '{c}'")
            self._scan_funcs.pop() # убираем функцию из стека
            return

        if not self._prepend_chars:
            self._scan_funcs.pop()

    def _raw_base_line_expect(self, c:str) -> None:
        """ Получение токена сырого текста в коде основного описания и действий. """
        # Данная строка оканчивается, когда встречает токен, значимый для локации,
        # или конец строки, или конец файла
        if (self._next_in_line() in self._STMT_DELIMITERS):
            self._add_token(tt.RAW_TEXT)
            self._scan_funcs.pop()

    # вспомогательные методы
    def _is_alnum(self, s:str) -> bool:
        """ is \\w ? """
        return s.isalnum() or s in ('_', '$', '%')

    def _current_is_last_in_line(self) -> bool:
        """ Является ли текущий символ последним в строке? """
        return self._current == self._line_len - 1

    def _next_is_last_in_line(self) -> bool:
        """ Является ли следующий символ последним в строке? """
        return self._current + 1 == self._line_len - 1

    def _set_start_lexeme(self) -> None:
        """ Устанавливаем начало лексемы. """
        self._start_lexeme = (self._line_num, self._current)

    def _curline_is_last(self) -> bool:
        """ Текущая строка последняя? """
        return self._line_num == len(self._src_lines) - 1

    def _next_in_line(self) -> str:
        """ Возвращает следующий символ в строке """
        if self._current + 1 < self._line_len:
            return self._cur_line[self._current + 1]
        else:
            return '\0'

    def _prev_in_line(self) -> str:
        """ Возвращает предыдущий символ в строке """
        if self._current > 0:
            return self._cur_line[self._current - 1]
        return '\0'

    def _prev(self, char_num:int = -1) -> Char:
        if char_num == -1: char_num = self._current
        if char_num > 0:
            return self._cur_line[char_num - 1]
        elif self._line_num > 0:
            return self._src_lines[self._line_num - 1][-1]
        return '\0'

    def _next(self, char_num:int=-1) -> Char:
        if char_num == -1: char_num = self._current
        if char_num + 1 < self._line_len:
            return self._cur_line[char_num + 1]
        elif self._line_num + 1 < len(self._src_lines):
            return self._src_lines[self._line_num + 1][0]
        return '\0'

    def _word_edges(self, word_start:int, word_end:int) -> bool:
        """Проверяет, является ли лексема самостоятельным словом"""
        return (self._prev(word_start-1) in self._STMT_DELIMITERS
            and self._next(word_end+1) in self._STMT_DELIMITERS)


    def _add_token(self, ttype:tt) -> None:
        self._tokens.append(Tkn(
            ttype,
            ''.join(self._curlexeme),
            self._start_lexeme))

        self._curlexeme.clear()

    def _add_expected_chars(self, chars:str) -> None:
        """Правильно добавляет ожидаемую последовательность символов. """
        self._prepend_chars = list(chars)
        self._prepend_chars.reverse()

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        print(f"Dirs-Scanner. {message}: ({self._line_num}, {self._current}).")

    def _logic_error(self, message:str) -> None:
        print(f"Dirs-Scanner Logic error: {message}. Please, report to the developer.")

if __name__ == "__main__":
    with open('base_example.qsps', 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
    scanner = BaseScaner(lines)
    scanner.scan_tokens()
    tokens = [t.get_as_node() for t in scanner.get_tokens()]
    with open('base_example.json', 'w', encoding='utf-8') as fp:
        json.dump(tokens, fp, indent=4, ensure_ascii=False)