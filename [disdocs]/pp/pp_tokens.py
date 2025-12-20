from dataclasses import dataclass
from typing import Tuple, Dict, Union, List

from enum import (IntEnum, auto)

# ------------------------------ Tokens Types ------------------------------ #
class PpTokenType(IntEnum):
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
    APOSTROPHE = auto()
    QUOTE = auto()

    # QSP-location tokens:
    LOC_OPEN = auto()
    LOC_CLOSE = auto()

    # Comments tokens:
    SIMPLE_SPEC_COMM = auto()
    LESS_SPEC_COMM = auto()
    EXCLAMATION_SIGN = auto()

    # PreProcessors Directives tokens:
    OPEN_DIRECTIVE_STMT = auto()
    IF_STMT = auto()
    THEN_STMT = auto()
    VAR_STMT = auto()

    ON_STMT = auto()
    OFF_STMT = auto()
    SAVECOMM_STMT = auto()
    NO_SAVECOMM_STMT = auto()
    # NOPP_STMT = auto()
    INCLUDE_STMT = auto()
    EXCLUDE_STMT = auto()
    ENDIF_STMT = auto()

    ASSIGNMENT_OPERATOR = auto()
    EQUAL_EQUAL = auto()
    EQUAL_NOT_EQUAL = auto()
    AND_OPERATOR = auto()
    OR_OPERATOR = auto()
    NOT_OPERATOR = auto()

    IDENTIFIER = auto() # любая переменная или её значение

    RAW_LINE = auto()
    RAW_LOC_LINE = auto()

    EOF = auto()

# ---------------------------- Token Class ------------------------------ #
@dataclass
class PpToken:
    ttype:PpTokenType
    lexeme:str # вся лексема целиком
    lexeme_start:Tuple[int, int] # строка и номер символа в которой токен находится

    def get_as_node(self) -> Dict[str, Union[str, List[int]]]:
        return {
            "token-type": self.ttype.name,  # название константы вместо номера
            'lexeme': self.lexeme,
            'lexeme_start': list(self.lexeme_start)
        }