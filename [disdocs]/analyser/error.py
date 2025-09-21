import sys
from token_ import QspToken, QspTokenType as tt

class QspErr:
    had_error = False

    @staticmethod
    def error(line:int, message:str) -> None:
        QspErr.report(line, "", message)

    @staticmethod
    def parse_error(token:QspToken, message:str) -> None:
        if token.ttype == tt.EOF:
            QspErr.report(token.line, " at end. ", message)
        else:
            QspErr.report(token.line, f" at '{token.lexeme}'. ", message)

    @staticmethod
    def report(line:int, where:str, message:str) -> None:
        print(
            f"[line {line}] Error {where}: {message}",
            file=sys.stderr
        )
        QspErr.had_error = True

class ParseError(RuntimeError):
    ...
