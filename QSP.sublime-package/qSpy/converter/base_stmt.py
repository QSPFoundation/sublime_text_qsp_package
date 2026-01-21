from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, List

from base_tokens import BaseToken

R = TypeVar("R")

class BaseStmt(ABC, Generic[R]):
    """ Класс поддержки операторов базового описания и базовых действий. """
    index:int = -1
    @abstractmethod # обязательный метод для всех операторов
    def accept(self, visitor:'PpVisitor[R]') -> R:
        """ Принимает объект, реализующий набор поведений в виде методов. """
        ...

class PpVisitor(ABC, Generic[R]):
    """ Интерфейс для всех реализаций поведения операторов препроцессинга. """

    @abstractmethod
    def visit_print_text_stmt(self, stmt:'PrintTextStmt[R]') -> R:
        ...

    @abstractmethod
    def visit_expression(self, stmt:'Expression[R]') -> R:
        ...

    @abstractmethod
    def visit_expression_stmt(self, stmt:'ExpressionStmt[R]') -> R:
        ...

    @abstractmethod
    def visit_literal(self, stmt:'Literal[R]') -> R:
        ...

    @abstractmethod
    def visit_parens(self, stmt:'Parens[R]') -> R:
        ...

    @abstractmethod
    def visit_brackets(self, stmt:'Brackets[R]') -> R:
        ...

    @abstractmethod
    def visit_braces(self, stmt:'Braces[R]') -> R:
        ...

    @abstractmethod
    def visit_action(self, stmt:'Action[R]') -> R:
        ...
    
    @abstractmethod
    def visit_comment(self, stmt:'Comment[R]') -> R:
        ...

    @abstractmethod
    def visit_condition(self, stmt:'Condition[R]') -> R:
        ...

    @abstractmethod
    def visit_loop(self, stmt:'Loop[R]') -> R:
        ...

    @abstractmethod
    def visit_unknown(self, stmt:'Unknown[R]') -> R:
        ...

    @abstractmethod
    def visit_end(self, stmt:'End[R]') -> R:
        ...



@dataclass(eq=False)
class Expression(BaseStmt[R]):
    chain:List[BaseStmt[R]]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_expression(self)

@dataclass(eq=False)
class ExpressionStmt(BaseStmt[R]):
    pref:Optional[BaseToken]
    expression:Expression[R]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_expression_stmt(self)

@dataclass(eq=False)
class PrintTextStmt(BaseStmt[R]):
    pref:Optional[BaseToken]
    stmt:BaseToken
    expression:Optional['Expression[R]']
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_print_text_stmt(self)

@dataclass(eq=False)
class Literal(BaseStmt[R]):
    value:BaseToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_literal(self)

@dataclass(eq=False)
class Parens(BaseStmt[R]):
    left:BaseToken
    content:Expression[R]
    right:BaseToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_parens(self)

@dataclass(eq=False)
class Brackets(BaseStmt[R]):
    left:BaseToken
    content:Expression[R]
    right:BaseToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_brackets(self)

@dataclass(eq=False)
class Braces(BaseStmt[R]):
    left:BaseToken
    content:List[BaseStmt[R]]
    right:BaseToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_braces(self)

@dataclass(eq=False)
class Action(BaseStmt[R]):
    pref:Optional[BaseToken]
    open:BaseToken
    name:Expression[R]
    image:Optional[Expression[R]]
    content:List[BaseStmt[R]]
    close:'End[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_action(self)

@dataclass(eq=False)
class Condition(BaseStmt[R]):
    pref:Optional[BaseToken]
    open:BaseToken # if
    condition:Expression[R]
    content:List[BaseStmt[R]]
    close:'End[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_condition(self)

@dataclass(eq=False)
class Loop(BaseStmt[R]):
    pref:Optional[BaseToken]
    open:BaseToken # loop
    defines:List[BaseStmt[R]]
    while_stmt:BaseToken # while
    condition:Expression[R]
    step_stmt:Optional[BaseToken]
    steps:List[BaseStmt[R]]
    content:List[BaseStmt[R]]
    close:'End[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_loop(self)

@dataclass(eq=False)
class Comment(BaseStmt[R]):
    pref:Optional[BaseToken]
    open:BaseToken
    chain:List[BaseStmt[R]]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_comment(self)

@dataclass(eq=False)
class Unknown(BaseStmt[R]):
    pref:Optional[BaseToken]
    open:BaseToken
    args:List[Expression[R]]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_unknown(self)

@dataclass(eq=False)
class End(BaseStmt[R]):
    pref:Optional[BaseToken]
    name:BaseToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_end(self)