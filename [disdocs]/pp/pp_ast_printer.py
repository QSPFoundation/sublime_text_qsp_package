from typing import List, Dict, Union, Literal

import pp_tokens as tkn

import pp_stmts as stm
import pp_expr as expr
import pp_dir as dir

AstNode = Dict[
    # key
    Literal[
        'type', # type of node /stmt, tkn, expr, dir/
        'class', # class of node /ex. BracketBlock/
        'sub', # subclass of node /ex. token type of open bracket/
        'value', # value / lexeme of token, chain of stmt and other /
    ],

    # value
    Union[
        str,
        List[int],
        'AstNode',
        List['AstNode'],
        None
    ]]

class AstPrinter(stm.PpVisitor[AstNode], dir.PpVisitor[AstNode], expr.PpVisitor[AstNode]):

    def __init__(self, stmts:List[stm.PpStmt[AstNode]]) -> None:
        self._stmts = stmts
        self._ast:List[AstNode] = []

    def get_ast(self, ) -> List[AstNode]:
        for statement in self._stmts:
            self._ast.append(statement.accept(self))
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
            'value': [el.accept(self) for el in stmt.value]
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
            'value': [el.accept(self) for el in stmt.value]
        }

    def visit_pp_directive(self, stmt: stm.PpDirective[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpDirective',
            'value': stmt.body.accept(self)
        }

    def visit_pp_literal(self, stmt: stm.PpLiteral[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpLiteral',
            'sub': stmt.value.ttype.name,
            'value': stmt.value.lexeme
        }

    def visit_endif_dir(self, stmt: dir.EndifDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'EndifDir',
            'value': stmt.name.lexeme
        }

    def visit_nopp_dir(self, stmt: dir.NoppDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'NoppDir',
            'value': stmt.name.lexeme
        }

    def visit_off_dir(self, stmt: dir.OffDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'OffDir',
            'value': stmt.name.lexeme
        }

    def visit_on_dir(self, stmt: dir.OnDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'OnDir',
            'value': stmt.name.lexeme
        }

    def visit_nosavecomm_dir(self, stmt: dir.NoSaveCommDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'NoSaveCommDir',
            'value': stmt.name.lexeme
        }

    def visit_savecomm_dir(self, stmt: dir.SaveCommDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'SaveCommDir',
            'value': stmt.name.lexeme
        }
        
    def visit_assignment_dir(self, stmt: dir.AssignmentDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'AssignmentDir',
            'value': [self._token(stmt.key)] + ([self._token(stmt.value)] if stmt.value else [])
        }

    def visit_condition_dir(self, stmt: dir.ConditionDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'ConditionDir',
            'value': [stmt.condition.accept(self)] + [el.accept(self) for el in stmt.next_dirs]
        }
        
    def visit_include_dir(self, stmt: dir.IncludeDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'IncludeDir',
            'value': stmt.name.lexeme
        }
        
    def visit_exclude_dir(self, stmt: dir.ExcludeDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'ExcludeDir',
            'value': stmt.name.lexeme
        }
        
    def visit_cond_expr_stmt(self, stmt: dir.CondExprStmt[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'CondExprStmt',
            'value': stmt.expr.accept(self)
        }

    def visit_or_expr(self, stmt: expr.OrExpr[AstNode]) -> AstNode:
        return {
            'type': 'expr',
            'class': 'OrExpr',
            'value': [stmt.left_oprnd.accept(self)] + [stmt.right_oprnd.accept(self)]
        }
        
    def visit_and_expr(self, stmt: expr.AndExpr[AstNode]) -> AstNode:
        return {
            'type': 'expr',
            'class': 'AndExpr',
            'value': [stmt.left_oprnd.accept(self)] + [stmt.right_oprnd.accept(self)]
        }

    def visit_not_expr(self, stmt: expr.NotExpr[AstNode]) -> AstNode:
        return {
            'type': 'expr',
            'class': 'NotExpr',
            'value': stmt.left.accept(self)
        }
        
    def visit_var_name(self, stmt: expr.VarName[AstNode]) -> AstNode:
        return {
            'type': 'expr',
            'class': 'VarName',
            'value': stmt.value.lexeme
        }
    
    def visit_equal_expr(self, stmt: expr.EqualExpr[AstNode]) -> AstNode:
        return {
            'type': 'expr',
            'class': 'EqualExpr',
            'value': [
                        stmt.left.accept(self),
                        self._token(stmt.operator),
                        stmt.right.accept(self)
                    ]
        }
    
