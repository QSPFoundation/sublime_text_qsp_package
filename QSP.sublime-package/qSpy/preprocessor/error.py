from .pp_tokens import PpToken

Line = str
Num = int

_MAIL = 'Mail me error text to lex666endless@gmail.com'


# --------------------------- Ошибки логики стадии (Run) --------------------------- #
class _RunError(RuntimeError):
    """База для ошибок в логике стадии (алгоритм сломан, а не разбираемый код).

    Наследники различаются только `label` — текстовым префиксом в `__str__`.
    """
    label: str = ''

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self._message = message

    def __str__(self) -> str:
        return f'{self.label} error: {self._message}. {_MAIL}'


class DirScannerRunError(_RunError):
    """ Исключение для ошибок в логике сканера директив. """
    label = 'PP.DirsScanner'


class DirsParserRunError(_RunError):
    """ Исключение для ошибок в логике парсера директив. """
    label = 'PP.DirsParser'


class DirsInterpreterError(_RunError):
    """ Исключение для ошибок при выполнении команд препроцессора. """
    label = 'PP.DirsInt'


class PpScannerRunError(_RunError):
    """ Исключение для ошибок в логике сканера кода. """
    label = 'PP.CodeScanner'


class PpParserRunError(_RunError):
    """ Исключение для ошибок в логике парсера кода. """
    label = 'PP.CodeParser'


class PpInterpreterError(_RunError):
    """ Исключение для ошибок при выполнении кода препроцессора. """
    label = 'PP.CodeInt'


# --------------------------- Ошибки разбираемого кода (Syntax) --------------------------- #
class DirScannerError(SyntaxError):
    """ Исключение для ошибок сканнера директив. Директива сломана. """

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self._message = message

    def __str__(self) -> str:
        return f'PP.DirsScanner. Error in directive: {self._message}. Prove game-file.'


class DirsParserError(SyntaxError):
    """ Исключение для ошибок парсера директив. Директива сломана. """

    def __init__(self, token: PpToken, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self._token = token
        self._message = message

    def __str__(self) -> str:
        return f'PP.DirsParser. Error in directive: {self._message}, get {self._token.ttype.name} {self._token.lexeme_start}. Prove game-file.'


class PpScannerError(SyntaxError):
    """ Исключение для ошибок сканнера. Сломан токен. """

    def __init__(self, line: int, char: int, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self._message = message
        self._char = (line, char)

    def __str__(self) -> str:
        return f'PP.CodeScanner. {self._message} {self._char}. Prove game-file.'


class PpParserError(SyntaxError):
    """ Исключение для ошибок парсера кода. Код сломан. """

    def __init__(self, token: PpToken, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self._token = token
        self._message = message

    def __str__(self) -> str:
        return f'PP.CodeParser. Error in the game-code: {self._message}, get {self._token.ttype.name} {self._token.lexeme_start}. Prove game-file.'
