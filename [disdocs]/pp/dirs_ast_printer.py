from typing import List, Dict, Union, Literal

import pp_tokens as tkn

import dirs_stmts as stm
import pp_expr as expr
import pp_dir as dir

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

Stmts = List[stm.DirStmt[AstNode]]

class DirsAstPrinter(stm.PpVisitor[AstNode], dir.PpVisitor[AstNode], expr.PpVisitor[AstNode]):

    def __init__(self, stmts:Stmts) -> None:
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

    def visit_qsps_line(self, stmt: stm.QspsLineStmt[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'QspsLineStmt',
            'value': ([self._token(stmt.pref)] if stmt.pref else [])
                     + [self._token(el) for el in stmt.value]
        }

    def visit_pp_directive(self, stmt: stm.DirectiveStmt[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpDirective',
            'sub': stmt.lexeme.lexeme,
            'pref': self._token(stmt.pref) if stmt.pref else None,
            'value': stmt.body.accept(self),
            'end': self._token(stmt.end)
        }

    def visit_endif_dir(self, stmt: dir.EndifDir[AstNode]) -> AstNode:
        return {
            'type': 'dir',
            'class': 'EndifDir',
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
                        v.accept(self) for v in stmt.operands
                    ] + [
                        self._token(t) for t in stmt.operators
                    ]
        }
    
