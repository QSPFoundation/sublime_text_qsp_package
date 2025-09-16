from typing import Any
from token_type import QspTokenType

class QspToken:

    def __init__(self, ttype:QspTokenType, lexeme:str, literal:Any, line:int) -> None:
        self.ttype = ttype
        self.lexeme = lexeme
        self.literal = literal
        self.line = line

    def __str__(self) -> str:
        return f"token: type = {self.ttype} lexeme = '{self.lexeme}' literal = '{self.literal}'"