from typing import Callable, List, Tuple, Literal

from .pp_tokens import PpToken as tkn, TokenNode
from .pp_tokens import PpTokenType as tt
from . import error as er

LineNum = int
CharNum = int
Point = Tuple[LineNum, CharNum]

Char = str
Stack = List[Char]

QspsLine = str
NoSaveComm = Literal[True, False]
IncludeLine = Literal[True, False]
MarkedLine = Tuple[
    QspsLine,
    NoSaveComm,
    IncludeLine
]

class PpScanner:
    """ Scanner for QspsPP. """

    _LOC_LINE_DELIMITERS = ("\"", "'", "{", "}", "[", "]", "(", ")", "&", "!", '\n')

    def __init__(self, marked_lines: List[MarkedLine]) -> None:
        self._marked_lines = marked_lines
        self._qsps_len:int = len(self._marked_lines) # число строк

        self._tokens: List[tkn] = [] # список токенов

        self._curchar:CharNum = 0 # указатель на текущий символ в строке

        self._line:MarkedLine = self._marked_lines[0] # значение текущей строки
        self._line_len:int = 0 # длина текущей строки
        self._line_num:LineNum = 0 # номер текущей строки
        
        self._start_lexeme:Point = (0, 0) # начало текущей лексемы (строка, позиция)

        self._scan_funcs:List[Callable[[str], None]] = [self._qsps_file_expect]
        self._prepend_chars:Stack = [] # ожидаемые символы в обратном порядке

        self._curlexeme:List[Char] = []

        self._error_check: bool = False

    def errored(self) -> bool:
        return self._error_check

    def scan_tokens(self) -> None:
        """ Find all tokens in the file. """
        for j, line in enumerate(self._marked_lines):
            self._line_num = j
            self._line = line
            self._scan_line(line)
            
        if self._curlexeme and self._scan_funcs:
            raise er.PpScannerRunError(f"no clean handler stack {''.join(self._curlexeme)}, {[foo.__name__ for foo in self._scan_funcs]}")

        self._tokens.append(tkn(tt.EOF, "", (-1, -1)))

    def get_tokens(self) -> List[tkn]:
        return self._tokens

    def get_token_nodes(self) -> List[TokenNode]:
        out_l: List[TokenNode] = []
        for t in self._tokens:
            out_l.append(t.get_as_node())
        return out_l

    def _scan_line(self, line:MarkedLine) -> None:
        """ Find all tokens in the line. """
        self._line_len = len(line[0])
        for i, c in enumerate(line[0]):
            self._curchar = i
            if not self._curlexeme:
                # если лексема пуста (начало новой лексемы), устанавливаем начало
                self._set_start_lexeme()
            self._curlexeme.append(c)
            # print(c, self._scan_funcs[-1].__name__)
            try:
                self._scan_funcs[-1](c)
            except er.PpScannerError as e:
                self._error_check = True
                print(e)
                self._scan_funcs.pop()
                self._scan_funcs.append(self._raw_loc_line_expect)

            
    # методы поиска, учитывающие контекст
    def _qsps_file_expect(self, c:str) -> None:
        """ Поиск токенов, из которых состоит qsps-файл """
        cn = self._curchar
        if cn == 0:
            # Если это первый символ в строке, ищем начало локации или начало директивы
            if c == "#":
                # Начало локации, значит это токен начала локации,
                # просто добавляем поглощение токена в список:
                self._scan_funcs.append(self._loc_open_expect)
            elif c in (' ', '\t'):
                # поглощаем токен преформатирования
                if self._next_in_line() in (' ', '\t'):
                    self._scan_funcs.append(self._preformatter_expect)
                else:
                    self._add_token(tt.PREFORMATTER)
            else:
                # Любой другой символ, это начало сырой строки
                if self._current_is_last_in_line():
                    self._add_token(tt.RAW_LINE)
                else:
                    self._scan_funcs.append(self._raw_line_end_expect)
        elif self._current_is_last_in_line():
            self._add_token(tt.RAW_LINE)
        else:
            self._scan_funcs.append(self._raw_line_end_expect)

    def _raw_line_end_expect(self, c:str) -> None:
        """ Поглощение токена сырой строки. """
        if self._current_is_last_in_line():
            # это последний символ, закрываем сырую строку, убираем функцию из стека
            self._add_token(tt.RAW_LINE)
            self._scan_funcs.pop()

    def _raw_text_expect(self, c:str) -> None:
        """ Токен сырого текста. Это любой текст, кроме конца строки.
        Закрывается концом файла, или перед концом строки. """
        if (self._current_is_last_in_file() or
            (self._next_is_last_in_line() and not self._curline_is_last())):
            self._add_token(tt.RAW_LINE)
            self._scan_funcs.pop()
                
    def _loc_open_expect(self, c:str) -> None:
        """ Распознавание имени локации """
        # имя локации - это то же самое, что и сырая строка, только с другим типом токена
        if self._current_is_last_in_line():
            self._add_token(tt.LOC_OPEN)
            self._scan_funcs.pop()
            self._scan_funcs.append(self._loc_body_scan)

    def _loc_close_expect(self, c:str) -> None:
        """ До конца строки все символы поглощаются, как токен конца локации. """
        if self._current_is_last_in_line():
            # с окончанием строки закрываем токен
            self._add_token(tt.LOC_CLOSE)
            self._scan_funcs.pop()

    def _preformatter_expect(self, c:str) -> None:
        """ Поглощение пробелов в начале строки """
        if not self._next_in_line() in (' ', '\t'):
            self._add_token(tt.PREFORMATTER) # формируем токен
            self._scan_funcs.pop() # отключаем поглощение

    def _ampersand_expect(self, c:str) -> None:
        """ Поглощение разделителя с постлежащими пробелами """
        if not self._next_in_line() in (' ', '\t'):
            self._add_token(tt.AMPERSAND)
            self._scan_funcs.pop()

    def _loc_body_scan(self, c:str) -> None:
        """ Сканирование тела локации. """
        cn:int = self._curchar
        if cn == 0 and c in (' ', '\t'):
            # пробелы с начала строки поглощаем до непробельного символа
            if self._next_in_line() in (' ', '\t'):
                self._scan_funcs.append(self._preformatter_expect)
            else:
                self._add_token(tt.PREFORMATTER)
        elif cn == 0 and c == '-' and self._next_in_line() == '-':
            # если следующий символ является -, поглощаем строку, как конец локации
            self._scan_funcs.pop() # закрываем сканер тела локации
            self._scan_funcs.append(self._loc_close_expect)
        elif c == '!' and cn+2 < self._line_len and self._line[0][cn:cn+3] == '!@<':
            # токен коммента под удаление строки
            self._add_expected_chars('@<')
            self._scan_funcs.append(self._less_spec_comm_tkn_expect)
        elif c == '!' and cn+1 < self._line_len and self._line[0][cn:cn+2] == '!@':
            self._add_expected_chars('@')
            self._scan_funcs.append(self._spec_comm_tkn_expect)
        elif c == '!':
            # токен простого комментария
            self._add_token(tt.EXCLAMATION_SIGN)
        elif c == "\"":
            # кавычка
            self._add_token(tt.QUOTE)
        elif c == "'":
            self._add_token(tt.APOSTROPHE)
        elif c == "{":
            # блок кода
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
            if self._next_in_line() in (' ', '\t'):
                self._scan_funcs.append(self._ampersand_expect)
            else:
                self._add_token(tt.AMPERSAND)
        elif c == '\n':
            self._add_token(tt.NEWLINE)
        elif (not self._next_in_line() in self._LOC_LINE_DELIMITERS and
              not self._current_is_last_in_line()):
            # предусматриваем, что следующий символ не является значимым токеном локации
            # тогда можно включить выборку сырой строки
            self._scan_funcs.append(self._raw_loc_line_expect)
        else:
            # если следующий символ является значимым токеном локации,
            # закрываем сырую строку на этом же символе
            self._add_token(tt.RAW_LOC_LINE)

    def _less_spec_comm_tkn_expect(self, c:str) -> None:
        """ Поглощение токена спецкомментария с удалением строки """
        need = self._prepend_chars.pop()
        if need != c:
            raise er.PpScannerError(self._line_num, self._curchar,
                        f"less_spec_comm_tkn_expect: expected '{need}', got '{c}'")

        if not self._prepend_chars:
            self._add_token(tt.LESS_SPEC_COMM)
            self._scan_funcs.pop()

    def _spec_comm_tkn_expect(self, c:str) -> None:
        """ Поглощение токена обычного спецкомментария """
        need = self._prepend_chars.pop()
        if need != c:
            raise er.PpScannerError(self._line_num, self._curchar,
                        f"spec_comm_tkn_expect: expected '{need}', got '{c}'")

        if not self._prepend_chars:
            self._add_token(tt.SIMPLE_SPEC_COMM)
            self._scan_funcs.pop()

    def _raw_loc_line_expect(self, c:str) -> None:
        """ Получение токена сырого текста на локации. """
        # Данная строка оканчивается, когда встречает токен, значимый для локации,
        # или конец строки, или конец файла
        if (self._next_in_line() in self._LOC_LINE_DELIMITERS or
            self._current_is_last_in_file()):
            self._add_token(tt.RAW_LOC_LINE)
            self._scan_funcs.pop()

    # вспомогательные методы
    def _is_alnum(self, s:str) -> bool:
        """ is \\w ? """
        return s.isalnum() or s == '_'

    def _current_is_last_in_line(self) -> bool:
        """ Является ли текущий символ последним в строке? """
        return self._curchar == self._line_len - 1

    def _next_is_last_in_line(self) -> bool:
        """ Является ли следующий символ последним в строке? """
        return self._curchar + 1 == self._line_len - 1

    def _current_is_last_in_file(self) -> bool:
        """ Является ли текущий символ последним в файле? """
        return self._curline_is_last() and self._current_is_last_in_line()

    def _next_is_last_in_file(self) -> bool:
        """ Является ли следующий символ последним в файле? """
        return self._curline_is_last() and self._next_is_last_in_line()

    def _set_start_lexeme(self) -> None:
        """ Устанавливаем начало лексемы. """
        self._start_lexeme = (self._line_num, self._curchar)

    def _curline_is_last(self) -> bool:
        """ Текущая строка последняя? """
        return self._line_num == self._qsps_len - 1

    def _next_in_line(self) -> str:
        """ Возвращает следующий символ в строке """
        if self._curchar + 1 < self._line_len:
            return self._line[0][self._curchar + 1]
        else:
            return '\0'

    def _prev_in_line(self) -> str:
        """ Возвращает предыдущий символ в строке """
        if self._curchar > 0:
            return self._line[0][self._curchar - 1]
        else:
            return '\0'

    def _add_token(self, ttype:tt) -> None:
        self._tokens.append(tkn(
            ttype,
            ''.join(self._curlexeme),
            self._start_lexeme,
            self._line[1],
            self._line[2]))

        self._curlexeme.clear()

    def _add_expected_chars(self, chars:str) -> None:
        """Правильно добавляет ожидаемую последовательность символов. """
        self._prepend_chars = list(chars)
        self._prepend_chars.reverse()
