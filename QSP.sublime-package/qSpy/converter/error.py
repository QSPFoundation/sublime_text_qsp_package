from base_tokens import BaseToken

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