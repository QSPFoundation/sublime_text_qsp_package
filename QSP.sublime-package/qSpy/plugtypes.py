from typing import Dict, List, Tuple, Literal, Optional, Union

Path = str # file or folder path
AppParam = str # parameters for application (ex.: --br, -u, -f)
FileName = str
FolderName = str
LocName = str
QspsLine = str
PpMode = Literal['Hard-off', 'Off', 'On']

SchemeArgs = Dict[
	Literal[
		'point_file', # Path
		'platform', # Literal['windows', 'unix']
		'packages_path' # Path
	],
	Union[Path, str]
]

FolderPath = Dict[Literal['path'], Path]
FilePath = Dict[Literal['path'], Path]
QspModule = Dict[
	Literal['module', 'folders', 'files'],
	Union[FileName, List[FolderPath], List[FilePath]]
]
AssetsConfig = Dict[
	Literal['output', 'folders', 'files'],
	Union[Path, List[FolderPath], List[FilePath]]
]
ScansConfig = Dict[
	Literal['location', 'folders', 'files'],
	Union[LocName, List[Path]]
]
ProjectScheme = Dict[
	Literal[
		'project', 'start', 'converter', 'player', 'save_temp_files',
		'preprocessor', 'assets', 'scans',
		'qgc'
	],
	Union[
		str,
		bool,
		FileName,
		Path,
		List[QspModule],
		List[AssetsConfig],
		ScansConfig,
		List[Union[Path, AppParam]]
	]
]