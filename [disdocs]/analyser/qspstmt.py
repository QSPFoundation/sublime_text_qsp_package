from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any

from token_ import QspToken

R = TypeVar("R")

class QspStmt(ABC, Generic[R]):
    """Класс поддержки выражений. Используется в т.ч. для указания типов."""
    @abstractmethod
    def accept(self, visitor: "Visitor[R]") -> R:
        ...

class Visitor(ABC, Generic[R]):
    """interface of visitor for Expression"""
    @abstractmethod
    def visit_ression_stmt(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_nt_stmt(self, expr:R) -> R:
        ...

@dataclass
class Expression(QspStmt[R]):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_ression_stmt(self)

@dataclass
class Print(QspStmt[R]):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_nt_stmt(self)
