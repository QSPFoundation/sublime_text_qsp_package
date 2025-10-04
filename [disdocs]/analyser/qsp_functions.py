# from abc import ABC, abstractmethod
from typing import Any, List, TYPE_CHECKING
from qsp_callable import QspCallable
from qspstmt import QspFunction
from environment import QspEnvironment
from error import ReturnErr

if TYPE_CHECKING:
    from interpreter import QspInterpreter

class QspCallableFunction(QspCallable):
    def __init__(self, declaration:QspFunction) -> None:
        self.declaration = declaration

    def call(self, interpreter: 'QspInterpreter', arguments: List[Any]) -> Any:
        environment = QspEnvironment(interpreter.globals)
        for i, param in enumerate(self.declaration.params):
            environment.define(param.lexeme, arguments[i])
        try:
            interpreter._execute_block(self.declaration.body, environment)
        except ReturnErr as e:
            return e.value

    def arity(self) -> int:
        return len(self.declaration.params)

    def __str__(self) -> str:
        return f"<fn {self.declaration.name.lexeme}>"

