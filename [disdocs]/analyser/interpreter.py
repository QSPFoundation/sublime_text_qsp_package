import sys
from typing import Any, List

import qspexpr
import qspstmt
from error import ParseError, QspErr
from token_ import QspToken, QspTokenType as tt
from environment import QspEnvironment

class QspInterpreter(qspexpr.Visitor, qspstmt.Visitor):

    def __init__(self) -> None:
        self.environment = QspEnvironment()
        self.line_count = 0 # по этой метке пока что отслеживаем, можем ли мы неявно вызывать принт
                            # на выражениях, но это решение неверное.

    def interpret(self, statements:List[qspstmt.QspStmt]) -> None:
        self.line_count = len(statements)
        try:
            for stmt in statements:
                self._execute(stmt)
        except ParseError as e:
            QspErr.runtime_error(e)
    
    def visit_literal_expr(self, expr: qspexpr.QspLiteral) -> Any:
        return expr.value

    def visit_logical_expr(self, expr: qspexpr.QspLogical) -> Any:
        left = self._evaluate(expr.left)

        if (expr.operator.ttype == tt.OR):
            if self._is_truthy(left): return left
        else:
            if not self._is_truthy(left): return left

        return self._evaluate(expr.right)

    def visit_unary_expr(self, expr: qspexpr.QspUnary) -> Any:
        right = self._evaluate(expr.right)

        if expr.operator.ttype == tt.MINUS:
            self._check_number_operand(expr.operator, right)
            return -float(right)
        if expr.operator.ttype == tt.BANG:
            return not self._is_truthy(right)

        return None

    def visit_variable_expr(self, expr: qspexpr.QspVariable) -> Any:
        # print('visit_variable_expr', expr, expr.name)
        return self.environment.get(expr.name)

    def visit_grouping_expr(self, expr: qspexpr.QspGrouping) -> Any:
        return self._evaluate(expr.expression)

    def visit_binary_expr(self, expr: qspexpr.QspBinary) -> Any:
        # print('visit_binary_expr', str(expr.left), expr.right)
        left = self._evaluate(expr.left)
        right = self._evaluate(expr.right)

        if expr.operator.ttype == tt.BANG_EQUAL:
            return not self._is_equal(left, right)
        if expr.operator.ttype == tt.EQUAL_EQUAL:
            return self._is_equal(left, right)
        if expr.operator.ttype == tt.GREATER:
            return float(left) > float(right)
        if expr.operator.ttype == tt.LESS:
            return float(left) < float(right)
        if expr.operator.ttype == tt.GREATER_EQUAL:
            return float(left) >= float(right)
        if expr.operator.ttype == tt.LESS_EQUAL:
            return float(left) <= float(right)
        if expr.operator.ttype == tt.MINUS:
            return float(left) - float(right)
        if expr.operator.ttype == tt.SLASH:
            return float(left) / float(right)
        if expr.operator.ttype == tt.STAR:
            return float(left) * float(right)
        if expr.operator.ttype == tt.PLUS:
            if isinstance(left, float) and isinstance(right, float):
                return float(left) + float(right)
            if isinstance(left, str) and isinstance(right, str):
                return str(left) + str(right)
        # недостижимо!
        return None

    def visit_expression_stmt(self, expr:qspstmt.QspExpression) -> None:
        # expr is stmt
        value = self._evaluate(expr.expression)
        # in QSP is as print_line
        if self.line_count == 1: print(str(value))

    def visit_print_stmt(self, expr:qspstmt.QspPrint) -> None:
        value = self._evaluate(expr.expression)
        print(str(value))

    def visit_var_stmt(self, stmt:qspstmt.QspVar) -> None:
        value = None
        if stmt.initializer != None:
            value = self._evaluate(stmt.initializer)
        # print('visit_var_stmt.value:', value)
        self.environment.define(stmt.name.lexeme, value)

    def visit_assign_expr(self, expr: qspexpr.QspAssign) -> Any:
        value = self._evaluate(expr.value)
        self.environment.assign(expr.name, value)

    def visit_block_stmt(self, stmt: qspstmt.QspBlock) -> None:
        self._execute_block(stmt.statements,
                            QspEnvironment(self.environment))

    def visit_if_stmt(self, stmt: qspstmt.QspIf) -> None:
        if self._is_truthy(self._evaluate(stmt.condition)):
            self._execute(stmt.then_branch)
        elif not stmt.else_branch is None:
            self._execute(stmt.else_branch)

    def visit_while_stmt(self, stmt:qspstmt.QspWhile) -> None:
        while self._is_truthy(self._evaluate(stmt.condition)):
            self._execute(stmt.body)

    def _evaluate(self, expr:qspexpr.QspExpr) -> Any:
        # print('evaluate', expr)
        return expr.accept(self)

    def _is_truthy(self, object:Any) -> bool:
        if object is None: return False
        if isinstance(object, bool): return bool(object)
        return True

    def _is_equal(self, a:Any, b:Any) -> bool:
        if a is None and b is None: return True
        if a is None: return False

        return a == b

    def _check_number_operand(self, operator:QspToken, operand:Any) -> None:
        if isinstance(operand, float): return
        raise ParseError(operator, "Operand must be a number.")

    def _check_number_operands(self, operator:QspToken, left:Any, right:Any) -> None:
        if isinstance(left, float) and isinstance(right, float): return
        raise ParseError(operator, "Operands must be numbers.")

    def _execute(self, stmt:qspstmt.QspStmt) -> None:
        # print('_execute', stmt)
        stmt.accept(self)

    def _execute_block(self, statements:List[qspstmt.QspStmt],
                        environment:QspEnvironment) -> None:
        previous = self.environment
        try:
            self.environment = environment
            for statement in statements:
                self._execute(statement)
        finally:
            self.environment = previous
