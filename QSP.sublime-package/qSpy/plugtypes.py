from typing import Dict, List, Tuple, Literal, Optional, Union

Path = str # file or folder path
FileName = str
LocName = str
QspsLine = str

BuilderArgs = Dict[
	Literal['build', 'run', 'point_file', 'qgc_path'],
	Union[bool, str]
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
		'preprocessor', 'assets', 'scans'
	],
	Union[
		str,
		bool,
		FileName,
		Path,
		List[QspModule],
		List[AssetsConfig],
		ScansConfig
	]
]