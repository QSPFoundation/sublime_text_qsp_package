from typing import List, Any, Dict, Optional
from token_ import QspToken
from token_type import QspTokenType
from error import QspErr

class QspScanner:

    def __init__(self, source:str) -> None:
        self.source = source
        self.tokens:List[QspToken] = []

        self._start = 0 # первый символ рассматриваемой лексемы
        self._current = 0 # текущий рассматриваемый символ
        self._line = 1 # номер строки текущего символа

        self.keywords:Dict[str, QspTokenType] = {
            "and": QspTokenType.AND,
            "class": QspTokenType.CLASS,
            "else": QspTokenType.ELSE,
            "false": QspTokenType.FALSE,
            "for": QspTokenType.FOR,
            "fun": QspTokenType.FUN,
            "if": QspTokenType.IF,
            "nil": QspTokenType.NIL,
            "or": QspTokenType.OR,
            "print": QspTokenType.PRINT,
            "return": QspTokenType.RETURN,
            "super": QspTokenType.SUPER,
            "this": QspTokenType.THIS,
            "true": QspTokenType.TRUE,
            "var": QspTokenType.VAR,
            "while": QspTokenType.WHILE
        }

    def scan_tokens(self) -> List[QspToken]:
        """Ищем все токены в файле(строке)"""
        while not self.is_at_end():
            self._start = self._current
            self.scan_token()

        # добавляем токен конца файла
        self.tokens.append(QspToken(QspTokenType.EOF, "", None, self._line))
        return self.tokens

    def scan_token(self) -> None:
        c = self.advance()
        if c == '(':
            self.add_token(QspTokenType.LEFT_PAREN)
        elif c == ')':
            self.add_token(QspTokenType.RIGHT_PAREN,)
        elif c == '{':
            self.add_token(QspTokenType.LEFT_BRACE,)
        elif c == '}':
            self.add_token(QspTokenType.RIGHT_BRACE,)
        elif c == ',':
            self.add_token(QspTokenType.COMMA,)
        elif c == '.':
            self.add_token(QspTokenType.DOT,)
        elif c == '-':
            self.add_token(QspTokenType.MINUS,)
        elif c == '+':
            self.add_token(QspTokenType.PLUS,)
        elif c == ';':
            self.add_token(QspTokenType.SEMICOLON,)
        elif c == '*':
            self.add_token(QspTokenType.STAR )
        elif c == '!':
            self.add_token(QspTokenType.BANG_EQUAL if self.match('=') else QspTokenType.BANG)
        elif c == '=':
            self.add_token(QspTokenType.EQUAL_EQUAL if self.match('=') else QspTokenType.EQUAL)
        elif c == '<':
            self.add_token(QspTokenType.LESS_EQUAL if self.match('=') else QspTokenType.LESS)
        elif c == '>':
            self.add_token(QspTokenType.GREATER_EQUAL if self.match('=') else QspTokenType.GREATER)
        elif c == '/':
            if (self.match('/')):
                while self.peek() != '\n' and not self.is_at_end():
                    self.advance()
            else:
                self.add_token(QspTokenType.SLASH)
        elif c in (' ', '\r', '\t'):
            pass
        elif c == '\n':
            self._line += 1
        elif c == '"':
            self.string()
        elif c.isdigit():
            self.number()
        elif c.isalpha():
            self.identifier()
        else:
            QspErr.error(self._line, "Unexpected character")

    @staticmethod
    def is_al_num(s:str) -> bool:
        return s.isalnum() or s == '_'

    def is_at_end(self) -> bool:
        return (self._current >= len(self.source))

    def advance(self) -> str: # one char
        c = self.source[self._current]
        self._current += 1
        return c

    def match(self, expected:str) -> bool:
        if self.is_at_end(): return False
        if self.source[self._current] != expected: return False

        self._current += 1
        return True

    def peek(self) -> str:
        """Возвращает текущий символ последовательности. """
        if self.is_at_end(): return '\0'
        return self.source[self._current]

    def peek_next(self) -> str:
        if self._current + 1 >= len(self.source): return '\0'
        return self.source[self._current + 1]

    def string(self) -> None:
        while self.peek() != '"' and not self.is_at_end():
            if self.peek() == '\n': self._line += 1
            self.advance()

        if self.is_at_end():
            QspErr.error(self._line, "Unterminated string")
            return

        # закрываем
        self.advance()

        # обрезаем кавычки и вносим значение в токен
        value = self.source[self._start+1: self._current-1]
        self.add_token(QspTokenType.STRING, value)

    def number(self) -> None:
        while self.peek().isdigit(): self.advance()

        if self.peek() == '.' and self.peek_next().isdigit():
            self.advance()
            while self.peek().isdigit(): self.advance()

        self.add_token(QspTokenType.NUMBER,
            float(self.source[self._start: self._current])
        )

    def identifier(self) -> None:
        while QspScanner.is_al_num(self.peek()): self.advance()

        text:str = self.source[self._start: self._current]
        ttype:Optional[QspTokenType] = self.keywords.get(text, None)
        if ttype == None: ttype = QspTokenType.IDENTIFIER
        self.add_token(ttype)


    def add_token(self, ttype:QspTokenType, literal:Any = None) -> None:
        text = self.source[self._start: self._current]
        self.tokens.append(QspToken(ttype, text, literal, self._line))