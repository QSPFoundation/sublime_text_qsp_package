from typing import Any, Dict, Optional
from error import ParseError
import token_ as t

class QspEnvironment:
    def __init__(self, enclosing:'QspEnvironment'=None):
        self.values:Dict[str, Any] = {}
        self.enclosing:Optional['QspEnvironment'] = enclosing

    def get(self, name:t.QspToken) -> Any:
        if name.lexeme in self.values:
            # print('env.get:', self.values.get(name.lexeme))
            return self.values.get(name.lexeme)

        if self.enclosing != None:
            return self.enclosing.get(name)

        raise ParseError(name,
            f"Undefined variable '{name.lexeme}'.")

    def get_at(self, distance:int, name:str) -> Any:
        return self.ancestor(distance).values.get(name)

    def ancestor(self, distance:int) -> 'QspEnvironment':
        environment = self
        for i in range(distance):
            environment = environment.enclosing

        return environment

    def define(self, name:str, value:Any) -> None:
        self.values[name] = value

    def assign(self, name:t.QspToken, value:Any) -> None:
        if name.lexeme in self.values:
            self.values[name.lexeme] = value
            return

        if self.enclosing != None:
            self.enclosing.assign(name, value)
            return

        raise ParseError(name,
            f"Undefined variable '{name.lexeme}'.")

    def assign_at(self, distance:int, name:t.QspToken, value:Any) -> None:
        self.ancestor(distance).values[name.lexeme] = value