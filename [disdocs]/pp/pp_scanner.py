from typing import List, Dict

from pp_tokens import PpToken, PpTokenType

class PpScanner:
    """ Scanner for QspsPP. """
    def __init__(self, qsps_lines: List[str]) -> None:
        self._qsps_lines = qsps_lines
        self._qsps_len = len(self._qsps_lines)
        self._tokens: List[PpToken] = []

        self._offset = 0 # смещение относительно начала файла
        self._current = 0 # указатель на текущий символ в строке
        self._line = 0 # номер текущей строки
        self._line_len = 0 # длина текущей строки
        
        self._lexeme_start = ( # начало текущей лексемы
            self._line, # строка
            self._current # символ в строке
        )

        self._skip_mode = False

        self.keywords:Dict[str, PpTokenType] = {
            
        }

    def scan_tokens(self) -> None:
        """ Find all tokens in the file. """
        # to self._tokens
        for i, line in enumerate(self._qsps_lines):
            self._current = 0
            self._line = i
            self._line_len = len(line)
            self._scan_line(line)
            
        self._tokens.append(PpToken(PpTokenType.EOF, "", None, self._line))

    def _scan_line(self, line:str) -> None:
        """ Find all tokens in the line. """
        # to self._tokens
        for j, c in enumerate(line):
            # поскольку поглощение нового символа происходит автоматически,
            # нам нужно знать, пропускаем мы следующий символ, или парсим
            if self._skip_mode:
                # режим пропуска включён, значит просто проверяем

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
        if self._current + 1 < len(self._qsps_lines[self])

    def _is_eof(self) -> bool:
        """ Является ли текущий символ концом файла? """
        return (
            (self._line == self._l-1 and self._current > len(self._line))
            or self._line == self._l
        )