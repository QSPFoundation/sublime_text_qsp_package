from typing import List, Literal, TypedDict

Path = str

Char = str
CharsStack = List[Char]
QspsLine = str

LocName = str
LocCode = List[QspsLine]

# base description
MultilineDesc = str

class BaseFindMode(TypedDict):
    open_base: bool
    quote: List[Literal['"', "'", "{"]]

# base action
ActionName = str
class Action(TypedDict):
    image: Path
    name: ActionName
    code: List[QspsLine]