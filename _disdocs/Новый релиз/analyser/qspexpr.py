from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any, List

from token_ import QspToken

R = TypeVar("R")

class QspExpr(ABC, Generic[R]):
    """Класс поддержки выражений. Используется в т.ч. для указания типов."""
    @abstractmethod
    def accept(self, visitor: "Visitor[R]") -> R:
        ...

class Visitor(ABC, Generic[R]):
    """interface of visitor for Expression"""
    @abstractmethod
    def visit_assign_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_binary_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_call_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_grouping_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_literal_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_logical_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_unary_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_variable_expr(self, expr:R) -> R:
        ...

@dataclass(eq=False)
class QspAssign(QspExpr[R]):
    name: QspToken
    value: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_assign_expr(self)

@dataclass(eq=False)
class QspBinary(QspExpr[R]):
    left: QspExpr
    operator: QspToken
    right: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_binary_expr(self)

@dataclass(eq=False)
class QspCall(QspExpr[R]):
    callee: QspExpr
    paren: QspToken
    arguments: List[QspExpr]
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_call_expr(self)

@dataclass(eq=False)
class QspGrouping(QspExpr[R]):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_grouping_expr(self)

@dataclass(eq=False)
class QspLiteral(QspExpr[R]):
    value: Any
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_literal_expr(self)

@dataclass(eq=False)
class QspLogical(QspExpr[R]):
    left: QspExpr
    operator: QspToken
    right: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_logical_expr(self)

@dataclass(eq=False)
class QspUnary(QspExpr[R]):
    operator: QspToken
    right: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_unary_expr(self)

@dataclass(eq=False)
class QspVariable(QspExpr[R]):
    name: QspToken
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_variable_expr(self)
