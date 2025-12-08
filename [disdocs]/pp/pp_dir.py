from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional

from pp_tokens import PpToken

R = TypeVar("R")

class PpDir(ABC, Generic[R]):
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
    def visit_endif_dir(self, stmt:'EndifDir[R]') -> R:
        ...

    @abstractmethod
    def visit_nopp_dir(self, stmt:'NoppDir[R]') -> R:
        ...

    @abstractmethod
    def visit_off_dir(self, stmt:'OffDir[R]') -> R:
        ...

    @abstractmethod
    def visit_on_dir(self, stmt:'OnDir[R]') -> R:
        ...
    
    @abstractmethod
    def visit_nosavecomm_dir(self, stmt:'NoSaveCommDir[R]') -> R:
        ...
    
    @abstractmethod
    def visit_savecomm_dir(self, stmt:'SaveCommDir[R]') -> R:
        ...

    @abstractmethod
    def visit_assignment_dir(self, stmt:'AssignmentDir[R]') -> R:
        ...

@dataclass(eq=False)
class EndifDir(PpDir[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_endif_dir(self)

@dataclass(eq=False)
class NoppDir(PpDir[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_nopp_dir(self)

@dataclass(eq=False)
class OffDir(PpDir[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_off_dir(self)

@dataclass(eq=False)
class OnDir(PpDir[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_on_dir(self)

@dataclass(eq=False)
class NoSaveCommDir(PpDir[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_nosavecomm_dir(self)

@dataclass(eq=False)
class SaveCommDir(PpDir[R]):
    name:PpToken
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_savecomm_dir(self)

@dataclass(eq=False)
class AssignmentDir(PpDir[R]):
    key:PpToken
    value:Optional[PpToken]
    def accept(self, visitor: 'PpVisitor[R]') -> R:
        return visitor.visit_assignment_dir(self)