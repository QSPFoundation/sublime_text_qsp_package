from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any, List

from pp_tokens import PpToken

R = TypeVar("R")

class PpStmt(ABC, Generic[R]):
    """ Класс поддержки операторов препроцессинга. В т.ч. общий тип, шаблон. """
    index:int = -1
    @abstractmethod # обязательный метод для всех операторов
    def accept(self, runner:'PpVisitor[R]') -> R:
        """ Принимает объект, реализующий набор поведений в виде методов.
        См. описание в файле ниже. """
        ...

class PpVisitor(ABC, Generic[R]):
    """ Интерфейс для всех реализаций поведения операторов препроцессинга. """
    def visit_raw_line_stmt(self, stmt:PpStmt) -> R:
        ...

@dataclass(eq=False)
class RawLineStmt(PpStmt[R]):
    value:PpToken
    index:int = -1
    def accept(self, visitor:PpVisitor[R]) -> R:
        return visitor.visit_raw_line_stmt(self)

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