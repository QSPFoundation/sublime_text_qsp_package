import sys

from typing import (List, Literal, Tuple, Dict, Match, Optional, Callable)
from token_ import QspToken
from error import QspErr, ParseError
from scanner import QspScanner
from parser import QspParser
# from ast_printer import AstPrinter
from interpreter import QspInterpreter

class QspInt:
    """ Сканирует QSP-код. Я так думаю, но посмотрим. """
    def __init__(self, args:list[str]) -> None:
        self.scanner = None
        self.interpreter = QspInterpreter()

        if len(args) > 1:
            print("Usage: QSP [script]")
            sys.exit(64)
        elif len(args) == 1:
            self.run_file(args[0])
        else:
            self.run_prompt()

    def run_file(self, path: str) -> None:
        """выполнить скрипт из файла по пути `path`."""
        with open(path, 'r', encoding='utf-8') as fp:
            string = fp.read()
        self.run(string)
        if QspErr.had_error: sys.exit(65)
        if QspErr.had_runtime_error: sys.exit(70)


    def run_prompt(self) -> None:
        """
            Запустить интерактивный режим (REPL).
            Если у вас уже есть REPL в вашем окружении,
            это будет REPL внутри REPL
        """
        while True:
            try:
                line = input("> ")
            except EOFError:
                break
            if line is None or line == 'quit':
                break
            self.run(line)

    def run(self, source: str) -> None:
        """Обработать исходный текст `source` (лексинг/парсинг/исполнение)."""
        QspErr.had_error = False
        QspErr.had_runtime_error = False
        self.scanner = QspScanner(source)
        tokens:List[QspToken] = self.scanner.scan_tokens()
       
        parser = QspParser(tokens)
        try:
            statements = parser.parse()
        except ParseError:
            return

        if QspErr.had_error: return
        # print(AstPrinter().print(expr))
        self.interpreter.interpret(statements)

def main() -> None:
    # interpretator = QspInt(sys.argv[1:])
    interpretator = QspInt(['lox.lox'])

if __name__ == "__main__":
    main()
