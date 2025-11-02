from typing import Any, Callable, List, Dict, Union, Optional

from pp_tokens import PpToken as tkn
from pp_tokens import PpTokenType as tt

Stack = List[str]

class PpScanner:
    """ Scanner for QspsPP. """
    def __init__(self, qsps_lines: List[str]) -> None:
        self._qsps_lines = qsps_lines
        self._qsps_len:int = len(self._qsps_lines) # число строк

        self._tokens: List[tkn] = [] # список токенов

        self._offset:int = 0 # смещение относительно начала файла
        self._current:int = 0 # указатель на текущий символ в строке

        self._line:str = '' # значение текущей строки
        self._line_len:int = 0 # длина текущей строки
        self._line_num:int = 0 # номер текущей строки
        
        self._lexeme_start:tuple = ( # начало текущей лексемы
            self._line, # строка
            self._current # символ в строке
        )

        self._scan_funcs:List[Callable[[str], None]] = [self._qsps_file]
        self._prepend_chars:Stack = [] # ожидаемые символы в обратном порядке

        self.keywords:Dict[str, tt] = {
            "var": tt.VAR_STMT,
            "on": tt.ON_STMT,
            "if": tt.IF_STMT,
            "off": tt.OFF_STMT,
            "savecomm": tt.SAVECOMM_STMT,
            "nosavecom": tt.NO_SAVECOMM_STMT,
            "nopp": tt.NOPP_STMT,
            "include": tt.INCLUDE_STMT,
            "exclude": tt.EXCLUDE_STMT,
            "and": tt.AND_OPERATOR,
            "or": tt.OR_OPERATOR,
            "not": tt.NOT_OPERATOR,
            "endif": tt.ENDIF_STMT
        }
        self._curlexeme:List[str] = []
        self._pp_directive:str = ''
        self._expected_token:tt = tt.RAW_LINE
        self._edge:tuple = tuple()

    def scan_tokens(self) -> None:
        """ Find all tokens in the file. """
        for j, line in enumerate(self._qsps_lines):
            self._line_num = j
            self._line = line
            self._scan_line(line)
            
        self._tokens.append(tkn(tt.EOF, "", None, self._line))

    def _scan_line(self, line:str) -> None:
        """ Find all tokens in the line. """
        self._line_len = len(line)
        for i, c in enumerate(line):
            self._current = i
            self._curlexeme.append(c)
            self._scan_funcs[-1](c)
            
    # методы поиска, учитывающие контекст
    def _qsps_file_expect(self, c:str) -> None:
        """ Поиск токенов, из которых состоит qsps-файл """
        if self._current == 0:
            # Если это первый символ в строке, ищем начало локации или начало директивы
            if c == "#":
                # Начало локации, значит это токен начала локации,
                # просто добавляем поглощение токена в список:
                self._scan_funcs.append(self._loc_open_expect)
            elif c == "!" and self._line_len >= 5 and self._line[0:5] == '!@pp:':
                # Начало директивы препроцессора. Это однозначно, осталось поглотить токен.
                self._add_expected_chars('@pp:')
                self._scan_funcs.append(self._pp_directive_stmt_expect)
            else:
                # Любой другой символ, это начало сырой строки
                self._scan_funcs.append(self._raw_line_end_expect)
        else:
            # такой вариант невозможен, но предусмотрительно обрабатываем, как сырую строку
            self._scan_funcs.append(self._raw_line_end_expect)

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
            self._scan_funcs.append(self._raw_line_end_expect)
            return
        
        # ожидаемый символ совпадает с текущим:
        if not self._prepend_chars:
            # директива препроцессора закончена
            self._add_token(tt.OPEN_DIRECTIVE_STMT)
            self._scan_funcs.pop() # убираем функцию из стека
            self._scan_funcs.append(self._scan_pp_dirrective) # добавляем функцию для сканирования директивы
        else:
            # директива препроцессора не закончена, просто продолжаем
            pass

    def _scan_pp_dirrective(self, c:str) -> None:
        """ Распознаём внутренние токены директивы """
        if c in (" ", "\t", "\r", "\n"):
            # пробелы не учитываются
            self._curlexeme = [] # очищаем текущую лексему
        elif c == ":":
            # токен then
            self._add_token(tt.THEN_STMT)
        elif c == "(":
            self._add_token(tt.LEFT_PAREN)
        elif c == ")":
            self._add_token(tt.RIGHT_PAREN)
        elif c == "=":
            # Либо это assignment либо начало equal
            next_char = self._next_in_line()
            if next_char != "=":
                # assignment
                self._add_token(tt.ASSIGNMENT_OPERATOR)
            else:
                self._scan_funcs.append(self._equal_expect)
        elif c == "!":
            next_char = self._next_in_line()
            if next_char != "=":
                self._scan_funcs.append(self._raw_text_expect)
            else:
                self._scan_funcs.append(self._equal_expect)
        elif self._is_alnum(c):
            # если это \w, ожидается, что мы имеем дело с идентификатором
            # ключевым словом и т.п.
            self._scan_funcs.append(self._identifier_expect)
        else:
            # любой другой символ включает выборку сырого текста до конца строки
            self._scan_funcs.append(self._raw_text_expect)
        
        if self._current_is_last_in_line():
            # если это последний символ строки, добавляем токен конца строки
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
            ttype:Optional[tt] = self.keywords.get(self._curlexeme, None)
            if ttype == None: ttype = tt.IDENTIFIER
            self._add_token(ttype)
            self._scan_funcs.pop()

    def _raw_line_end_expect(self, c:str, ttype:tt = tt.RAW_LINE) -> None:
        """ Поглощение токена сырой строки. """
        # самый надёжный способ это проверить, последний ли это символ
        if self._current_is_last_in_line():
            # это последний символ, закрываем сырую строку, убираем функцию из стека
            self._add_token(ttype)
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
        if self._current_is_last_in_line:
            self._add_token(tt.LOC_OPEN)
            self._scan_funcs.pop()

    def _loc_body_expect(self, c:str) -> None:
        """ Сканирование тела локации. """
        cn:int = self._current
        # В первую очередб нужно проверить, не является ли очередная строка концом локации
        if cn == 0 and c in ('-', '!'):
            if c == '-' and self._peek_next() == '-':
                # если следующий символ является -, поглощаем строку, как конец локации
                self._scan_funcs.append(self._loc_end_expect)
            elif c == '!':
                # распознавание комментария
                self._scan_funcs.append(self._comment_stmt_expect)
        elif c == "\"":
            # поглощение строки в кавычках
            # открывающая кавычка является токеном
            self._add_token(tt.OPEN_QUOTE)
            self._scan_funcs.append(self._quoted_string_expect)
        elif c == "'":
            self._add_token(tt.OPEN_APOSTROPHE)
            self._scan_funcs.append(self._apostrophe_string_expect)
        elif c == "{":
            # блок кода
            self._add_token(tt.LEFT_BRACE)
            self._scan_funcs.append(self._code_block_expect)

    


    def _comment_stmt_expect(self, c:str) -> None:
        """ Распознавание специального комментария """
        pn:int = self._current - 1
        if c == '@' and pn == 0:
            # это спецкомментарий. Определяем, что это за спецком
            if self._qsps_lines[self._line][pn:5] == '!@pp:':
                # Включаем ожидание команды препроцессора
                self._add_expected_chars('pp:')
                self._scan_funcs.append(self._open_pp_directive_stmt_expect)
            elif self._qsps_lines[self._line][pn:3] == '!@<':
                # включаем распознавание коммментария к удалению
                self._expected_token = tt.LESS_SPEC_COMM
                self._scan_funcs.append(self._comment_body_expect)
            else:
                # простой спецкоментарий
                self._expected_token = tt.SIMPLE_SPEC_COMM
                self._scan_funcs.append(self._comment_body_expect)
        else:
            self._expected_token = tt.SIMPLE_COMM
            self._scan_funcs.append(self._comment_body_expect)
        self._scan_funcs.pop()

    def _comment_body_expect(self, c:str) -> None:
        """Поглощение всего тела комментария."""
        if c == "{":
            # включаем поглощение блока
            self._scan_funcs.append(self._comm_code_block_expect)
        elif c == "\"":
            # Включаем поглощение строки в кавычках
            self._scan_funcs.append(self._comm_quoted_string_expect)
        elif c == "'":
            # Включаем поглощение строки в апострофах
            self._scan_funcs.append(self._comm_apostrophed_string_expect)
        elif self._current_is_last_in_line():
            # если любой другой символ и он последний в строке,
            # закрываем токен комментария
            self._add_token(self._expected_token)
            self._scan_funcs.pop()
        else:
            # любой непоследний символ в строке просто поглощается
            pass

    def _comm_code_block_expect(self, c:str) -> None:
        """ Поглощение блока внутри комментария """
        if c == "{":
            # поглощение внутреннего блока
            self._scan_funcs.append(self._comm_code_block_expect)
        elif c == "}":
            # закрываем блок
            self._scan_funcs.pop()
        else:
            # остальные символы, какие бы они ни были, просто поглощаются
            pass

    def _comm_quoted_string_expect(self, c:str) -> None:
        """ Поглощение строки внутри комментария """
        if c == "\"":
            # закрываем строку
            self._scan_funcs.pop()
        else:
            # остальные символы, какие бы они ни были, просто поглощаются
            pass

    def _comm_apostrophed_string_expect(self, c:str) -> None:
        """ Поглощение строки внутри комментария """
        if c == "'":
            # закрываем строку
            self._scan_funcs.pop()
        else:
            # остальные символы, какие бы они ни были, просто поглощаются
            pass
            

    def _loc_end_expect(self, c:str) -> None:
        """ До конца строки все символы поглощаются, как токен конца локации. """
        if self._current_is_last_in_line:
            # с окончанием строки закрываем токен
            self._add_token(tt.LOC_END_KWRD)
            self._scan_funcs.pop()

    # вспомогательные методы
    def _is_alnum(self, s:str) -> bool:
        """ is \w ? """
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

    def _set_lexeme_start(self) -> None:
        """ Устанавливаем начало лексемы. """
        self._lexeme_start = (self._line, self._current)

    def _is_line_end(self) -> bool:
        """ Проверяем, не закончилась ли строка. """
        return self._current >= len(self._qsps_lines[self._line])

    def _curline_is_last(self) -> bool:
        """ Текущая строка последняя? """
        return self._line == self._qsps_len - 1

    def _next_in_line(self) -> str:
        """ Возвращает следующий символ в строке """
        if self._current + 1 < self._line_len:
            return self._line[self._current + 1]
        else:
            return '\0'

    def _prev_in_line(self) -> str:
        """ Возвращает предыдущий символ в строке """
        if self._current > 0:
            return self._line[self._current - 1]
        else:
            return '\0'

    def _advance(self) -> str:
        """ Возвращаем текущий символ и перемещаем указатель """
        c = self._peek()
        self._to_next_char()
        return c

    def _to_next_char(self) -> None:
        """ Перемещает указатель на следующий символ """
        self._current += 1
        self._offset += 1

    def _peek(self) -> str:
        """ Возвращает текущий символ """
        if self._is_eof(): return '\0'
        return self._qsps_lines[self._line][self._current]

    def _peek_next(self) -> str:
        """ Возвращает следующий символ """
        if self._current_is_last_in_file: return '\0'
        if self._current_is_last_in_line:
            return self._qsps_lines[self._line+1][0]
        else:
            return self._line[self._current+1]

    def _peek_prev(self) -> str:
        """ Возвращает предыдущий символ """
        if self._line == 0 and self._current == 0: return '\0'
        if self._current == 0:
            return self._qsps_lines[self._line-1][-1]
        else:
            return self._line[self._current-1]

    def _add_token(self, ttype:tt, literal:Any = None) -> None:
        self._tokens.append(tkn(
            ttype,
            self._curlexeme,
            literal,
            self._line))

        self._curlexeme = ''

    def _add_expected_chars(self, chars:str) -> None:
        """Правильно добавляет ожидаемую последовательность символов. """
        self._prepend_chars = list(chars)
        self._prepend_chars.reverse()

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        print(f"Err. {message}: ({self._line_num}, {self._current}).")