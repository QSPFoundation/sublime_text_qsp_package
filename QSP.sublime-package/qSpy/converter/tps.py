from typing import Dict, List, Literal, TypedDict, Union

Path = str

Char = str
CharsStack = List[Char]

QspsChar = str
GameChar = str
CharCache = Dict[QspsChar, GameChar]

QspsLine = str

LocName = str
LocCode = List[QspsLine]

FileName = str
FileExt = str

FolderName = str

GamePassword = str
GameLine = str

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

class QspLocation(TypedDict):
    name: LocName
    desc: MultilineDesc
    actions:List[Action]
    run_to_visit:List[QspsLine]

ParseStringMode = Union[BaseFindMode, LocFindMode]