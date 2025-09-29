from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any, List

from token_ import QspToken

from qspexpr import QspExpr

R = TypeVar("R")

class QspStmt(ABC, Generic[R]):
    """Класс поддержки выражений. Используется в т.ч. для указания типов."""
    @abstractmethod
    def accept(self, visitor: "Visitor[R]") -> R:
        ...

class Visitor(ABC, Generic[R]):
    """interface of visitor for Expression"""
    @abstractmethod
    def visit_expression_stmt(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_if_stmt(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_print_stmt(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_var_stmt(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_while_stmt(self, expr:R) -> R:
        ...

    @abstractmethod
    def visit_block_stmt(self, expr:R) -> R:
        ...

@dataclass
class QspExpression(QspStmt[R]):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_expression_stmt(self)

@dataclass
class QspIf(QspStmt[R]):
    condition: QspExpr
    then_branch: QspStmt
    else_branch: QspStmt
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_if_stmt(self)

@dataclass
class QspPrint(QspStmt[R]):
    expression: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_print_stmt(self)

@dataclass
class QspVar(QspStmt[R]):
    name: QspToken
    initializer: QspExpr
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_var_stmt(self)

@dataclass
class QspWhile(QspStmt[R]):
    condition: QspExpr
    body: QspStmt
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_while_stmt(self)

@dataclass
class QspBlock(QspStmt[R]):
    statements: List[QspStmt]
    def accept(self, visitor: Visitor[R]) -> R:
        return visitor.visit_block_stmt(self)
