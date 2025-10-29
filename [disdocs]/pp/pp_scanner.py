from typing import Any, Callable, List, Dict, Union, Optional

from pp_tokens import PpToken as tkn
from pp_tokens import PpTokenType as tt

class PpScanner:
    """ Scanner for QspsPP. """
    def __init__(self, qsps_lines: List[str]) -> None:
        self._qsps_lines = qsps_lines
        self._qsps_len = len(self._qsps_lines)
        self._tokens: List[tkn] = []

        self._offset = 0 # смещение относительно начала файла
        self._current = 0 # указатель на текущий символ в строке
        self._line = 0 # номер текущей строки
        self._line_len = 0 # длина текущей строки
        
        self._lexeme_start = ( # начало текущей лексемы
            self._line, # строка
            self._current # символ в строке
        )

        self._scan_funcs:List[Callable[[str], None]] = [self._qsps_file]
        self._prepend_chars:List[str] = [] # ожидаемые символы в обратном порядке

        self.keywords:Dict[str, tt] = {
            
        }
        self._curlexeme = ''
        self._pp_directive = ''
        self._expected_token = tt.RAW_LINE

    def scan_tokens(self) -> None:
        """ Find all tokens in the file. """
        # to self._tokens
        for j, line in enumerate(self._qsps_lines):
            self._line = j
            self._scan_line(line)
            
        self._tokens.append(tkn(tt.EOF, "", None, self._line))

    def _scan_line(self, line:str) -> None:
        """ Find all tokens in the line. """
        self._line_len = len(line)
        for i, c in enumerate(line):
            self._current = i
            self._curlexeme += c
            self._scan_funcs[-1](c)
            
    # методы поиска, учитывающие контекст
    def _qsps_file_expect(self, c:str) -> None:
        """ Поиск токенов, из которых состоит qsps-файл """
        cn:int = self._current
        if cn == 0:
            # Если это первый символ в строке, ищем начало локации или начало директивы
            if c == "#":
                # Начало локации, значит это токен начала локации,
                # просто добавляем токен в список:
                self._add_token(tt.LOC_DEF_KWRD)
                self._scan_funcs.append(self._loc_name_expect)
            elif c == "!":
                # Начало комментария.
                # Включаем ожидание команды препроцессора
                self._add_expected_chars('@pp:')
                self._scan_funcs.append(self._open_pp_directive_stmt_expect)
            else:
                # Любой другой символ, это сырая строка
                self._scan_funcs.append(self._raw_line_end_expect)
        else:
            # такой вариант невозможен, но предусмотрительно обрабатываем, как сырую строку
            self._scan_funcs.append(self._raw_line_end_expect)

    def _raw_line_end_expect(self, c:str, ttype:tt = tt.RAW_LINE) -> None:
        """Поиск токена конца строки."""
        # самый надёжный способ это проверить, последний ли это символ
        if self._current >= self._line_len - 1:
            # это последний символ, закрываем сырую строку, убираем функцию из стека
            self._add_token(ttype)
            self._scan_funcs.pop()

    def _raw_text_expect(self, c:str) -> None:
        """ Данный токен закрывается до конца строки. """
        if self._current + 1 >= self._line_len - 1:
            self._add_token(tt.RAW_LINE)
            self._scan_funcs.pop()

    def _open_pp_directive_stmt_expect(self, c:str) -> None:
        """ Поиск токена оператора директивы """
        if self._prepend_chars:
            # ожидаемые символы ещё есть
            need = self._prepend_chars.pop() # какой символ ожидаем
            if need != c:
                # ожидаемый символ не совпадает с текущим, значит это сырая строка
                self._scan_funcs.pop()
                self._scan_funcs.append(self._raw_line_end_expect)
                return
            else:
                # Ожидаемый символ совпал с текущим, он уже извлечён
                # Если список ожидаемых символов опустел, дальше распознаются
                # внутренние токены директивы.
                # Удаляем из стека поиск токена:
                self._scan_funcs.pop()
                # Добавляем сканирование директивы на внутренние токены
                self._scan_funcs.append(self._scan_pp_dirrective)
                # добавляем токен
                self._add_token(tt.OPEN_DIRECTIVE_STMT)
        else:
            # в данном случае мы имеем дело с ошибкой работы сканера.
            print(f"Err. open pp dir stmt expect: ({self._line}, {self._current}).")
                
    def _loc_name_expect(self, c:str) -> None:
        """ Распознавание имени локации """
        # имя локации - это то же самое, что и сырая строка, только с другим типом токена
        self._raw_line_end_expect(c, tt.LOC_NAME)
        # и ещё, дальше начинается распознавание тела локации
        self._scan_funcs.append(self._loc_body_expect)

    def _scan_pp_dirrective(self, c:str) -> None:
        """ Распознаём внутренние токены директивы """
        self._pp_directive += c
        if c in (" ", "\t", "\r", "\n"):
            # пробелы не учитываются
            self._curlexeme = ''
        elif c == ":":
            # токен then
            self._add_token(tt.THEN_STMT)
        elif c == "(":
            self._add_token(tt.LEFT_PAREN)
        elif c == ")":
            self._add_token(tt.RIGHT_PAREN)
        elif c == "=":
            # Либо это assignment либо начало equal
            if self._current + 1 < self._line_len:
                next_char = self._qsps_lines[self._line][self._current + 1]
                if next_char != "=":
                    # assignment
                    self._add_token(tt.ASSIGNMENT_OPERATOR)
                else:
                    self._scan_funcs.append(self._equal_expect)
            else:
                self._add_token(tt.ASSIGNMENT_OPERATOR)
        elif self._is_alnum(c):
            # если это \w, ожидается, что мы имеем дело с идентификатором
            # ключевым словом и т.п.
            self._scan_funcs.append(self._identifier_expect)
        else:
            # любой другой символ включает выборку сырого текста до конца строки
            self._scan_funcs.append(self._raw_text_expect)
        
        if self._current >= self._line_len - 1:
            # если это последний символ строки, добавляем токен конца строки
            self._add_token(tt.NEWLINE)
            # удаляем парсер директив из стека
            self._scan_funcs.pop()
        ...

    def _equal_expect(self) -> None:
        """ Получает токен оператора сравнения """
        if self._current > 0:
            prev_char = self._qsps_lines[self._line][self._current - 1]
            if prev_char == '=':
                self._add_token(tt.EQUAL_EQUAL)
            elif prev_char == '!':
                self._add_token(tt.EQUAL_NOT_EQUAL)
            self._scan_funcs.pop()
        else:
            print(f"Err. equal_expect: ({self._line}, {self._current}).")

    def _identifier_expect(self, c:str) -> None:
        """ Сборка идентификатора """
        # Если следующий символ не буква,не цифра и не символ подчёркивания, закрываем
        next_char = self._qsps_lines[self._line][self._current + 1]
        if not self._is_alnum(next_char):
            ttype:Optional[tt] = self.keywords.get(self._curlexeme, None)
            if ttype == None: ttype = tt.IDENTIFIER
            self._add_token(ttype)
            self._scan_funcs.pop()

    def _loc_body_expect(self, c:str) -> None:
        ...

    # вспомогательные методы
    def _is_alnum(self, s:str) -> bool:
        return s.isalnum() or s == '_'

    def _set_lexeme_start(self) -> None:
        """ Устанавливаем начало лексемы. """
        self._lexeme_start = (self._line, self._current)

    def _is_line_end(self) -> bool:
        """ Проверяем, не закончилась ли строка. """
        return self._current >= len(self._qsps_lines[self._line])

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
        # if self._current + 1 < len(self._qsps_lines[self])
        ...

    def _is_eof(self) -> bool:
        """ Является ли текущий символ концом файла? """
        return (
            (self._line == self._l-1 and self._current > len(self._line))
            or self._line == self._l
        )

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