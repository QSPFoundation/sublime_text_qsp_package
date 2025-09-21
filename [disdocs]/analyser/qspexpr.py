from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Generic, TypeVar, Any

R = TypeVar("R")

class QspExpr(ABC, Generic[R]):
    """Класс поддержки выражений. Используется в т.ч. для указания типов."""
    @abstractmethod
    def accept(self, visitor: "Visitor[R]") -> R:
        ...

class Visitor(Protocol[R]):
    """interface of visitor for Expression"""
    def visit_binary_expr(self, expr:R) -> R:
        ...

    def visit_grouping_expr(self, expr:R) -> R:
        ...

    def visit_literal_expr(self, expr:R) -> R:
        ...

    def visit_unary_expr(self, expr:R) -> R:
        ...


@dataclass
class QspBinary(QspExpr):
    left: QspExpr
    operator: QspToken
    right: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_binary_expr(self)


@dataclass
class QspGrouping(QspExpr):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_grouping_expr(self)


@dataclass
class QspLiteral(QspExpr):
    value: Any
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_literal_expr(self)


@dataclass
class QspUnary(QspExpr):
    operator: QspToken
    right: QspToken
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_unary_expr(self)
