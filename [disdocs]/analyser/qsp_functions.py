# from abc import ABC, abstractmethod
from typing import Any, List
from qsp_callable import QspCallable
from qspstmt import QspFunction
from interpreter import QspInterpreter
from environment import QspEnvironment

class QspCallableFunction(QspCallable):
    def __init__(self, declaration:QspFunction) -> None:
        self.declaration = declaration

    def call(self, interpreter: QspInterpreter, arguments: List[Any]) -> Any:
        environment = QspEnvironment(interpreter.globals)
        for i, param in enumerate(self.declaration.params):
            environment.define(param.lexeme, arguments[i])

        interpreter._execute_block(self.declaration.body, environment)

    def arity(self) -> int:
        return len(self.declaration.params)

    def __str__(self) -> str:
        return f"<fn {self.declaration.name.lexeme}>"

