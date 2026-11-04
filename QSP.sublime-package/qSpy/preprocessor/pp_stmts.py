from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, List, Union

from .pp_tokens import PpToken

R = TypeVar("R")

class PpStmt(ABC, Generic[R]):
    """ Класс поддержки операторов препроцессинга. В т.ч. общий тип, шаблон. """
    index:int = -1
    @abstractmethod # обязательный метод для всех операторов
    def accept(self, visitor:'PpVisitor[R]') -> R:
        """ Принимает объект, реализующий набор поведений в виде методов.
        См. описание в файле ниже. """
        ...

class PpVisitor(ABC, Generic[R]):
    """ Интерфейс для всех реализаций поведения операторов препроцессинга. """
    @abstractmethod
    def visit_raw_line_dclrt(self, stmt:'RawLineStmt[R]') -> R:
        ...

    @abstractmethod
    def visit_loc_open_dclrt(self, stmt:'PpQspLocOpen[R]') -> R:
        ...

    @abstractmethod
    def visit_loc_close_dclrt(self, stmt:'PpQspLocClose[R]') -> R:
        ...

    @abstractmethod
    def visit_comment_stmt(self, stmt:'CommentStmt[R]') -> R:
        ...

    @abstractmethod
    def visit_stmts_line(self, stmt:'StmtsLine[R]') -> R:
        ...

    @abstractmethod
    def visit_other_stmt(self, stmt:'OtherStmt[R]') -> R:
        ...

    @abstractmethod
    def visit_string_literal(self, stmt:'StringLiteral[R]') -> R:
        ...

    @abstractmethod
    def visit_bracket_block(self, stmt:'BracketBlock[R]') -> R:
        ...

    @abstractmethod
    def visit_paren_block(self, stmt:'ParenBlock[R]') -> R:
        ...

    @abstractmethod
    def visit_code_block(self, stmt:'CodeBlock[R]') -> R:
        ...

    @abstractmethod
    def visit_pp_literal(self, stmt:'PpLiteral[R]') -> R:
        ...

    @abstractmethod
    def visit_raw_string_line(self, stmt:'RawStringLine[R]') -> R:
        ...

@dataclass(eq=False)
class BracketBlock(PpStmt[R]):
    left:PpToken
    value:Optional['OtherStmt[R]']
    right:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_bracket_block(self)

@dataclass(eq=False)
class ParenBlock(PpStmt[R]):
    left:PpToken
    value:Optional['OtherStmt[R]']
    right:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_paren_block(self)

@dataclass(eq=False)
class CodeBlock(PpStmt[R]):
    left:PpToken
    value:Optional['OtherStmt[R]']
    right:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_code_block(self)

@dataclass(eq=False)
class StringLiteral(PpStmt[R]):
    left:PpToken
    value:List['RawStringLine[R]']
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_string_literal(self)

@dataclass(eq=False)
class OtherStmt(PpStmt[R]):
    chain:'OtherStmtChain[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_other_stmt(self)

@dataclass(eq=False)
class StmtsLine(PpStmt[R]):
    pref:Optional[PpToken]
    stmts:List['StmtLinePart[R]']
    comment:Optional['CommentStmt[R]']
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_stmts_line(self)

@dataclass(eq=False)
class CommentStmt(PpStmt[R]):
    pref:Optional[PpToken]
    name:PpToken
    value:List[PpToken]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_comment_stmt(self)

@dataclass(eq=False)
class PpQspLocOpen(PpStmt[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_loc_open_dclrt(self)

@dataclass(eq=False)
class PpQspLocClose(PpStmt[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_loc_close_dclrt(self)

@dataclass(eq=False)
class RawLineStmt(PpStmt[R]): # Raw Line between location
    pref:Optional[PpToken]
    value:List[PpToken]
    def accept(self, visitor:PpVisitor[R]) -> R:
        return visitor.visit_raw_line_dclrt(self)

@dataclass
class RawStringLine(PpStmt[R]): # Raw Line in literal string
    value:List[PpToken]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_raw_string_line(self)

@dataclass(eq=False)
class PpLiteral(PpStmt[R]): # token wrap
    value:PpToken
    def accept(self, visitor:PpVisitor[R]) -> R:
        return visitor.visit_pp_literal(self)

OtherStmtChain = List[PpStmt[R]]
StmtLinePart = Union[OtherStmt[R], PpLiteral[R]]

# Паттерн Visitor: единый PpVisitor задаёт по методу visit_* на каждый класс
# операторов, а оператор в accept вызывает соответствующий метод посетителя —
# вместо дублирования поведения в каждом классе оператора.
