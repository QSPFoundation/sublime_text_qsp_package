from typing import Any

import qspexpr
from error import ParseError, QspErr
from token_ import QspToken, QspTokenType as tt

class QspInterpreter(qspexpr.Visitor):

    def interpret(self, expr:qspexpr.QspExpr) -> None:
        try:
            value = self._evaluate(expr)
            print(value)
        except ParseError as e:
            QspErr.runtime_error(e)
    
    def visit_literal_expr(self, expr: qspexpr.QspLiteral) -> Any:
        return expr.value

    def visit_unary_expr(self, expr: qspexpr.QspUnary) -> Any:
        right = self._evaluate(expr.right)

        if expr.operator.ttype == tt.MINUS:
            self._check_number_operand(expr.operator, right)
            return -float(right)
        if expr.operator.ttype == tt.BANG:
            return not self._is_truthy(right)

        return None

    def visit_grouping_expr(self, expr: qspexpr.QspGrouping) -> Any:
        return self._evaluate(expr.expression)

    def visit_binary_expr(self, expr: qspexpr.QspBinary) -> Any:
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



    def _evaluate(self, expr:qspexpr.QspExpr) -> Any:
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

    def _check_number_operand(self, operator:QspToken, left:Any, right:Any) -> None:
        if isinstance(left, float) and isinstance(right, float): return
        raise ParseError(operator, "Operands must be numbers.")