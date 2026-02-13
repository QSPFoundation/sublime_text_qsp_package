from dataclasses import dataclass
from typing import Any
from token_type import QspTokenType

@dataclass
class QspToken:
    ttype:QspTokenType
    lexeme:str
    literal:Any
    line:int