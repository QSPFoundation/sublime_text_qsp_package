from abc import ABC, abstractmethod
from typing import Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from interpreter import QspInterpreter

class QspCallable(ABC):
    @abstractmethod
    def arity(self) -> int:
        ...

    @abstractmethod
    def call(self, interpreter: 'QspInterpreter', arguments: List[Any]) -> Any:
        ...
