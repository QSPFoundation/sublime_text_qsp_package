from abc import ABC, abstractmethod
from typing import Any, List
from interpreter import QspInterpreter

class QspCallable(ABC):
    @abstractmethod
    def arity(self) -> int:
        ...

    @abstractmethod
    def call(self, interpreter: QspInterpreter, arguments: List[Any]) -> Any:
        ...
