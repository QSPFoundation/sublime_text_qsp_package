import sys

from typing import (List, Literal, Tuple, Dict, Match, Optional, Callable)

class QspToken:
    ...

class QspScanner:
    ...

    def scan_tokens(self) -> List[QspToken]:
        """Получить список токенов из QSP-кода."""

class QspInt:
    """ Сканирует QSP-код. Я так думаю, но посмотрим. """
    def __init__(self, args:list[str]) -> None:
        self.scanner = None
        self.had_error = False

        if len(args) > 1:
            print("Usage: QSP [script]")
            sys.exit(64)
        elif len(args) == 1:
            self.run_file(args[0])
        else:
            self.run_prompt()

    def run_file(self, path: str) -> None:
        """Заглушка: выполнить скрипт из файла по пути `path`."""
        with open(path, 'r', encoding='utf-8') as fp:
            string = fp.read()
        self.run(string)
        if self.had_error: sys.exit(65)


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
        self.scanner = QspScanner(source)
        tokens:List[QspToken] = self.scanner.scan_tokens()
        for token in tokens:
            print(token)

    def error(self, line:int, message:str) -> None:
        self.report(line, "", message)

    def report(self, line:int, where:str, message:str) -> None:
        print(
            "[line " + line + "] Error" + where + ": " + message,
            file=sys.stderr
        )
        self.had_error = True




def main() -> None:
    interpretator = QspInt(sys.argv[1:])

if __name__ == "__main__":
    main()


