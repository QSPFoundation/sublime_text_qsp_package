from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, List, Union

from pp_tokens import PpToken
import pp_dir as dir

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
    def visit_pp_directive(self, stmt:'PpDirective[R]') -> R:
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
class StringLiteral(PpStmt[R]):
    left:PpToken
    value:List['StringLine[R]']
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_string_literal(self)

@dataclass(eq=False)
class OtherStmt(PpStmt[R]):
    chain:'OtherStmtChain[R]'
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_other_stmt(self)

@dataclass(eq=False)
class StmtsLine(PpStmt[R]):
    stmts:List[OtherStmt[R]]
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
class PpDirective(PpStmt[R]):
    pref:Optional[PpToken]
    lexeme:PpToken
    body:dir.PpDir[R]
    end:PpToken # tt.NEWLINE
    def accept(self, visitor:PpVisitor[R]) -> R:
        return visitor.visit_pp_directive(self)

@dataclass
class RawStringLine(PpStmt[R]):
    value:List[PpToken]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_raw_string_line(self)

@dataclass(eq=False)
class PpLiteral(PpStmt[R]):
    value:PpToken
    def accept(self, visitor:PpVisitor[R]) -> R:
        return visitor.visit_pp_literal(self)

OtherStmtChain = List[PpStmt[R]]
StringLine = Union[RawStringLine[R], PpDirective[R]]

# Допустим у нас есть объекты класса Животное. От этого класса наследуются:
# - Собака
# - Кошка
# - Акула
# Нам для каждого класса нужно реализовать поведение. Например, все животные
# Должны уметь говорить. Мы можем реализовать это через написание метода say
# для каждого класса, но это не рациионально. Если таких классов и таких
# методов будет очень много, мы очень быстро запутаемся. Куда как проще реализовать
# отдельный класс, в котором писать по методу на каждый из существующих классов
# животных. А уже в самих классах животных нам достаточно вызывать стандартный
# метод accept, который принимает как раз объект класса Поведение, и вызывает
# соответствующий метод этого класса.
# Собака:
#   def accept(behaviour:Behaviour):
#       behaviour.dog_run(self)
# Кошка:
#   def accept(behaviour):
#       behaviour.cat_run(self)
# Акула:
#   def accept(behaviour):
#       behaviour.shark_run(self)
# 
# Behaviour:
#   def dog_run(self, animal:Животное):
#       ...
#   def cat_run(self, animal:Животное):
#       ...
#   def shark_run(self, animal:Животное):
#       ...