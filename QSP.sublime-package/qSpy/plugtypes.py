from typing import Dict, List, Literal, Union, TypedDict

Path = str # file or folder path
AbsPath = str # absolute path of file or folder
AppParam = str # parameters for application (ex.: --br, -u, -f)
FileName = str
FolderName = str
LocName = str
QspsLine = str
GameLine = str

HashMD5 = str
PpMode = Literal['Hard-off', 'Off', 'On']
QspMode = Literal['--br', '--build', '--run']

class SchemeArgs(TypedDict, total=False):
	point_file: Path
	platform: Literal['windows', 'linux', 'osx']
	packages_path: Path

FolderPath = Dict[Literal['path'], Path]
FilePath = Dict[Literal['path'], Path]

class QspModule(TypedDict, total=False):
	module: Path
	folders: List[FolderPath]
	files: List[FilePath]

class AssetsConfig(TypedDict, total=False):
	output:Path
	folders:List[FolderPath]
	files:List[FilePath]

class ScansConfig(TypedDict, total=False):
	location:LocName
	folders:List[Path]
	files:List[Path]

class ConverterConfig(TypedDict):
	capi: Literal['qgc', 'builtin', 'outer']
	path: Path
	args: AppParam

class JsonScheme(TypedDict, total=False):
	""" Source Project Scheme aka json-file """
	project: List[QspModule]
	start: Path
	converter: Union[Path, List[Union[Path, AppParam]]]
	player: Path
	save_temp_files: bool
	preprocessor: PpMode
	assets: List[AssetsConfig]
	scans: ScansConfig

class ProjectScheme(TypedDict):
	""" Correct Project Scheme for builder """
	project: List[QspModule]
	start: Path
	converter: ConverterConfig
	player: Path
	save_temp_files: bool
	preprocessor: PpMode
	assets: List[AssetsConfig]
	scans: ScansConfig

class QspPluginCommandMarkers(TypedDict):
	rename_path: bool
	delete_files:List[Path]
	save_log_file: bool

ViewId = int