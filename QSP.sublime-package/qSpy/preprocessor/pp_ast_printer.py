from typing import List, Dict, Union, Literal

from . import pp_tokens as tkn
from . import pp_stmts as stm

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

class AstPrinter(stm.PpVisitor[AstNode]):

    def __init__(self, stmts:List[stm.PpStmt[AstNode]]) -> None:
        self._stmts = stmts
        self._ast:List[AstNode] = []

    def gen_ast(self) -> None:
        for statement in self._stmts:
            self._ast.append(statement.accept(self))

    def get_ast(self) -> List[AstNode]:
        return self._ast

    def _token(self, t:tkn.PpToken) -> AstNode:
        return {
            'type': 'tkn',
            'sub': t.ttype.name,
            'value': t.lexeme
        }

    def visit_bracket_block(self, stmt: stm.BracketBlock[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'BracketBlock',
            'sub': stmt.left.ttype.name,
            'value': stmt.value.accept(self) if stmt.value is not None else None
        }

    def visit_other_stmt(self, stmt: stm.OtherStmt[AstNode]) -> AstNode:
        chain:List[AstNode] = []
        for el in stmt.chain:
            if isinstance(el, tkn.PpToken):
                chain.append(self._token(el))
            else:
                chain.append(el.accept(self))
        return {
            'type': 'stmt',
            'class': 'OtherStmt',
            'value': chain
        }

    def visit_string_literal(self, stmt: stm.StringLiteral[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'StringLiteral',
            'sub': stmt.left.ttype.name,
            'value': [s.accept(self) for s in stmt.value]
        }

    def visit_raw_string_line(self, stmt: stm.RawStringLine[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'RawStringLine',
            'value': [self._token(t) for t in stmt.value]
        }

    def visit_stmts_line(self, stmt: stm.StmtsLine[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'StmtsLine',
            'value': [el.accept(self) for el in stmt.stmts] + ([stmt.comment.accept(self)] if stmt.comment else [])
        }

    def visit_comment_stmt(self, stmt: stm.CommentStmt[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'CommentStmt',
            'sub': stmt.name.ttype.name,
            'value': ([self._token(stmt.pref)] if stmt.pref else [])
                     + [self._token(el) for el in stmt.value]
        }

    def visit_loc_open_dclrt(self, stmt: stm.PpQspLocOpen[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpQspLocOpen',
            'sub': stmt.name.ttype.name,
            'value': stmt.name.lexeme
        }

    def visit_loc_close_dclrt(self, stmt: stm.PpQspLocClose[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpQspLocClose',
            'sub': stmt.name.ttype.name,
            'value': stmt.name.lexeme
        }

    def visit_raw_line_dclrt(self, stmt: stm.RawLineStmt[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'RawLineStmt',
            'value': ([self._token(stmt.pref)] if stmt.pref else [])
                     + [self._token(el) for el in stmt.value]
        }

    def visit_pp_literal(self, stmt: stm.PpLiteral[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpLiteral',
            'sub': stmt.value.ttype.name,
            'value': stmt.value.lexeme
        }
    
