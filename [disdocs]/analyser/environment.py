from typing import Any, Dict
from error import ParseError
import token_ as t

class QspEnvironment:
    def __init__(self):
        self.values:Dict[str, Any] = {}

    def get(self, name:t.QspToken) -> Any:
        if name.lexeme in self.values:
            print('env.get:', self.values.get(name.lexeme))
            return self.values.get(name.lexeme)

        raise ParseError(name,
            f"Undefined variable '{name.lexeme}'.")

    def define(self, name:str, value:Any) -> None:
        self.values[name] = value