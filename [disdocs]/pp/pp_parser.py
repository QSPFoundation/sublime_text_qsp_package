from typing import List, Optional

from pp_tokens import PpToken as tkn

class PpParser:

    def __init__(self, tokens:List[tkn]) -> None:
        self._tokens:List[tkn] = tokens

        self._curtok:int = 0

        self._stmts:List = [] #list of statements

    def parse(self) -> None:
        for token in self._tokens:
            ...