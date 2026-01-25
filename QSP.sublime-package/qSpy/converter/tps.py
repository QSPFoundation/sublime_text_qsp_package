from typing import List, Literal, TypedDict, Union

Path = str

Char = str
CharsStack = List[Char]
QspsLine = str

LocName = str
LocCode = List[QspsLine]

# location finds

class LocFindMode(TypedDict):
    loc_name: LocName
    quote: List[Literal['"', "'", "{"]]
    src_lines: List[QspsLine]

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

ParseStringMode = Union[BaseFindMode, LocFindMode]