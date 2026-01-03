import json

from typing import Any, List, Dict, Optional, Tuple, Callable

from pp_tokens import PpToken as Tkn
from pp_tokens import PpTokenType as tt

ScanHandler = Callable[[str], None]
HandlerStack = List[ScanHandler]

CharsStack = List[str]
QspsLine = str
QspsLines = List[QspsLine]


class DirsScaner:
    """ Scanner of Pp-Directives and Qsps-Lines tokens. """

    _KEYWORDS:Dict[str, tt] = {
            "var": tt.VAR_STMT,
            "on": tt.ON_STMT,
            "if": tt.IF_STMT,
            "off": tt.OFF_STMT,
            "savecomm": tt.SAVECOMM_STMT,
            "nosavecomm": tt.NO_SAVECOMM_STMT,
            "include": tt.INCLUDE_STMT,
            "exclude": tt.EXCLUDE_STMT,
            "and": tt.AND_OPERATOR,
            "or": tt.OR_OPERATOR,
            "not": tt.NOT_OPERATOR,
            "endif": tt.ENDIF_STMT
        }

    def __init__(self, qsps_lines: QspsLines) -> None:
        self._src_lines = qsps_lines

        self._tokens: List[Tkn] = [] # список токенов

        self._current:int = 0 # указатель на текущий символ в строке

        self._cur_line:QspsLine = '' # значение текущей строки
        self._line_len:int = 0 # длина текущей строки
        self._line_num:int = 0 # номер текущей строки
        
        self._start_lexeme:Tuple[int, int] = (0, 0) # начало текущей лексемы (строка, позиция)

        self._scan_funcs:HandlerStack = [self._qsps_file_expect]
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
            print(self._scan_funcs[-1].__name__)

        self._tokens.append(Tkn(tt.EOF, "", (-1, -1)))

    def _scan_line(self, line:str) -> None:
        """ Find all tokens in the line. """
        self._line_len = len(line)
        for i, c in enumerate(line):
            self._current = i
            if not self._curlexeme:
                # если лексема пуста (начало новой лексемы), устанавливаем начало
                self._set_start_lexeme()
            self._curlexeme.append(c)
            # print(c, self._scan_funcs[-1].__name__)
            self._scan_funcs[-1](c)
            
    # методы поиска, учитывающие контекст
    def _qsps_file_expect(self, c:str) -> None:
        """ Поиск токенов, из которых состоит qsps-файл """
        cn = self._current
        if cn == 0:
            # Если это первый символ в строке, ищем начало локации или начало директивы
            if c in (' ', '\t'):
                # поглощаем токен преформатирования
                self._scan_funcs.append(self._preformatter_expect)
            elif c == "!" and self._line_len >= 5 and self._cur_line[0:5] == '!@pp:':
                # Начало директивы препроцессора. Это однозначно, осталось поглотить токен.
                self._add_expected_chars('@pp:')
                self._scan_funcs.append(self._pp_directive_stmt_expect)
            else:
                # Любой другой символ, это начало сырой строки
                self._scan_funcs.append(self._qsps_line_expect)
        elif (self._tokens and self._tokens[-1].ttype == tt.PREFORMATTER):
            # если до этого мы поглощали токен преформатирования
            if c == "!" and len(self._cur_line[cn:]) > 5 and self._cur_line[cn:cn+5] == '!@pp:':
                # имеем дело с диррективой
                self._add_expected_chars('@pp:')
                self._scan_funcs.append(self._pp_directive_stmt_expect)
            else:
                # или с сырой строкой
                self._scan_funcs.append(self._qsps_line_expect)
        else:
            # такой вариант невозможен, но предусмотрительно обрабатываем, как сырую строку
            self._scan_funcs.append(self._qsps_line_expect)

    def _pp_directive_stmt_expect(self, c:str) -> None:
        """ Ожидание токена директивы препроцессора. """
        # Данный метод вызывается однозначно, это означает, что мы просто убеждаемся,
        # что поглощаем токен директивы препроцессора. На старте есть список ожидаемых
        # символов, поэтому проверку, не пуст ли список проводим только в конце метода.
        need = self._prepend_chars.pop() # какой символ ожидаем
        if need != c:
            # ожидаемый символ не совпадает с текущим, значит это:
            # 1. ошибка работы сканера
            self._error(f"pp_directive_stmt_expect: expected '{need}', got '{c}'")
            # 2. сырая строка
            self._scan_funcs.pop() # убираем функцию из стека
            self._scan_funcs.append(self._qsps_line_expect)
            return
        
        # ожидаемый символ совпадает с текущим:
        if not self._prepend_chars:
            # директива препроцессора закончена
            self._add_token(tt.OPEN_DIRECTIVE_STMT)
            self._scan_funcs.pop() # убираем функцию из стека
            self._scan_funcs.append(self._scan_pp_dirrective) # добавляем функцию для сканирования директивы

    def _scan_pp_dirrective(self, c:str) -> None:
        """ Распознаём внутренние токены директивы """
        if c in (" ", "\t", "\r", "\n"):
            # пробелы не учитываются
            self._curlexeme.clear() # очищаем текущую лексему
            self._set_start_lexeme() # устанавливаем начало следующей лексемы
        elif c == ":":
            # токен then
            self._add_token(tt.THEN_STMT)
        elif c == "(":
            self._add_token(tt.LEFT_PAREN)
        elif c == ")":
            self._add_token(tt.RIGHT_PAREN)
        elif c == "=":
            # Либо это assignment либо начало equal
            if self._next_in_line() != "=":    # assignment
                self._add_token(tt.ASSIGNMENT_OPERATOR)
            else:
                self._scan_funcs.append(self._equal_expect)
        elif c == "!":
            if self._next_in_line() != "=":
                self._scan_funcs.append(self._qsps_line_expect)
            else:
                self._scan_funcs.append(self._equal_expect)
        elif self._is_alnum(c):
            # если это \w, ожидается, что мы имеем дело с идентификатором
            # ключевым словом и т.п.
            self._scan_funcs.append(self._identifier_expect)
        else:
            # любой другой символ включает выборку сырого текста до конца строки
            self._scan_funcs.append(self._qsps_line_expect)
        
        if self._current_is_last_in_line():
            # если это последний символ строки, добавляем токен конца строки
            if c == '\n': self._curlexeme.append(c)
            self._add_token(tt.NEWLINE)
            # удаляем парсер директив из стека
            self._scan_funcs.pop()
    
    def _equal_expect(self, c:str) -> None:
        """ Получает токен оператора сравнения """
        # предыдущий символ уже поглощён, и он ! или =
        prev_char = self._prev_in_line()
        if prev_char == '=':
            self._add_token(tt.EQUAL_EQUAL)
        elif prev_char == '!':
            self._add_token(tt.EQUAL_NOT_EQUAL)
        else:
            self._error(f"equal_expect: expected '=', got '{c}'")
        self._scan_funcs.pop()

    def _identifier_expect(self, c:str) -> None:
        """ Сборка идентификатора директивы препроцессора. """
        # Если следующий символ не буква, не цифра и не символ подчёркивания, закрываем
        next_char = self._next_in_line()
        if not self._is_alnum(next_char):
            ttype:Optional[tt] = self._KEYWORDS.get(''.join(self._curlexeme), None)
            if ttype == None: ttype = tt.IDENTIFIER
            self._add_token(ttype)
            self._scan_funcs.pop()

    def _qsps_line_expect(self, c:str) -> None:
        """ Поглощение токена сырой строки. """
        if self._current_is_last_in_line():
            # это последний символ, закрываем сырую строку, убираем функцию из стека
            self._add_token(tt.QSPS_LINE)
            self._scan_funcs.pop()

    def _preformatter_expect(self, c:str) -> None:
        """ Поглощение пробелов в начале строки """
        if not self._next_in_line() in (' ', '\t'):
            self._add_token(tt.PREFORMATTER) # формируем токен
            self._scan_funcs.pop() # отключаем поглощение

    # вспомогательные методы
    def _is_alnum(self, s:str) -> bool:
        """ is \\w ? """
        return s.isalnum() or s == '_'

    def _current_is_last_in_line(self) -> bool:
        """ Является ли текущий символ последним в строке? """
        return self._current == self._line_len - 1

    def _next_is_last_in_line(self) -> bool:
        """ Является ли следующий символ последним в строке? """
        return self._current + 1 == self._line_len - 1

    def _current_is_last_in_file(self) -> bool:
        """ Является ли текущий символ последним в файле? """
        return self._curline_is_last() and self._current_is_last_in_line()

    def _next_is_last_in_file(self) -> bool:
        """ Является ли следующий символ последним в файле? """
        return self._curline_is_last() and self._next_is_last_in_line()

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
        else:
            return '\0'

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
        print(f"Err. {message}: ({self._line_num}, {self._current}).")

def _main():
    import time
    path = "..\\..\\[examples]\\example_preprocessor\\pptest.qsps"
    outp = ".\\_test\\dirs-tokens.json"
    with open(path, 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
    old = time.time()
    scanner = DirsScaner(lines)
    scanner.scan_tokens()
    new = time.time()
    print(['scanner-time', new-old])
    l: List[Dict[str, Any]] = []
    for t in scanner.get_tokens():
        l.append(t.get_as_node())
    with open(outp, 'w', encoding='utf-8') as fp:
        json.dump(l, fp, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    _main()