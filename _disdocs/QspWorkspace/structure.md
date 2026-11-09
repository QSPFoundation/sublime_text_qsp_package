# QspWorkspace — актуальная структура (stage 1, R7)

Техническая документация реализации `QspWorkspace` после рефакторинга stage 1 (локации, R7). Источник истины по плану/решениям — `handoff.md`, `refactor_plan.md`, `cache_architecture.md` в этой папке. Stage 2 (метки/глобальные переменные/прочие символы, автодополнение) — отдельная работа.

## Назначение

`QspWorkspace` (`QSP.sublime-package/qSpy/workspace.py`) хранит для окна ST **индекс QSP-локаций проекта**: имена, регионы, место (файл на диске или untitled-view), а также метаданные индексированных `.qsp-txt`/`.qsps` файлов для инкрементального обновления. Используется командами/листенерами плагина (`QSP.py`) для автодополнения имён локаций, поиска дубликатов локаций, подсветки невалидного ввода имени локации. Переменные не хранятся в WS и сканируются по требованию (`qSpy/vars_scanner.py: scan_vars`).

## Инварианты

- **И1.** Область индексации — все папки окна (`window.folders()`), рекурсивно; `*.qsp-txt`/`*.qsps`/`.qsps`. Плюс untitled `qsps`-буферы (только в RAM). За пределами папок окна индексации нет.
- **И2.** Окну без `.sublime-project` (`identity == None`, Open Folder) WS живёт только в RAM, файловый кэш не ведётся.
- **И3.** Живой индекс локаций во вью: правки текста отражаются через debounced `on_modified_async`.
- **И4.** Несовпадение с диском (mtime/size/md5) → перескан затронутых файлов при `refresh_qsps_files`.

## Идентичность, scope, реестр (R1/R2, 4.1/4.4)

- **RAM-ключ реестра** — `window.id()` (целое на время жизни окна), не первая папка.
- **`identity`** — `normcase(abspath(window.project_file_name()))` или `None` (нет `.sublime-project`). Используется как диск-идентичность/ключ кэша.
- **`scope`** — список папок окна `window.folders()` (все папки, не `folders[0]`).
- Реестр: `QSP_WORKSPACES: Dict[int, QspWorkspace]` в `qSpy.workspace`.
- Доступ **только** через аксессоры модуля (identity-checked, Д11):
  - `identity_of(window)`, `folders_of(window)`;
  - `for_window(window) -> QspWorkspace` — вернуть/создать, при смене identity (например Save Project As) перепривязать (`rebind`) и сбросить индекс;
  - `peek_for_window(window) -> Optional[QspWorkspace]` — вернуть существующий без создания, с проверкой identity (используется там, где создание/реактивация нежелательны, напр. debounced-колбэк, листенеры автодополнения/валидации).
- Ручное создание `QspWorkspace(...)` вне аксессоров/реестра не используется.

## Модель данных (`qSpy/workspace.py`)

```text
LocName  = str
ViewRegion = Tuple[int, int]         # (begin, end), границы view.symbol_regions()
FilePlace(path: str) | ViewPlace(vid: int)  # место локации (NamedTuple)
LocRecord(name, region, place)       # NamedTuple — запись микробазы локаций
FileMeta = {mtime, size, md5}        # метаданные индексированного файла (R4)
```

Состояние экземпляра:
- `_identity: Optional[str]`, `_scope: List[Path]`, `_cache_path: Optional[str]` (цель v2-кэша);
- `_locs: List[LocRecord]` — единственная микробаза локаций (вместо параллельных списков names/regions/places/hashes);
- `_files: Dict[AbsPath, FileMeta]` — известные qsps-файлы и их метаданные;
- `_built: bool` — индекс построен для текущей identity/scope (флаг принятого кэша/завершённого построения).

### API локаций
- `add_loc(name, region, place)` — добавить, если `(name, region, place)` ещё нет;
- `replace_locs(old_path, new_path)` — перепривязать локации файла (переименование/ассоциация буфера);
- `del_loc_by_index(i)`, `del_all_locs_by_place(place)`;
- `get_locs()`, `get_locs_names()`;
- `refresh_qsplocs(view, current_qsps)` — перескан локаций одного вью по `view.symbol_regions()` (символы `Локация: …`); место — `FilePlace(path)` или `ViewPlace(view.id())` для untitled;
- `clear_old_qsplocs(views)` — удалить локации `ViewPlace`, чьих вью больше нет;
- `locs_dupl() -> List[LocRecord]` — записи имён локаций, встречающихся >1 раза (плоский список по группам, порядок групп по первому появлению, 4.6).

### Файлы и инкрементальный индекс (R4, 4.7)
- `refresh_qsps_files(window_folders)` — строит актуальный список qsps по `scope/folders`, мигрирует legacy-кэш (`_migrate_legacy_cache`), затем инкрементально сверяет с `_files`: `mtime+size` без изменений → пропуск; иначе md5 — совпал → обновить только метаданные, изменился → `_reparse_locs`; новые/удалённые с общим md5 трактуются как переименование (`replace_locs`). Ставит `_built = True`.
- `_reparse_locs(file_path)` — перечитать локации файла (`QspsFile`) и заменить в `_locs`.
- `get_qsps_files() -> List[(path, md5)]`, `qsps_file_is_exist`, `get_hash`.
- `refresh_from_views(windows_views, window_folders)` — `refresh_qsplocs` по всем QSP-вью окна + `clear_old_qsplocs`.

