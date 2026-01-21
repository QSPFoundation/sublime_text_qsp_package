from typing import List, Dict, Union, Literal

import base_tokens as tkn

import base_stmt as stm

AstNode = Dict[
    # key
    Literal[
        'type', # type of node /stmt, tkn, expr, dir/
        'class', # class of node /ex. BracketBlock/
        'sub', # subclass of node /ex. token type of open bracket/
        'value', # value / lexeme of token, chain of stmt and other /
        'pref', # preformatting token,
        'end', # newline token
    ],

    # value
    Union[
        str,
        List[int],
        'AstNode',
        List['AstNode'],
        None
    ]]

Stmts = List[stm.BaseStmt[AstNode]]

class BasePrinter(stm.BaseVisitor[AstNode]):

    def __init__(self, stmts:Stmts) -> None:
        self._stmts = stmts
        self._ast:List[AstNode] = []

    def gen_ast(self) -> None:
        for statement in self._stmts:
            self._ast.append(statement.accept(self))

    def get_ast(self) -> List[AstNode]:
        return self._ast

    def _token(self, t:tkn.BaseToken) -> AstNode:
        return {
            'type': 'tkn',
            'sub': t.ttype.name,
            'value': t.lexeme
        }

    def visit_expression(self, stmt: stm.Expression[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': stmt.__class__.__name__,
            'value': [s.accept(self) for s in stmt.chain]
        }

    def visit_print_text_stmt(self, stmt: stm.PrintTextStmt[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': stmt.__class__.__name__,
            'sub': stmt.stmt.lexeme,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'value': stmt.expression.accept(self) if stmt.expression else None,
        }

    def visit_literal(self, stmt: stm.Literal[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'value': stmt.value.lexeme
        }

    def visit_parens(self, stmt: stm.Parens[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'sub': [self._token(stmt.left), self._token(stmt.right)],
            'value': stmt.content.accept(self) if stmt.content else None
        }

    def visit_brackets(self, stmt: stm.Brackets[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'sub': [self._token(stmt.left), self._token(stmt.right)],
            'value': stmt.content.accept(self) if stmt.content else None
        }

    def visit_braces(self, stmt: stm.Braces[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'sub': [self._token(stmt.left), self._token(stmt.right)],
            'value': [s.accept(self) for s in stmt.content]
        }

    def visit_action(self, stmt: stm.Action[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'sub': [
                self._token(stmt.open),
                stmt.name.accept(self),
                stmt.image.accept(self) if stmt.image else {},
            ],
            'value': [s.accept(self) for s in stmt.content],
            'end': stmt.close.accept(self)
        }
        
    def visit_condition(self, stmt: stm.Condition[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'sub': [
                self._token(stmt.open),
                stmt.condition.accept(self),
            ],
            'value': [s.accept(self) for s in stmt.content],
            'end': stmt.close.accept(self)
        }

    def visit_loop(self, stmt: stm.Loop[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'sub': [self._token(stmt.open)
            ] + [s.accept(self) for s in stmt.defines] + [self._token(stmt.while_stmt),
            stmt.condition.accept(self)] + ([self._token(stmt.step_stmt)] if stmt.step_stmt else []) +
            [s.accept(self) for s in stmt.steps],
            'value': [s.accept(self) for s in stmt.content],
            'end': stmt.close.accept(self)
        }
        
    def visit_comment(self, stmt: stm.Comment[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'sub': self._token(stmt.open),
            'value': [s.accept(self) for s in stmt.chain]
        }
        
    def visit_unknown(self, stmt: stm.Unknown[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'sub': self._token(stmt.open),
            'value': [e.accept(self) for e in stmt.args]
        }

    def visit_expression_stmt(self, stmt: stm.ExpressionStmt[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'value': stmt.expression.accept(self)
        }

    def visit_end(self, stmt: stm.End[AstNode]) -> AstNode:
        return {
            'type': 'stm',
            'class': stmt.__class__.__name__,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'value': stmt.name.lexeme
        }