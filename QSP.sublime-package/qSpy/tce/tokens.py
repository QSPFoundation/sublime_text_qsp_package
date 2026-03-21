from dataclasses import dataclass
from typing import Tuple, Dict, Union, List

from enum import (IntEnum, auto)

LineNum = int
CharNum = int
Point = Tuple[LineNum, CharNum]

TokenNode = Dict[str, Union[str, List[int], bool]]

# ------------------------------ Tokens Types ------------------------------ #
class TextTokenType(IntEnum):
    #
    NEWLINE = 0

    RAW_LINE = auto()

    LOC_OPEN = auto()
    LOC_CLOSE = auto()

    TEXT_QUOTE_CONST = auto()
    TEXT_APOSTROPHE_CONST = auto()

    # EOF:
    EOF = auto()

# ---------------------------- Token Class ------------------------------ #
@dataclass
class TextToken:
    ttype:TextTokenType
    lexeme:str # вся лексема целиком
    lexeme_start:Point # строка и номер символа в которой токен находится
    def get_as_node(self) -> TokenNode:
        return {
            "token-type": self.ttype.name,  # название константы вместо номера
            'lexeme': self.lexeme,
            'lexeme_start': list(self.lexeme_start),
        }

    def get_end_pos(self) -> Point:
        line, char = self.lexeme_start
        return (line, char + len(self.lexeme))
