from dataclasses import dataclass
from typing import Tuple

from enum import (IntEnum, auto)

LineNum = int
CharNum = int
Point = Tuple[LineNum, CharNum]

# ------------------------------ Tokens Types ------------------------------ #
class BaseTokenType(IntEnum):
    # 
    NEWLINE = 0

    # preformatting spaces
    PREFORMATTER = auto()

    # One char tokens:
    AMPERSAND = auto()

    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()

    RIGHT_BRACE = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()

    APOSTROPHE_STRING = auto()
    QUOTE_STRING = auto()

    # Comments tokens:
    EXCLAMATION_SIGN = auto()

    # STMT KEYWORDS
    THEN = auto()
    ACT_STMT = auto()
    END_STMT = auto()
    IF_STMT = auto()
    STAR_P_STMT = auto()
    STAR_PL_STMT = auto()
    STAR_NL_STMT = auto()
    LOOP_STMT = auto()
    WHILE_STMT = auto()
    STEP_STMT = auto()

    IDENTIFIER = auto()
    
    DELIMITER = auto()
    COMMA = auto()

    # Raw Lines:
    RAW_TEXT = auto()

    # PreProcessors Directives tokens:

    # EOF:
    EOF = auto()

# ---------------------------- Token Class ------------------------------ #
@dataclass
class BaseToken:
    ttype:BaseTokenType
    lexeme:str # вся лексема целиком
    lexeme_start:Point # строка и номер символа в которой токен находится

    def get_end_pos(self) -> Point:
        """ line_num, char_num after last"""
        line, char = self.lexeme_start
        return (line, char + len(self.lexeme))
