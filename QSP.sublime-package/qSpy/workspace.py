import sublime			# type: ignore

import os
import json
from typing import (Dict, NamedTuple, Optional, Set, TypedDict, Union, List, Tuple, cast)
import hashlib

from .converter import QspsFile
from . import function as qsp
from . import const as const
from .plugtypes import (AbsPath, LocName, Path, ViewId, HashMD5)
from .converter import ViewRegion

WorkspacesRegistry = Dict[int, 'QspWorkspace'] # RAM-реестр: window.id() -> WS (R1, шаг 4.B)
LocPlace = Union[Path, ViewId]

class LocRecord(NamedTuple):
	""" Одна локация в индексе WS (4.2). NamedTuple, чтобы запись нельзя было
		разъехать по полям и чтобы прежний кортежный API (распаковка, [0]/[1]/[2]) жил. """
	name: LocName
	region: ViewRegion
	place: LocPlace

LocHash = LocRecord # алиас для потребителей (QSP.py); раньше это был Tuple тех же трёх полей

class QspsFilesMb(TypedDict):
	pathes:List[AbsPath]
	hashes:List[HashMD5]

class WsJson(TypedDict):
	locations: Dict[
		Path, List[Tuple[AbsPath, ViewRegion]]
	]
	files_paths: Dict[Path, HashMD5]

class QspWorkspace:
	def __init__(self, all_workspaces:WorkspacesRegistry,
		identity:Optional[str]=None, scope:Optional[List[Path]]=None) -> None:
		# Идентичность и область (R1/R2; шаг 4.B): заполняются accessor-ом for_window, которым
		# создаётся WS; при несовпадении identity окна accessor пересобирает запись (Д11).
		self._identity:Optional[str] = identity # дисковый ключ: identity_of(window) или None
		self._scope:List[Path] = list(scope or []) # все папки окна на момент постройки (R2)
		self.reset() # индекс пустой; identity/scope уже заданы выше

	@property
	def identity(self) -> Optional[str]:
		""" Дисковый ключ идентичности окна, которому принадлежит WS (R1); None без .sublime-project. """
		return self._identity

	@property
	def scope(self) -> List[Path]:
		""" Все папки окна на момент постройки WS (R2). На закрытии область берётся отсюда,
			а не из window.folders(): к моменту закрытия оно уже могло сузиться (Д9). """
		return list(self._scope)

	def reset(self) -> None:
		""" Сброс индекса (4.3). identity, scope, ссылка на реестр и флаги режима не трогаются.
			Регионы переменных в WS не хранятся (2.4, 4.5): сканируются on-demand функцией scan_vars. """
		self._locs:List[LocRecord] = []
		self._qsps_files:QspsFilesMb = {
			'pathes': [],	# all files in project (abs pathes)
			'hashes': []	# md5
		}

# --------------------------------- qsp-locations mb functions ---------------------------------

	def add_loc(self, name:LocName, region:ViewRegion, place:LocPlace) -> None:
		""" Add new qsp-location to workspace """
		rec = LocRecord(name, region, place)
		if rec not in self._locs:
			self._locs.append(rec)

	def replace_locs(self, old_path:str, new_path:str) -> None:
		""" Change place of qsp-locations. """
		if old_path == new_path: return None
		self._locs = [
			loc._replace(place=new_path) if loc.place == old_path else loc
			for loc in self._locs
		]

	def del_loc_by_index(self, i:int) -> None:
		""" Delete the qsp-location from workspace by index"""
		if i < 0 or i > len(self._locs)-1: return None
		del self._locs[i]

	def del_all_locs_by_place(self, loc_place:LocPlace) -> None:
		""" del all locations by place. loc_place - path at file with qsp_location """
		self._locs = [loc for loc in self._locs if loc.place != loc_place]

	def get_locs(self) -> List[LocRecord]:
		return list(self._locs)

	def get_locs_names(self) -> List[LocName]:
		"""	Extract all qsp-location's names. """
		return [loc.name for loc in self._locs]

	def refresh_qsplocs(self, view:sublime.View, current_qsps:Optional[Path]) -> None:
		"""	Refresh list of QSP-locations created on this view """
		qsps_path = (view.id() if not current_qsps else current_qsps) # abs_path
		self.del_all_locs_by_place(qsps_path)
		for s in view.symbol_regions():
			if s.name.startswith('Локация: '): # TODO: привязка к тому, что символ начинается с Локация не очень удобна!
				self.add_loc(s.name[9:], (s.region.begin(), s.region.end()), qsps_path)

	def clear_old_qsplocs(self, views:List[sublime.View]) -> None:
		""" Delete locations from WS, if this views don't exist. """
		view_ids = [v.id() for v in views]
		self._locs = [
			loc for loc in self._locs
			if not (isinstance(loc.place, int) and loc.place not in view_ids)
		]

	def locs_dupl(self) -> List[LocRecord]:
		""" Имена локаций, встречающиеся более одного раза (4.6). Плоский список записей
			по группам дубликатов, порядок групп — по первому появлению имени. """
		groups:Dict[LocName, List[LocRecord]] = {}
		for loc in self._locs:
			groups.setdefault(loc.name, []).append(loc)
		return [loc for recs in groups.values() if len(recs) >= 2 for loc in recs]

