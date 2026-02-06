from typing import Dict, List, Literal, Tuple, TypedDict, Union

Path = str

Char = str
CharsStack = List[Char]

QspsChar = str
GameChar = str
CharCache = Dict[QspsChar, GameChar]

QspsLine = str

LocName = str
LocCode = List[QspsLine]

Start = int
End = int
ViewRegion = Tuple[Start, End]

FileName = str
FileExt = str

FolderName = str

GamePassword = str
GameLine = str

# location finds

class LocFindMode(TypedDict):
    loc_name: LocName
    region: ViewRegion
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