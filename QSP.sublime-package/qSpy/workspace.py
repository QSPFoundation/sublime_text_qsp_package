import sublime			# type: ignore

import os
import json
from typing import (Dict, Literal, NamedTuple, Optional, Set, TypedDict, Union, List, Tuple, cast)
import hashlib

from .converter import QspsFile
from . import function as qsp
from . import const as const
from .plugtypes import (AbsPath, LocName, Path, ViewId, HashMD5)
from .converter import ViewRegion

Point = int
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

class FindOverlapMb(TypedDict):
	separator_name: List[Literal['assign', 'while', 'brace']]
	separator_region: List[sublime.Region]
	separator_instr: List[Point]

class QspWorkspace:
	def __init__(self, all_workspaces:WorkspacesRegistry,
		identity:Optional[str]=None, scope:Optional[List[Path]]=None) -> None:
		self._all_ws = all_workspaces # dict of all workspaces
		# Идентичность и область (R1/R2; шаг 4.B): заполняются accessor-ом for_window, которым
		# создаётся WS; при несовпадении identity окна accessor пересобирает запись (Д11).
		self._identity:Optional[str] = identity # дисковый ключ: identity_of(window) или None
		self._scope:List[Path] = list(scope or []) # все папки окна на момент постройки (R2)
		self.save_temp_files:bool = True
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

	def _log(self, string:str) -> None:
		if self.save_temp_files:
			qsp.log(string)

	def reset(self) -> None:
		""" Сброс индекса (4.3). identity, scope, ссылка на реестр и флаги режима не трогаются. """
		self._locs:List[LocRecord] = []
		self._qsps_files:QspsFilesMb = {
			'pathes': [],	# all files in project (abs pathes)
			'hashes': []	# md5
		}
		self._local_vars:List[sublime.Region] = []
		self._global_vars:List[sublime.Region] = []
		self._global_vars_names:Set[str] = set()

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
		""" Get qsp-locations with duplicate names. """
		qsp_locs:List[LocRecord] = []
		exclude:List[LocRecord] = []
		names = [loc.name for loc in self._locs]
		for i, loc in enumerate(self._locs):
			if (loc not in exclude) and (loc.name in names[i+1:]):
				qsp_locs.append(loc)
				exclude.append(loc)
				u = i + 1
				while u < len(self._locs) and loc.name in names[u:]:
					u = names.index(loc.name, u)
					qsp_locs.append(self._locs[u])
					exclude.append(self._locs[u])
					u += 1
		return qsp_locs

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
				self.refresh_vars(view)
		self.clear_old_qsplocs(windows_views) # clear locs from untitled views

# ---------------------------------------- WS functions ----------------------------------------


# ---------------------------------- variables mb function in WS ----------------------------------
	def refresh_vars(self, view:sublime.View) -> None:
		def _find_overlap_main(start_find:int):
			maximal = view.size()+1
			mini_data_base:FindOverlapMb = {
				"separator_name": [
					'assign',
					'while',
					'brace'
				],
				"separator_region":
				[
					view.find('=', start_find, flags=1+2),
					view.find('while', start_find, flags=1+2),
					view.find('}', start_find, flags=1+2)
				],
				"separator_instr":
				[]
			}
			for i, _ in enumerate(mini_data_base['separator_name']):
				region = mini_data_base['separator_region'][i]
				mini_data_base['separator_instr'].append(
					region.begin() if region.begin()!=-1 else maximal)
			minimal = min(mini_data_base['separator_instr'])
			if minimal != maximal:
				i = mini_data_base['separator_instr'].index(minimal)
				sprtr_type = mini_data_base['separator_name'][i]
				sprtr_region = mini_data_base['separator_region'][i]
				return sprtr_type, sprtr_region
			else:
				return None, None

		def _safe_f(x:str, y:sublime.Region, z:Point) -> bool:
			""" Selector, """
			return view.match_selector(y.begin(),x) and y.begin()<z

		kw_regions = view.find_all('local', flags=2+4)
		vars_regions:List[sublime.Region] = []
		
		for r in kw_regions:
			if not view.match_selector(r.begin(), 'keyword.declaration.variables.qsp'):
				continue
			# not use 'local' in string and comment scopes
			start_region = r.end()
			end_line = view.line(r).end()
			end_region = end_line
			start_find = start_region
			# print(view.substr(sublime.Region(start_region, end_region)))
			while start_find < end_line:
				sprtr_type, sprtr_region = _find_overlap_main(start_find)
				if sprtr_type == 'assign':
					if _safe_f('keyword.operator.one-sign.qsp', cast(sublime.Region, sprtr_region), end_line):
						end_region = sprtr_region.begin()-1
						break
					else:
						start_find = sprtr_region.end()
				elif sprtr_type == 'while':
					if _safe_f('keyword.control.qsp', cast(sublime.Region, sprtr_region), end_line):
						end_region = sprtr_region.begin()-1
						break
					else:
						start_find = sprtr_region.end()
				elif sprtr_type == 'brace':
					if _safe_f('avs_brace_end', cast(sublime.Region, sprtr_region), end_line):
						end_region = sprtr_region.begin()-1
						break
					else:
						start_find = sprtr_region.end()
				else:
					end_region = end_line
					break
				# break
			vars_regions.append(sublime.Region(start_region, end_region))
			# print(view.substr(sublime.Region(start_region, end_region)))
		if len(vars_regions) == 0: return None

		user_variable = r'\$?[A-Za-zА-Яа-я_][\w\.]*'
		# uv_regions = view.find_all(user_variable, 2)
		# start = 0
		# for uv in uv_regions[0:25]:
		# 	f = view.find(user_variable, start, 2)
		# 	start = f.end()
		# 	print(view.substr(f))
		# 	print(view.substr(uv))
		start_point = vars_regions[0].begin()
		edge_point = vars_regions[0].end()
		end_point = vars_regions[-1].end()
		i = 1
		u = 0
		local_vars:List[sublime.Region] = []
		while start_point < end_point and not u > 999:
			u += 1
			find_var = view.find(user_variable, start_point, flags=2)
			if find_var.begin()!=-1 and find_var.begin() < edge_point:
				# print(start_point, view.substr(find_var), find_var)
				for var in view.find_all(view.substr(find_var).replace('$', r'\$')+r'\b', flags=2):
					if not find_var.begin() > var.begin() and view.match_selector(var.begin(), 'meta.user-variables.qsp'):
						# print(var, view.substr(var))
						local_vars.append(var)
			start_point = find_var.end()+1
			if start_point > edge_point:
				if i < len(vars_regions):
					start_point = vars_regions[i].begin()
					edge_point = vars_regions[i].end()
					i += 1
				else:
					break
		self._local_vars = local_vars # list[sublime.Region]
		global_vars:List[sublime.Region] = []
		for var in view.find_all(user_variable, flags=2):
			if not var in local_vars and view.match_selector(var.begin(), 'meta.user-variables.qsp'):
				global_vars.append(var)
				self._global_vars_names.add(view.substr(var))
		self._global_vars = global_vars

	def get_local_vars(self) -> List[sublime.Region]:
		return self._local_vars

	def get_global_vars(self) -> List[sublime.Region]:
		return self._global_vars

# ---------------------------------- variables mb function in WS ----------------------------------

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