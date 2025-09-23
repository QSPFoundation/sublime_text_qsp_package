from typing import List
from token_ import QspTokenType as tt, QspToken
import qspexpr as qe
# from qspexpr import QspExpr, QspBinary, QspUnary, QspLiteral, QspGrouping
import qspstmt as qs
from error import QspErr, ParseError

class QspParser:

    def __init__(self, tokens:List[QspToken]) -> None:
        self.tokens = tokens

        self.current:int = 0

    def parse(self) -> List[qs.QspStmt]:
        statements:List[qs.QspStmt] = []
        while not self._is_at_end():
            statements.append(self.declaration())
        return statements

    def declaration(self) -> qs.QspStmt:
        try:
            if self._match(tt.VAR): return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return

    def statement(self) -> qs.QspStmt:
        if self._match(tt.PRINT): return self.print_statement()

        return self.expression_statement()

    def var_declaration(self) -> qs.QspStmt:
        name:QspToken = self._consume(tt.IDENTIFIER, "Expect variable name.")

        initializer:qe.QspExpr = None
        if self._match(tt.EQUAL):
            initializer = self.expression()

        self._consume(tt.SEMICOLON, "Expect ';' avter value.")
        return qs.QspVar(name, initializer)

    def print_statement(self) -> qs.QspStmt:
        value = self.expression()
        self._consume(tt.SEMICOLON, "Expect ';' avter value.")
        return qs.QspPrint(value)

    def expression_statement(self) -> qs.QspStmt:
        expr = self.expression()
        self._consume(tt.SEMICOLON, "Expect ';' after expression.")
        return qs.QspExpression(expr)

    def expression(self) -> qe.QspExpr:
        return self.equality()

    def equality(self) -> qe.QspExpr:
        expr = self.comparison()

        while self._match(tt.BANG_EQUAL, tt.EQUAL_EQUAL):
            operator:QspToken = self._previous()
            right:qe.QspExpr = self.comparison()
            expr = qe.QspBinary(expr, operator, right)

        return expr

    def comparison(self) -> qe.QspExpr:
        expr = self.term()

        while self._match(tt.GREATER, tt.GREATER_EQUAL, tt.LESS, tt.LESS_EQUAL):
            operator = self._previous()
            right = self.term()
            expr = qe.QspBinary(expr, operator, right)

        return expr

    def term(self) -> qe.QspExpr:
        expr = self.factor()

        while self._match(tt.MINUS, tt.PLUS):
            operator = self._previous()
            right = self.factor()
            expr = qe.QspBinary(expr, operator, right)

        return expr

    def factor(self) -> qe.QspExpr:
        expr = self.unary()

        while self._match(tt.SLASH, tt.STAR):
            operator = self._previous()
            right = self.unary()
            expr = qe.QspBinary(expr, operator, right)

        return expr

    def unary(self) -> qe.QspExpr:
        if self._match(tt.BANG, tt.MINUS):
            operator = self._previous()
            right = self.unary()
            return qe.QspUnary(operator, right)
        
        return self.primary()

    def primary(self) -> qe.QspExpr:
        if self._match(tt.FALSE): return qe.QspLiteral(False)
        if self._match(tt.TRUE): return qe.QspLiteral(True)
        if self._match(tt.NIL): return qe.QspLiteral(None)

        if self._match(tt.NUMBER, tt.STRING):
            return qe.QspLiteral(self._previous().literal)

        if self._match(tt.IDENTIFIER):
            return qe.QspVariable(self._previous())

        if self._match(tt.LEFT_PAREN):
            expr = self.expression()
            self._consume(tt.RIGHT_PAREN, "Expect ')' after expression.")
            return qe.QspGrouping(expr)

        # Специальная диагностика: бинарный оператор в начале выражения
        if self._check(tt.PLUS) or self._check(tt.STAR) or self._check(tt.SLASH) \
            or self._check(tt.EQUAL_EQUAL) or self._check(tt.BANG_EQUAL) \
            or self._check(tt.GREATER) or self._check(tt.GREATER_EQUAL) \
            or self._check(tt.LESS) or self._check(tt.LESS_EQUAL):
            tok = self._peek()
            self.error(tok, f"Ожидалось выражение, а найден бинарный оператор '{tok.lexeme}'.")

        self.error(self._peek(), "Expect expression.")

    def error(self, token:QspToken, message:str) -> ParseError:
        QspErr.parse_error(token, message)

        raise ParseError(token, message)

    def synchronize(self) -> None:
        self._advance()

        while not self._is_at_end():
            if self._previous().ttype == tt.SEMICOLON: return

            if self._peek().ttype in (
                tt.CLASS, tt.FUN, tt.VAR, tt.FOR, tt.IF,
                tt.WHILE, tt.PRINT, tt.RETURN
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
        return self._peek().ttype == tt.EOF

    def _peek(self) -> QspToken:
        return self.tokens[self.current]

    def _previous(self) -> QspToken:
        sk = self.current
        return self.tokens[sk - 1] if sk > 0 else None