# --------------------------------- qsp-locations mb functions ---------------------------------

# ----------------------------------- qsps-files mb functions -----------------------------------

	def get_qsps_files(self) -> List[Tuple[AbsPath, HashMD5]]: # list of tuples!
		"""
			Return list of qsps-files from WS:
			list[tuples(path_of_file:str, hash_of_file:str)]
		"""
		# all pathes in list of pathes are abs. Dont need use absing func.
		return list(zip(self._qsps_files['pathes'], self._qsps_files['hashes']))

	def add_qsps_file(self, qsps_file_path:str, qsps_file_hash:str) -> None:
		""" Add qsps-file to WS """
		self._qsps_files['pathes'].append(qsps_file_path)
		self._qsps_files['hashes'].append(qsps_file_hash)

	def del_qsps_file(self, path:str) -> None:
		if path in self._qsps_files['pathes']:
			i = self._qsps_files['pathes'].index(path)
			del self._qsps_files['pathes'][i]
			del self._qsps_files['hashes'][i]

	def replace_qsps_file(self, old_path:str, new_path:str) -> None:
		""" When replace the phisically file, or rename it,
		this func replace old file by new in WS. """
		if old_path in self._qsps_files['pathes']:
			i = self._qsps_files['pathes'].index(old_path)
			self._qsps_files['pathes'][i] = new_path

	def _reparse_locs(self, file_path:AbsPath) -> None:
		""" (Re)read qsp-locations of an existing qsps-file into the locs mb. """
		self.del_all_locs_by_place(file_path)
		qsps_file = QspsFile()
		qsps_file.read_from_file(file_path)
		qsps_file.split_to_locations()
		for loc_name, loc_region in qsps_file.get_loc_symbols():
			# str, tuple(start, end)
			self.add_loc(loc_name, loc_region, file_path)

	def refresh_qsps_files(self, window_folders:List[AbsPath]) -> None:
		"""
			Refresh files microbase in ws. File identity is the path, content identity
			is the md5 hash - they are compared separately so that a rename is detected
			only when the path actually changed and the content hash was kept.
		"""
		old:Dict[AbsPath, HashMD5] = dict(self.get_qsps_files()) # {abs_path: hash}
		new:Dict[AbsPath, HashMD5] = {}
		for folder in window_folders:
			for f in qsp.get_files_list(folder):
				new[f] = self.get_hash(f)

		modified = [path for path in set(old) & set(new) if old[path] != new[path]]
		removed_paths:Set[AbsPath] = set(old) - set(new) # deletion / rename source
		added_paths:Set[AbsPath] = set(new) - set(old)   # new file / rename target

		# index disappearing files by their content hash to detect renames
		removed_by_hash:Dict[HashMD5, List[AbsPath]] = {}
		for path in removed_paths:
			removed_by_hash.setdefault(old[path], []).append(path)

		renamed_sources:Set[AbsPath] = set()
		for path in added_paths:
			md5 = new[path]
			candidates = removed_by_hash.get(md5)
			if candidates:
				# content moved from old path to a new path -> rename, keep locations
				old_path = candidates.pop()
				renamed_sources.add(old_path)
				self.replace_locs(old_path, path)
				self.replace_qsps_file(old_path, path)
			else:
				# brand-new file -> parse its locations
				self._reparse_locs(path)
				self.add_qsps_file(path, md5)

		for path in modified:
			# existing file, content changed -> re-derive its locations and refresh hash
			self._reparse_locs(path)
			self.refresh_md5(path)

		for path in removed_paths:
			# files that disappeared and were not consumed by a rename -> deleted
			if path in renamed_sources: continue
			self.del_all_locs_by_place(path)
			self.del_qsps_file(path)

	def refresh_md5(self, qsps_file_path:str) -> None:
		""" Refreshing md5 of file by path """
		if qsps_file_path in self._qsps_files['pathes']:
			i = self._qsps_files['pathes'].index(qsps_file_path)
			self._qsps_files['hashes'][i] = self.get_hash(qsps_file_path)

	def qsps_file_is_exist(self, qsps_file_path:str) -> bool:
		""" Prove qsps-file is exist in WS """
		return qsps_file_path in self._qsps_files['pathes']

	def qsps_files_number(self) -> int:
		"""
			Return number of qsps-files in WS.
		"""
		return len(self._qsps_files['pathes'])

