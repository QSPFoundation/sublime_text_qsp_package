from typing import List, Union, Dict
import qspexpr as qe
import qspstmt as qs
from token_ import QspToken
from interpreter import QspInterpreter
from func_type import QspFunctionType
from error import QspErr

class QspResolver(qe.Visitor, qs.Visitor):

    def __init__(self, interpreter:QspInterpreter) -> None:
        self.interpreter = interpreter
        self.scopes:List[Dict[str, bool]] = []
        self.current_function = QspFunctionType.NONE

    # base methods
    def visit_block_stmt(self, stmt:qs.QspBlock) -> None:
        self._begin_scope()
        self._resolve(stmt.statements)
        self._end_scope()

    def visit_var_stmt(self, var:qs.QspVar) -> None:
        self._declare(var.name)
        if var.initializer is not None:
            self._resolve(var.initializer)
        self._define(var.name)

    def visit_variable_expr(self, expr:qe.QspVariable) -> None:
        if (self.scopes and
            self.scopes[-1].get(expr.name.lexeme, None) is False):
            QspErr.parse_error(expr.name, 
                "Can't read local variable in its own initializer.")

        self._resolve_local(expr, expr.name) 

    def visit_assign_expr(self, expr:qe.QspAssign) -> None:
        self._resolve(expr.value) 
        self._resolve_local(expr, expr.name)

    def visit_function_stmt(self, stmt:qs.QspFunction) -> None:
        self._declare(stmt.name)
        self._define(stmt.name)

        self._resolve_function(stmt)

    def visit_expression_stmt(self, stmt:qs.QspExpression) -> None:
        self._resolve(stmt.expression)

    def visit_if_stmt(self, stmt:qs.QspIf) -> None:
        self._resolve(stmt.condition)
        self._resolve(stmt.then_branch)
        if stmt.else_branch is not None:
            self._resolve(stmt.else_branch)

    def visit_print_stmt(self, stmt:qs.QspPrint) -> None:
        self._resolve(stmt.expression)

    def visit_return_stmt(self, stmt:qs.QspReturn) -> None:
        if self.current_function == QspFunctionType.NONE:
            QspErr.parse_error(stmt.keyword,
                "Can't return from top-level code.")
        if stmt.value is not None:
            self._resolve(stmt.value)

    def visit_while_stmt(self, stmt:qs.QspWhile) -> None:
        self._resolve(stmt.condition)
        self._resolve(stmt.body)

    def visit_binary_expr(self, expr:qe.QspBinary) -> None:
        self._resolve(expr.left)
        self._resolve(expr.right)

    def visit_call_expr(self, expr:qe.QspCall) -> None:
        self._resolve(expr.callee)

        for arg in expr.arguments:
            self._resolve(arg)

    def visit_grouping_expr(self, expr:qe.QspGrouping) -> None:
        self._resolve(expr.expression)

    def visit_literal_expr(self, expr:qe.QspLiteral) -> None:
        pass

    def visit_logical_expr(self, expr:qe.QspLogical) -> None:
        self._resolve(expr.left)
        self._resolve(expr.right)

    def visit_unary_expr(self, expr:qe.QspUnary) -> None:
        self._resolve(expr.right)

    # aux methods
        # public resolve method
    def resolve(self,
        statements:Union[List[qs.QspStmt], qs.QspStmt, qe.QspExpr]) -> None:
        self._resolve(statements)

    def _resolve(self,
        statements:Union[List[qs.QspStmt], qs.QspStmt, qe.QspExpr]) -> None:
        if isinstance(statements, list):
            for stmt in statements:
                self._resolve(stmt)
        elif isinstance(statements, qs.QspStmt):
            statements.accept(self)
        elif isinstance(statements, qe.QspExpr):
            statements.accept(self)

    def _begin_scope(self) -> None:
       self.scopes.append({})

    def _end_scope(self) -> None:
        self.scopes.pop()

    def _declare(self, name:QspToken) -> None:
        if not self.scopes: return

        scope = self.scopes[-1]
        if name.lexeme in scope:
            QspErr.parse_error(name,
                "Already a variable with this name in this scope.")
        scope[name.lexeme] = False

    def _define(self, name:QspToken) -> None:
        if not self.scopes: return
        self.scopes[-1][name.lexeme] = True
    
    def _resolve_local(self, expr:qe.QspExpr, name:QspToken) -> None:
        for i, scope in enumerate(self.scopes[::-1]):
            if name.lexeme in scope:
                self.interpreter.resolve(expr, i)
                return

    def _resolve_function(self,
        foo:qs.QspFunction, ftype:QspFunctionType) -> None:
        enclosing_function = self.current_function
        self.current_function = ftype
        self._begin_scope()
        for param in foo.params:
            self._declare(param)
            self._define(param)
        self._resolve(foo.body)
        self._end_scope
        self.current_function = enclosing_function