## Персистентность и диск (R3/R4/R6)

Каталог кэша: `<sublime.cache_path()>/QSP/workspaces/`.

- **Файл кэша v2** (`cache_file_path(identity) -> <base>-<hash8>.json`): `CacheJson {version=2, identity, scope, built, files{path: FileMeta}, locations{file_path: [[name,(begin,end)], ...]}}`. Записываются только локации из файлов (`FilePlace`); untitled/view-локации не персистятся. Атомарная запись `.tmp` + `os.replace` (`_flush_payload`), чистый IO (без `sublime.*`) — безопасно для `on_exit`.
- `cache_payload()`, `save_to_cache()` (пишет только если есть identity, `_built` и cache_path; обновляет `index.json`), `load_from_cache()` (валидирует identity/scope и метаданные файлов на диске; несовпадение/ошибка → отклонён, индекс не принят). `rebind(identity, scope)` перепривязывает WS к окну без сброса индекса.
- **Legacy** `<scope[0]>/qsp-project-workspace.json` (v1, у `folders[0]`): одноразовая миграция при первом `refresh_qsps_files` при отсутствии v2 — переименование в `.bak` (`_migrate_legacy_cache`).
- **`index.json` v1** (неавторитативный, `index_file_path()`): `entries{identity: {file, scope, ts}}`, обновляется `update_index_entry/remove_index_entry` при save/flush/reset. Повреждённый/чужой формат игнорируется и пересоздаётся по факту записей.
- **`prune_orphan_caches(force=False)`**: async на close (throttled `PRUNE_INTERVAL_DAYS=7`), удаляет сиротки `*.json` (кроме `index.json`), чей identity отсутствует в `sublime.project_history()` и на диске, при возрасте кэша > `ORPHAN_MAX_AGE_DAYS=90`.
- **`flush_workspaces_on_exit(workspaces)`** / `QspWorkspace.flush_on_exit()`: флаш всех живых WS на выходе ST — только чистый IO (`_flush_payload` + `update_index_entry`), без `sublime.*` (Д20–Д22).

## Интеграция с плагином (`QSP.py`)

### Жизненный цикл (`QspWorkspaceHandlers`, `EventListener`)

- `_refresh_ws(window)`: `for_window` → `load_from_cache()` → `refresh_qsps_files(folders)` → `refresh_from_views(views, folders)`; окно без папок пропускается.
- `_flush_ws(window)`, `_cleanup_window(window)`: flush RAM → диск (`save_to_cache`, запись только при `_built`+identity) затем async `prune_orphan_caches`.
- `_markers[wid]` — локальные маркеры окна (переименование/удаление файлов) вместо глобального реестра.
- События: `on_init`/`on_load_project_async` → `_refresh_ws`; `on_load_async` → `refresh_qsplocs` сохранённого QSP-вью в папках окна; `on_post_save_async` → `refresh_qsplocs` + `refresh_qsps_files` + `refresh_from_views`; `on_modified_async` → debounced (`_LOCS_DEBOUNCE_MS = 250`, per-view поколение в `_locs_gen`) вызов `refresh_qsplocs` только этого вью (через `peek_for_window`, без создания WS; stale/закрытые гасит колбэк); `on_pre_close_project`/`on_pre_close_window` → flush+cleanup; `on_exit` → `flush_workspaces_on_exit(QSP_WORKSPACES)` (только IO).

### Команды и потребители
- `QspShowWorkspaceCacheCommand` — открыть v2-кэш активного окна; при отсутствии identity сообщает, что кэш не ведётся (И2).
- `QspResetWorkspaceCacheCommand` — `rebind`+сброс RAM, удаление файла кэша и записи index, перестроение как `_refresh_ws`, немедленный `save_to_cache` при наличии `.sublime-project`.
- `QspShowDuplLocsCommand` — `peek_for_window` → `locs_dupl()`, вывод в output panel.
- Автодополнение имён локаций (`QspAutocomplete`) — `peek_for_window` → `get_locs_names()` в scope `meta.start_location.qsp`.
- Валидация ввода (`QspInvalidInput`) — сверка имени локации с `get_locs_names()`.
- Подсветка переменных (`QspLocalVarsHighlightCommand`, `QspGlobalVarsHighlightCommand`) — on-demand `scan_vars(view)`, WS не используется.

## Ограничения stage 1 / техдолг
- В индексе и кэше только локации (R7). Метки/глобалы/прочие символы — stage 2.
- Типизация `load_from_cache` без `Any` — техдолг.
- `PRUNE_INTERVAL_DAYS`/`ORPHAN_MAX_AGE_DAYS` — константы, кандидаты в настройки.