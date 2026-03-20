from .tokens import TextToken

Line = str
Num = int

class TceScannerError(SyntaxError):
    """ Исключение для ошибок сканнера. Сломан токен. """

    def __init__(self, line:int, char:int, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message
        self._char = (line, char)

    def __str__(self) -> str:
        return f'Tce.CodeScanner. {self._message} {self._char}. Prove game-file.'

class TceScannerRunError(RuntimeError):
    """ Исключение для ошибок в логике сканера директив. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message

    def __str__(self) -> str:
        return f'Tce.CodeScanner error: {self._message}. Mail me error text to lex666endless@gmail.com'

class TceParserError(SyntaxError):
    """ Исключение для ошибок парсера директив. Директива сломана. """

    def __init__(self, token:TextToken, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._token = token
        self._message = message

    def __str__(self) -> str:
        return f'Tce.CodeParser. Error in the game-code: {self._message}, get {self._token.ttype.name} {self._token.lexeme_start}. Prove game-file.'

class TceParserRunError(RuntimeError):
    """ Исключение для ошибок в логике парсера директив. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message

    def __str__(self) -> str:
        return f'Tce.CodeParser error: {self._message}. Mail me error text to lex666endless@gmail.com'

class TceInterpreterError(RuntimeError):
    """ Исключение для ошибок при выполнении команд препроцессора. """
    def __init__(self, message: str, *args:object) -> None:
        super().__init__(message, *args)
        self._message = message

    def __str__(self) -> str:
        return f'Tce.CodeInt error: {self._message}. Mail me error text to lex666endless@gmail.com'

