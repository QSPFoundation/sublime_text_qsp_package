from typing import Tuple
from .base_tokens import BaseToken

Line = str
Num = int

class ParserError(SyntaxError):
    """Исключение для ошибок парсинга"""
    
    def __init__(self, token:BaseToken, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._token = token
        self._message = message
        
    def __str__(self) -> str:
        if self._token:
            name = self._token.ttype.name
            token_info = f"[{name}] '{self._token.lexeme}' at {self._token.lexeme_start}"
            return f"Base-Parser Error! {self._message}: {token_info}"
        return self._message

class RuntimeIntError(RuntimeError):
    """ Исключения для ошибок воспроизведения базового описания и действий """

    def __init__(self, line:Tuple[Line, Num], message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._line = line
        self._message = message
        
    def __str__(self) -> str:
        return f"Base-Int Error! {self._message}: [{self._line[1]}] {self._line[0]}"
