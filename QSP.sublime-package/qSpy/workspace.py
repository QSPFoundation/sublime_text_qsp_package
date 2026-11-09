import sublime			# type: ignore

import os
import json
import time
from typing import (Any, Dict, NamedTuple, Optional, Set, TypedDict, Union, List, Tuple, cast)
import hashlib

from .converter import QspsFile
from . import function as qsp
from . import const as const
from .plugtypes import (AbsPath, LocName, Path, ViewId, HashMD5)
from .converter import ViewRegion

WorkspacesRegistry = Dict[int, 'QspWorkspace'] # RAM-реестр: window.id() -> WS (R1, шаг 4.B)

WS_VERSION = 2
CACHE_DIR_NAME = os.path.join('QSP', 'workspaces') # <sublime.cache_path()>/QSP/workspaces/
LEGACY_WS_FILE = 'qsp-project-workspace.json'       # старый кэш в корне проекта (R6 -> .bak)

class FilePlace(NamedTuple):
	""" Место локации — файл на диске (2.6, tagged). """
	path: Path

class ViewPlace(NamedTuple):
	""" Место локации — безымянный буфер (2.6, tagged), идентифицируется view.id(). """
	vid: ViewId

LocPlace = Union[FilePlace, ViewPlace]

class LocRecord(NamedTuple):
	""" Одна локация в индексе WS (2.6, 4.2). """
	name: LocName
	region: ViewRegion
	place: LocPlace

LocHash = LocRecord # алиас для потребителей (QSP.py)

class FileMeta(TypedDict):
	mtime: float
	size: int
	md5: HashMD5

class CacheJson(TypedDict, total=False):
	""" Схема кэша v2 на диске (R3/R4). """
	version: int
	identity: str
	scope: List[Path]
	built: bool
	files: Dict[Path, FileMeta]
	locations: Dict[Path, List[Tuple[LocName, ViewRegion]]]

# ---- вспомогательные функции кэша (R3/R4) ----

def cache_dir() -> str:
	""" Каталог кэша воркспейсов: <sublime.cache_path()>/QSP/workspaces (R3). """
	return os.path.join(sublime.cache_path(), CACHE_DIR_NAME)

def cache_file_path(identity: str) -> Optional[str]:
	""" Путь к файлу кэша по identity: <base>-<hash8>.json (R3). None при пустом identity. """
	if not identity:
		return None
	base = os.path.splitext(os.path.basename(identity))[0] or 'workspace'
	hash8 = hashlib.sha1(identity.encode('utf-8')).hexdigest()[:8]
	return os.path.join(cache_dir(), f'{base}-{hash8}.json')

def _migrate_legacy_cache(scope: List[Path]) -> None:
	""" R6: старый <scope[0]>/qsp-project-workspace.json -> .bak (без импорта). """
	if not scope:
		return
	legacy = os.path.join(scope[0], LEGACY_WS_FILE)
	if not os.path.isfile(legacy):
		return
	bak = legacy + '.bak'
	try:
		if not os.path.exists(bak):
			os.rename(legacy, bak)
		else:
			os.rename(legacy, legacy + f'.{int(time.time())}.bak')
	except OSError as e:
		qsp.write_error_log(f'[WS] Can not rename legacy cache "{legacy}": {e}')

def _stat_file(path: str) -> Optional[Tuple[float, int]]:
	""" (mtime, size) или None, если файл недоступен. """
	try:
		st = os.stat(path)
		return (st.st_mtime, st.st_size)
	except OSError:
		return None

class QspWorkspace:
	def __init__(self, identity:Optional[str]=None, scope:Optional[List[Path]]=None) -> None:
		# Идентичность и область (R1/R2; шаг 4.B): заполняются accessor-ом for_window, которым
		# создаётся WS; при несовпадении identity окна accessor пересобирает запись (Д11).
		self._identity:Optional[str] = identity # дисковый ключ: identity_of(window) или None
		self._scope:List[Path] = list(scope or []) # все папки окна на момент постройки (R2)
		self._built:bool = False # R4: WS реально построен для identity (пустой пишем только если True)
		# Целевой путь кэша готовим заранее (R5, Д20-Д22): on_exit пишет чистым IO без sublime-API.
		self._cache_path:Optional[str] = cache_file_path(identity) if identity else None
		self.reset() # индекс пустой; identity/scope/built/cache_path уже заданы

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
		self._files:Dict[AbsPath, FileMeta] = {} # R4/4.7: path -> {mtime,size,md5}
		self._built = False