# ----------------------------------- qsps-files mb functions -----------------------------------

# ---------------------------------------- WS functions ----------------------------------------

	def extract_from_file(self, ws_file_path:str) -> None:
		"""
			Extract data from file to WS. ws_file_path - is abspath to ws-json file.
			WARNING!!! All proves of project folder and exist of
			ws-file must be done prev call this function!
			Broken or structurally wrong file is tolerated: WS data is kept as is.
		"""
		try:
			with open(ws_file_path, "r", encoding="utf-8") as fp:
				ws_json = json.load(fp) # get json struct ws from file
		except (OSError, ValueError) as e: # ValueError covers json.JSONDecodeError
			qsp.write_error_log(f'[WS] Can not read workspace file "{ws_file_path}": {e}')
			return

		if not isinstance(ws_json, dict) or 'locations' not in ws_json \
										or 'files_paths' not in ws_json:
			qsp.write_error_log(f'[WS] Workspace file has wrong structure: "{ws_file_path}"')
			return

		# structure validated -> treat the loaded data as the known WsJson shape
		ws_json = cast(WsJson, ws_json)

		if self._locs:
			self.reset() # identity/scope живут на объекте, __init__ на себе больше не зовём (4.3)
			qsp.write_error_log(const.QSP_ERROR_MSG.WS_ALREADY_INIT)

		for place, qsp_locs in ws_json['locations'].items():
			# ws_json['locations'] = dict[abs_path: qsp_locs]
			# TODO: на данном этапе разработки все пути в файле абсолютные, однако абсолютные пути
			# TODO: должны оставаться только у файлов, хранящихся на других дисках!!!
			# qsp_locs = list[qsp_loc];
			# qsp_loc = list[name, list[start_point, end_point]]
			for name, region in qsp_locs:
				self.add_loc(name, cast(ViewRegion, tuple(region)), place)

		for path, md5 in ws_json['files_paths'].items():
			self._qsps_files['pathes'].append(path)
			self._qsps_files['hashes'].append(md5)

	def get_json_struct(self) -> WsJson:
		qsp_ws_out:WsJson = { 'locations': {}, 'files_paths': {} }
		qsp_locs_out = qsp_ws_out['locations']
		qsp_files_out = qsp_ws_out['files_paths']
		for loc in self._locs:
			if isinstance(loc.place, int): continue
			if loc.place not in qsp_locs_out: qsp_locs_out[loc.place] = []
			qsp_locs_out[loc.place].append((loc.name, loc.region))
		for i, qsps_file_path in enumerate(self._qsps_files['pathes']):
			# TODO: здесь часть путей должна преобразовываться в относительные
			# перед возвращением в виде json-структуры.
			qsp_files_out[qsps_file_path] = self._qsps_files['hashes'][i]
		return qsp_ws_out

	def save_to_file(self, project_folder:Path='') -> None:
		"""
			Save WS in json-file. project_folder must be exist!
		"""
		if not project_folder: return
		json_ws = self.get_json_struct()
		if not 'locations' in json_ws or not json_ws['locations']: return
		ws_json_path = os.path.join(project_folder, 'qsp-project-workspace.json')
		with open(ws_json_path, "w", encoding="utf-8") as ws_fp:
			json.dump(json_ws, ws_fp, indent=4, ensure_ascii=False)

	def refresh_from_views(self, windows_views:List[sublime.View], window_folders:List[AbsPath]) -> None:
		"""
			Refresh untitled views and opened files in WS.
		"""
		def _conditional_is_true(x:Optional[AbsPath], y:List[AbsPath]) -> bool:
			return x is None or qsp.is_path_in_project_folders(x, y)
		for view in windows_views:
			if QspWorkspace.view_syntax_is_wrong(view): continue
			current_qsps = view.file_name()
			if _conditional_is_true(current_qsps, window_folders):
				self.refresh_qsplocs(view, current_qsps)
		self.clear_old_qsplocs(windows_views) # clear locs from untitled views

