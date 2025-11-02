from dataclasses import dataclass
from token import NEWLINE
from typing import Any

from enum import (IntEnum, auto)

# ------------------------------ Tokens Types ------------------------------ #
class PpTokenType(IntEnum):
    # 
    NEWLINE = 0

    # One char tokens:
    STMT_DELIMITER = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    APOSTROPHE = auto()
    QUOTE = auto()

    # string escape tokens:
    OPEN_QUOTE = auto()
    CLOSE_QUOTE = auto()
    RAW_QS_LINE = auto()
    
    OPEN_APOSTROPHE = auto()
    CLOSE_APOSTROPHE = auto()
    RAW_AS_LINE = auto()

    # QSP-location tokens:
    LOC_DEF_KWRD = auto()
    LOC_END_KWRD = auto()

    # Comments tokens:
    COMMENT_KWRD = auto()
    SIMPLE_SPEC_COMM = auto()
    LESS_SPEC_COMM = auto()
    SIMPLE_COMM = auto()

    # PreProcessors Directives tokens:
    OPEN_DIRECTIVE_STMT = auto()
    IF_STMT = auto()
    THEN_STMT = auto()
    VAR_STMT = auto()

    ON_STMT = auto()
    OFF_STMT = auto()
    SAVECOMM_STMT = auto()
    NO_SAVECOMM_STMT = auto()
    NOPP_STMT = auto()
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

    LOC_NAME = auto()
    RAW_LINE = auto()

    EOF = auto()

# ---------------------------- Token Class ------------------------------ #
@dataclass
class PpToken:
    ttype:PpTokenType
    lexeme:str # вся лексема целиком
    literal:Any # только значение
    line:int # строка, в которой токен находится