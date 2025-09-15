from ast import literal_eval
from token_type import QspTokenType

class QspToken:

    def __init__(self, type_:QspTokenType, lexeme:str, literal, line:int) -> None:
        self.ttype = type_
        self.lexeme = lexeme
        self.literal = literal
        self.line = line

    def __str__(self) -> str:
        return f"{self.ttype} {self.lexeme} {self.literal}"