# --------------------------------- qsp-locations mb functions ---------------------------------

	def add_loc(self, name:LocName, region:ViewRegion, place:LocPlace) -> None:
		""" Add new qsp-location to workspace """
		rec = LocRecord(name, region, place)
		if rec not in self._locs:
			self._locs.append(rec)

	def replace_locs(self, old_path:str, new_path:str) -> None:
		""" Change place of qsp-locations. """
		if old_path == new_path: return None
		new_place = FilePlace(new_path)
		self._locs = [
			loc._replace(place=new_place) if loc.place == FilePlace(old_path) else loc
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
		qsps_path: LocPlace = FilePlace(current_qsps) if current_qsps else ViewPlace(view.id())
		self.del_all_locs_by_place(qsps_path)
		for s in view.symbol_regions():
			if s.name.startswith('Локация: '): # TODO: привязка к тому, что символ начинается с Локация не очень удобна!
				self.add_loc(s.name[9:], (s.region.begin(), s.region.end()), qsps_path)

	def clear_old_qsplocs(self, views:List[sublime.View]) -> None:
		""" Delete locations from WS, if this views don't exist. """
		view_ids = {v.id() for v in views}
		self._locs = [
			loc for loc in self._locs
			if not (isinstance(loc.place, ViewPlace) and loc.place.vid not in view_ids)
		]

	def locs_dupl(self) -> List[LocRecord]:
		""" Имена локаций, встречающиеся более одного раза (4.6). Плоский список записей
			по группам дубликатов, порядок групп — по первому появлению имени. """
		groups:Dict[LocName, List[LocRecord]] = {}
		for loc in self._locs:
			groups.setdefault(loc.name, []).append(loc)
		return [loc for recs in groups.values() if len(recs) >= 2 for loc in recs]

# ----------------------------------- файлы и кэш (R3/R4, 4.7) -----------------------------------

	def get_qsps_files(self) -> List[Tuple[AbsPath, HashMD5]]:
		""" Совместимый снимок (path, md5) по известным файлам. """
		return [(p, m['md5']) for p, m in self._files.items()]

	def qsps_file_is_exist(self, qsps_file_path: str) -> bool:
		return qsps_file_path in self._files

	def qsps_files_number(self) -> int:
		return len(self._files)

	def touch_file(self, qsps_file_path: AbsPath) -> None:
		""" Файл изменён (save): перечитать локации и обновить метаданные (mtime/size/md5).
			Если файла ещё нет в индексе — добавить. """
		stat = _stat_file(qsps_file_path)
		if stat is None:
			return
		self._reparse_locs(qsps_file_path)
		self._files[qsps_file_path] = {'mtime': stat[0], 'size': stat[1], 'md5': self.get_hash(qsps_file_path)}

	def _reparse_locs(self, file_path: AbsPath) -> None:
		""" (Re)read qsp-locations of an existing qsps-file into the locs mb. """
		self.del_all_locs_by_place(FilePlace(file_path))
		qsps_file = QspsFile()
		qsps_file.read_from_file(file_path)
		qsps_file.split_to_locations()
		for loc_name, loc_region in qsps_file.get_loc_symbols():
			self.add_loc(loc_name, loc_region, FilePlace(file_path))

	def refresh_qsps_files(self, window_folders: List[AbsPath]) -> None:
		""" Инкрементальное обновление индекса файлов (4.7, R4).
			mtime+size не изменились -> файл не трогаем. Иначе сверяем md5: сменился ->
			перепарсить локации, тот же md5 -> только обновить метаданные. Новые/исчезнувшие
			обрабатываем с учётом переименования (общий md5). """
		_migrate_legacy_cache(self._scope)
		old_meta = dict(self._files)
		# текущее состояние файлов на диске: path -> (mtime, size)
		current: Dict[AbsPath, Tuple[float, int]] = {}
		for folder in window_folders:
			for f in qsp.get_files_list(folder):
				st = _stat_file(f)
				if st is not None:
					current[f] = st

		old_paths = set(old_meta)
		cur_paths = set(current)
		removed_paths: Set[AbsPath] = old_paths - cur_paths
		added_paths: Set[AbsPath] = cur_paths - old_paths
		common_paths = old_paths & cur_paths

		# индекс исчезнувших по md5 для детекта переименований
		removed_by_hash: Dict[HashMD5, List[AbsPath]] = {}
		for path in removed_paths:
			removed_by_hash.setdefault(old_meta[path]['md5'], []).append(path)

		renamed_sources: Set[AbsPath] = set()
		for path in added_paths:
			mtime, size = current[path]
			md5 = self.get_hash(path)
			candidates = removed_by_hash.get(md5)
			if candidates:
				# содержимое переехало -> переименование, локации сохраняем
				old_path = candidates.pop()
				renamed_sources.add(old_path)
				self.replace_locs(old_path, path)
				self._files[path] = {'mtime': mtime, 'size': size, 'md5': md5}
				self._files.pop(old_path, None)
			else:
				self._reparse_locs(path)
				self._files[path] = {'mtime': mtime, 'size': size, 'md5': md5}

		for path in common_paths:
			mtime, size = current[path]
			meta = old_meta[path]
			if meta['mtime'] == mtime and meta['size'] == size:
				continue # не менялся — не хэшируем и не парсим (4.7)
			md5 = self.get_hash(path)
			if md5 != meta['md5']:
				self._reparse_locs(path)
			# md5 тот же -> локации актуальны, обновляем только метаданные
			self._files[path] = {'mtime': mtime, 'size': size, 'md5': md5}

		for path in removed_paths:
			if path in renamed_sources:
				continue
			self.del_all_locs_by_place(FilePlace(path))
			self._files.pop(path, None)

		# к этому моменту индекс построен/обновлён для identity
		self._built = True

# ----------------------------------- файлы и кэш (R3/R4, 4.7) -----------------------------------

# ---------------------------------------- WS: диск (R3/R4/R6) ----------------------------------------

	def load_from_cache(self) -> bool:
		""" Загрузка v2-кэша из cache_path по identity (R3/R4). Возвращает True, если
			кэш принят (индекс восстановлен). Иначе WS остаётся пустым/без built — вызывающий
			должен выполнить полное сканирование (И4). Старый кэш уводится в .bak (R6). """
		_migrate_legacy_cache(self._scope)
		if not self._identity:
			return False
		path = cache_file_path(self._identity)
		if not path or not os.path.isfile(path):
			return False
		try:
			with open(path, 'r', encoding='utf-8') as fp:
				data = cast(Dict[str, Any], json.load(fp))
		except (OSError, ValueError) as e:
			qsp.write_error_log(f'[WS] Can not read cache "{path}": {e}')
			return False
		if data.get('version') != WS_VERSION:
			return False # несовпадение версии -> пересборка (R4/R6)
		if not data.get('built'):
			return False # кэш не отмечен построенным — не доверяем (R4)

		self.reset() # identity/scope не трогаем
		# файлы: берём только существующие на диске (Д6: мёртвые пути отбрасываем)
		raw_files = cast(Dict[Any, Any], data.get('files') or {})
		for fpath, meta in raw_files.items():
			if not isinstance(fpath, str) or not isinstance(meta, dict) or not os.path.isfile(fpath):
				continue
			meta_d = cast(Dict[str, Any], meta)
			md5 = meta_d.get('md5')
			if not isinstance(md5, str):
				continue
			mtime = meta_d.get('mtime')
			size = meta_d.get('size')
			self._files[fpath] = {
				'mtime': float(mtime) if isinstance(mtime, (int, float)) else 0.0,
				'size': int(size) if isinstance(size, (int, float)) else 0,
				'md5': md5,
			}
		# локации: только для файлов, которые реально есть
		raw_locs = cast(Dict[Any, Any], data.get('locations') or {})
		for place, qsp_locs in raw_locs.items():
			if not isinstance(place, str) or place not in self._files or not isinstance(qsp_locs, list):
				continue
			file_place = FilePlace(place)
			for item in cast(List[Any], qsp_locs):
				if not isinstance(item, (list, tuple)):
					continue
				item_s = cast(List[Any], item)
				if len(item_s) != 2:
					continue
				name, region = item_s[0], item_s[1]
				if not isinstance(name, str):
					continue
				self.add_loc(name, cast(ViewRegion, tuple(region)), file_place)
		self._built = True
		return True

	def cache_payload(self) -> CacheJson:
		""" Готовый к записи payload v2 (R4). Содержит только файловые места. """
		locations: Dict[Path, List[Tuple[LocName, ViewRegion]]] = {}
		for loc in self._locs:
			if not isinstance(loc.place, FilePlace):
				continue
			locations.setdefault(loc.place.path, []).append((loc.name, loc.region))
		return cast(CacheJson, {
			'version': WS_VERSION,
			'identity': self._identity or '',
			'scope': list(self._scope),
			'built': bool(self._built),
			'files': {p: dict(m) for p, m in self._files.items()},
			'locations': locations,
		})

	def save_to_cache(self) -> Optional[str]:
		""" Записать кэш v2 в cache_path (R3/R5). Возвращает путь или None, если писать нечего
			(нет identity/окно без .sublime-project, либо WS не построен — R4). """
		if not self._identity or not self._built or not self._cache_path:
			return None
		return _flush_payload(self._cache_path, self.cache_payload())

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
	def view_syntax_is_wrong(view:sublime.View) -> bool:
		""" Prove QSP syntax! """
		vs = view.syntax()
		return (True if (vs is None or vs.name != 'QSP') else False)

	def flush_on_exit(self) -> None:
		""" Флаш этого WS на выходе (R5, Д20-Д22): чистый IO, без sublime-API. """
		if self._cache_path and self._identity and self._built:
			_flush_payload(self._cache_path, self.cache_payload())

def _flush_payload(path: str, payload: CacheJson) -> Optional[str]:
	""" Атомарная запись payload (чистый IO, без sublime-API — безопасно вызывать из on_exit, Д21). """
	try:
		os.makedirs(os.path.dirname(path), exist_ok=True)
		tmp = path + '.tmp'
		with open(tmp, 'w', encoding='utf-8') as fp:
			json.dump(payload, fp, indent=4, ensure_ascii=False)
		os.replace(tmp, path)
	except OSError as e:
		qsp.write_error_log(f'[WS] Can not write cache "{path}": {e}')
		return None
	return path

def flush_workspaces_on_exit(workspaces: WorkspacesRegistry) -> None:
	""" Флаш всех живых WS на выходе из ST (R5, Д20-Д22). Только чистый Python-IO, без
		sublime-API (в on_exit оно недоступно). """
	for qsp_ws in list(workspaces.values()):
		qsp_ws.flush_on_exit()

# ---------------------------------------- WS: диск (R3/R4/R6) ----------------------------------------
