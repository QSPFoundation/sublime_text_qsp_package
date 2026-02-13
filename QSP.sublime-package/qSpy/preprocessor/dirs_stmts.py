from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, List

from .pp_tokens import PpToken
from . import pp_dir as dir

R = TypeVar("R")

class DirStmt(ABC, Generic[R]):
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
    def visit_pp_directive(self, stmt:'DirectiveStmt[R]') -> R:
        ...

    @abstractmethod
    def visit_qsps_line(self, stmt:'QspsLineStmt[R]') -> R:
        ...

@dataclass(eq=False)
class QspsLineStmt(DirStmt[R]):
    pref:Optional[PpToken]
    value:List[PpToken]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_qsps_line(self)

@dataclass
class DirectiveStmt(DirStmt[R]):
    pref:Optional[PpToken] # tt.PREFORMATTER
    lexeme:PpToken # tt.OPEN_DIRECTIVE_STMT
    body:dir.PpDir[R]
    end:PpToken # tt.NEWLINE
    def accept(self, visitor:PpVisitor[R]) -> R:
        return visitor.visit_pp_directive(self)