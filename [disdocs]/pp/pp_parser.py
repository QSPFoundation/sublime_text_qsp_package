from typing import List, Callable

from pp_tokens import PpToken as tkn
from pp_tokens import PpTokenType as tt

Stack = List[Callable[(tkn), None]]

class PpParser:

    def __init__(self, tokens:List[tkn]) -> None:
        self._tokens:List[tkn] = tokens

        self._curtok:int = 0

        self._parse_funcs:Stack = [self._qsps_file_parse]

        self._stmts:List = [] #list of statements

    def parse(self) -> None:
        """ Публичная функция вызова парсера. """
        for j, token in enumerate(self._tokens):
            self._curtok = j
            self._parse_funcs[-1](token)

    def _qsps_file_parse(self, t:tkn) -> None:
        ...