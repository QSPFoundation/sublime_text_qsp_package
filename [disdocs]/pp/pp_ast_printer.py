from typing import List, Dict, Union

import pp_tokens as tkn

import pp_stmts as stm
import pp_expr as expr
import pp_dir as dir

AstNode = Dict[str, Union[str, stm.PpStmt[None]]]

class AstPrinter(stm.PpVisitor[AstNode], dir.PpVisitor[AstNode], expr.PpVisitor[AstNode]):

    def __init__(self) -> None:
        self._ast:List[AstNode] = []

    def print(self, statements:List[stm.PpStmt[None]]) -> None:
        for statement in statements:
            self._ast.append(statement.accept(self))

    def _token(self, t:tkn.PpToken) -> AstNode:
        return {
            'type': 'token',
            'sub': t.ttype.name,
            'lexeme': t.lexeme
        }

    def visit_bracket_block(self, stmt: stm.BracketBlock[AstNode]) -> AstNode:
        return {
            'type': 'statement',
            'name': 'BracketBlock',
            'sub': stmt.left.ttype.name,
            'value': stmt.value.accept(self)
        }

    def visit_other_stmt(self, stmt: stm.OtherStmt[AstNode]) -> AstNode:
        chain:List[AstNode] = []
        for el in stmt.chain:
            if isinstance(el, tkn.PpToken):
                chain.append(self._token(el))
            elif isinstance(el, stm.PpStmt[AstNode]):

        return {
            'type': 'statement',
            'name': 'OtherStmt',
            'chain': chain
        }