# ---------------------------------------- WS functions ----------------------------------------

	@staticmethod
	def get_hash(file_path:str) -> str:
		md5_hash = hashlib.new('md5')
		try:
			with open(file_path, 'rb') as file:
				while True:
					data = file.read(1024)
					if not data:
						break
					md5_hash.update(data)
		except OSError as e:
			# file could be removed/locked between scan and hash read - dont break the loop
			qsp.write_error_log(f'[WS] Can not hash "{file_path}": {e}')
			return ''
		return md5_hash.hexdigest()

	@staticmethod
	def project_folder(view:sublime.View) -> Optional[Path]:
		""" Get project folder from view. """
		window = view.window()
		if not window: return
		folders = window.folders()
		return (folders[0] if folders else None)

	@staticmethod
	def current_project_folder() -> Union[str, None]:
		""" Get path of current project folder if exist. """
		folders = sublime.active_window().folders()
		return (folders[0] if folders else None)

	@staticmethod
	def get_main_pathes(view:sublime.View) -> Tuple[Union[Path, None], Union[Path, None]]:
		""" Get current qsps-file path and project_folder path. """
		current_qsps = view.file_name()
		window = view.window()
		if not window: return current_qsps, None
		folders = window.folders()
		project_folder = (folders[0] if folders else None)
		return current_qsps, project_folder

	@staticmethod
	def get_qsplbls(view:sublime.View, exclude_inputting:Optional[sublime.Region]=None) -> List[str]: # View, Region -> list
		"""
			Return list of QSP-labels created on this view
		"""
		qsp_labels:List[str] = []
		for s in view.symbol_regions():
			if exclude_inputting is None or s.region != exclude_inputting:
				if s.name.startswith('Метка: '): qsp_labels.append(s.name[7:])
		return qsp_labels

	@staticmethod
	def absing_path(project_folder:str, other_path:str) -> str: # -> abs other path
		"""
			get project_folder - abs path, other_path: rel or abs path
			return abs path of otherpath
		"""
		if os.path.abspath(os.path.join(project_folder, other_path)) == project_folder:
			return project_folder
		elif os.path.abspath(other_path) == other_path:
			return other_path
		else:
			return os.path.abspath(os.path.join(project_folder, other_path))

	@staticmethod
	def reling_path(project_folder:str, other_path:str) -> str: # rel other path, or abs if not possible
		if os.path.commonprefix([project_folder, other_path]) != '':
			return os.path.relpath(other_path, project_folder)
		else:
			return other_path

	@staticmethod
	def view_syntax_is_wrong(view:sublime.View) -> bool:
		""" Prove QSP syntax! """
		vs = view.syntax()
		return (True if (vs is None or vs.name != 'QSP') else False)