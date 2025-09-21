from ast import Expression
import operator
from typing import List
from token_ import QspTokenType as tt, QspToken
from qspexpr import QspExpr, QspBinary, QspUnary, QspLiteral, QspGrouping
from error import QspErr, ParseError

class QspParser:

    def __init__(self, tokens:List[QspToken]) -> None:
        self.tokens = tokens

        self.current:int = 0

    def parse(self) -> QspExpr:
        try:
            return self.expression()
        except ParseError:
            return None

    def expression(self) -> QspExpr:
        return self.equality()

    def equality(self) -> QspExpr:
        expr = self.comparison()

        while self._match(tt.BANG_EQUAL, tt.EQUAL_EQUAL):
            operator:QspToken = self._previous()
            right:QspExpr = self.comparison()
            expr = QspBinary(expr, operator, right)

        return expr

    def comparison(self) -> QspExpr:
        expr = self.term()

        while self._match(tt.GREATER, tt.GREATER_EQUAL, tt.LESS, tt.LESS_EQUAL):
            operator = self._previous()
            right = self.term()
            expr = QspBinary(expr, operator, right)

        return expr

    def term(self) -> QspExpr:
        expr = self.factor()

        while self._match(tt.MINUS, tt.PLUS):
            operator = self._previous()
            right = self.factor()
            expr = QspBinary(expr, operator, right)

        return expr

    def factor(self) -> QspExpr:
        expr = self.unary()

        while self._match(tt.SLASH, tt.STAR):
            operator = self._previous()
            right = self.unary()
            expr = QspBinary(expr, operator, right)

        return expr

    def unary(self) -> QspExpr:
        if self._match(tt.BANG, tt.MINUS):
            operator = self._previous()
            right = self.unary()
            return QspUnary(operator, right)
        
        return self.primary()

    def primary(self) -> QspExpr:
        if self._match(tt.FALSE): return QspLiteral(False)
        if self._match(tt.TRUE): return QspLiteral(True)
        if self._match(tt.NIL): return QspLiteral(None)

        if self._match(tt.NUMBER, tt.STRING):
            return QspLiteral(self._previous().literal)

        if self._match(tt.LEFT_PAREN):
            expr = self.expression()
            self._consume(tt.RIGHT_PAREN, "Expect ')' after expression.")
            return QspGrouping(expr)

        self.error(self._peek(), "Expect expression.")

    def error(self, token:QspToken, message:str) -> ParseError:
        QspErr.parse_error(token, message)

        return ParseError()

    def synchronize(self) -> None:
        self._advance()

        while not self._is_at_end():
            if self._previous().ttype == tt.SEMICOLON: return

            if self._peek().ttype in (
                tt.CLASS, tt.FUN, tt.VAR, tt.FOR, tt.IF,
                tt.WHILE, tt.PRINT, tt. RETURN
            ): return

            self._advance()

    def _consume(self, ttype:tt, message:str) -> QspToken:
        if self._check(ttype): return self._advance()

        self.error(self._peek(), message)


    def _match(self, *ttypes:tt) -> bool:
        for ttype in ttypes:
            if self._check(ttype):
                self._advance()
                return True

        return False

    def _check(self, ttype:tt) -> bool:
        if self._is_at_end(): return False
        return self._peek().ttype == ttype

    def _advance(self) -> QspToken:
        if not self._is_at_end(): self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek() == tt.EOF

    def _peek(self) -> QspToken:
        return self.tokens[self.current]

    def _previous(self) -> QspToken:
        sk = self.current
        return self.tokens[sk - 1] if sk > 0 else None