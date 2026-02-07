"""
    Реализация выржений препроцессора.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Union, List

from .pp_tokens import PpToken

R = TypeVar("R")

class PpExpr(ABC, Generic[R]):
    """ Класс поддержки выражений препроцессинга. В т.ч. общий тип, шаблон. """
    index:int = -1
    @abstractmethod # обязательный метод для всех операторов
    def accept(self, visitor:'PpVisitor[R]') -> R:
        """ Принимает объект, реализующий набор поведений в виде методов.
        См. описание в файле ниже. """
        ...

class PpVisitor(ABC, Generic[R]):
    """ Интерфейс для всех реализаций поведения операторов препроцессинга. """
    @abstractmethod
    def visit_or_expr(self, stmt:'OrExpr[R]') -> R:
        ...

    @abstractmethod
    def visit_and_expr(self, stmt:'AndExpr[R]') -> R:
        ...

    @abstractmethod
    def visit_var_name(self, stmt:'VarName[R]') -> R:
        ...

    @abstractmethod
    def visit_equal_expr(self, stmt:'EqualExpr[R]') -> R:
        ...

    @abstractmethod
    def visit_not_expr(self, stmt:'NotExpr[R]') -> R:
        ...

@dataclass(eq=False)
class OrExpr(PpExpr[R]):
    left_oprnd:'OrType[R]'
    right_oprnd:PpExpr[R]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_or_expr(self)

@dataclass(eq=False)
class AndExpr(PpExpr[R]):
    left_oprnd:'AndType[R]'
    right_oprnd:'NotType[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_and_expr(self)

@dataclass(eq=False)
class NotExpr(PpExpr[R]):
    left:'EqualType[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_not_expr(self)

@dataclass(eq=False)
class EqualExpr(PpExpr[R]):
    operands:List['VarName[R]']
    operators:List[PpToken]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_equal_expr(self)

@dataclass(eq=False)
class VarName(PpExpr[R]):
    value:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_var_name(self)

EqualType = Union[VarName[R], EqualExpr[R]]
NotType = Union[EqualType[R], NotExpr[R]]
AndType = Union[NotType[R], AndExpr[R]]
OrType = Union[AndType[R], OrExpr[R]]