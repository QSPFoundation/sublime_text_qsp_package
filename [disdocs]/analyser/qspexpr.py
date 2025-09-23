from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any

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
    def visit_binary_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_grouping_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_literal_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_unary_expr(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_variable_expr(self, expr:R) -> R:
        ...

@dataclass
class QspBinary(QspExpr[R]):
    left: QspExpr
    operator: QspToken
    right: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_binary_expr(self)

@dataclass
class QspGrouping(QspExpr[R]):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_grouping_expr(self)

@dataclass
class QspLiteral(QspExpr[R]):
    value: Any
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_literal_expr(self)

@dataclass
class QspUnary(QspExpr[R]):
    operator: QspToken
    right: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_unary_expr(self)

@dataclass
class QspVariable(QspExpr[R]):
    name: QspToken
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_variable_expr(self)
