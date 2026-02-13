from .pp_tokens import PpToken

Line = str
Num = int

class DirScannerError(SyntaxError):
    """ Исключение для ошибок сканнера директив. Директива сломана. """
    
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.DirsScanner. Error in directive: {self._message}. Prove game-file.'

class DirScannerRunError(RuntimeError):
    """ Исключение для ошибок в логике сканера директив. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.DirsScanner error: {self._message}. Mail me error text to lex666endless@gmail.com'

class DirsParserError(SyntaxError):
    """ Исключение для ошибок парсера директив. Директива сломана. """
    
    def __init__(self, token:PpToken, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._token = token
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.DirsParser. Error in directive: {self._message}, get {self._token.ttype.name} {self._token.lexeme_start}. Prove game-file.'

class DirsParserRunError(RuntimeError):
    """ Исключение для ошибок в логике парсера директив. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.DirsParser error: {self._message}. Mail me error text to lex666endless@gmail.com'

class DirsInterpreterError(RuntimeError):
    """ Исключение для ошибок при выполнении команд препроцессора. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.DirsInt error: {self._message}. Mail me error text to lex666endless@gmail.com'


class PpScannerError(SyntaxError):
    """ Исключение для ошибок сканнера. Сломан токен. """
    
    def __init__(self, line:int, char:int, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        self._char = (line, char)
        
    def __str__(self) -> str:
        return f'PP.CodeScanner. {self._message} {self._char}. Prove game-file.'

class PpScannerRunError(RuntimeError):
    """ Исключение для ошибок в логике сканера директив. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.CodeScanner error: {self._message}. Mail me error text to lex666endless@gmail.com'

class PpParserError(SyntaxError):
    """ Исключение для ошибок парсера директив. Директива сломана. """
    
    def __init__(self, token:PpToken, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._token = token
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.CodeParser. Error in the game-code: {self._message}, get {self._token.ttype.name} {self._token.lexeme_start}. Prove game-file.'

class PpParserRunError(RuntimeError):
    """ Исключение для ошибок в логике парсера директив. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.CodeParser error: {self._message}. Mail me error text to lex666endless@gmail.com'

class PpInterpreterError(RuntimeError):
    """ Исключение для ошибок при выполнении команд препроцессора. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        
    def __str__(self) -> str:
        return f'PP.CodeInt error: {self._message}. Mail me error text to lex666endless@gmail.com'

