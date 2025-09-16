import sys

class QspErr:
    had_error = False

    @staticmethod
    def error(line:int, message:str) -> None:
        QspErr.report(line, "", message)

    @staticmethod
    def report(line:int, where:str, message:str) -> None:
        print(
            f"[line {line}] Error {where}: {message}",
            file=sys.stderr
        )
        QspErr.had_error = True
