# План рефакторинга: работа с QspWorkspace

Объект правок: `QSP.sublime-package/qSpy/workspace.py` (класс `QspWorkspace`) и
`QSP.sublime-package/QSP.py` (класс `QspWorkspaceHandlers` + команды-потребители).
Контекст модели данных — см. `structure.md`.

Приоритеты: **P0** — падающие/портящие данные баги; **P1** — белые дыры и хрупкость;
**P2** — мёртвый код; **P3** — производительность и реструктуризация.
Финальная приёмка, проверка и коммиты — вручную. Каждый пункт можно принимать отдельным коммитом
(`qwen fix(ws): ...` / `qwen ref(ws): ...`).

---

## P0 — логические ошибки, портящие данные

> Статус: 1.1–1.5 реализованы в `workspace.py` / `QSP.py` (ждут приёмки/коммита вручную).

### 1.1 ✅ `replace_locs` — бесконечный цикл при `new_path == old_path`
`workspace.py:79-84`. Пока `old_path in places` заменяем на `new_path`; если пути равны — условие
никогда не станет ложным. **Фикс:** `if old_path == new_path: return` в начале.

### 1.2 ✅ `refresh_qsps_files` — «переименование» определяется только по md5
`workspace.py:191-207`. Новый файл, чей md5 случайно совпал с md5 удалённого, трактуется как
переименование: его локации **не парсятся заново**, а локации удалённого файла просто «переезжают».
Два идентичных по содержимому файла (частый случай — копия локации) → молчаливое повреждение WS.
**Фикс:** разделять идентичность (путь) и содержимое (хэш): переименование считать только когда
файл убрался и появился с тем же md5 **и** его нельзя сопоставить как новый по другому признаку;
либо после «rename» всё равно перепарсивать новый файл. Как минимум — не делать rename-matching
по одному лишь md5 без проверки, что путь действительно изменился.

### 1.3 ✅ `extract_from_file` — падение на битом/неполном json
`workspace.py:234-258`. Нет `try/except`, нет проверки наличия ключей `locations` / `files_paths`.
Повреждённый `qsp-project-workspace.json` роняет весь `_refresh_ws` на старте.
**Фикс:** обернуть `json.load`, валидировать структуру, при ошибке — лог + старт с пустого WS.

### 1.4 ✅ `get_hash` — нет защиты от недоступного файла
`workspace.py:432-441`. Файл мог быть удалён/заблокирован между сканированием и чтением →
исключение убивает цикл `refresh_qsps_files`. **Фикс:** `try/except`, пропуск/лог, не ронять обход.

### 1.5 ✅ `on_navigate` в дубликатах локаций ломается на абсолютных Windows-путях
`QSP.py:363-392`. Ссылка строится как `f:{qsp_loc_place}{count}` где `count = ':123'`, а затем
`int(link.split(':')[1])`. Для `D:\...\file.qsps:123` `split(':')[1]` == `\...`, а не номер строки.
Плюс сравнение `current_view.file_name() == link`, когда `link` ещё содержит `:line` (ветка
«файл уже открыт» никогда не срабатывала), и off-by-one: `text_point` ждёт 0-based row, а `count`
1-based.
**Разделитель остаётся `:`** — href это родной формат ST `open_file(encoded_position)`, его нельзя
менить без пересборки всей генерации ссылки (`os.path` здесь не помогает — нет функции для отсечения
`:line`). Реализовано: `head, sep, tail = link.rpartition(':')`; строкой считаем `tail`, только если
он целиком `isdigit()`. Путь qsps всегда имеет расширение, поэтому хвост `\...` (после `D:`) или
`/home/...` — не число → ложных срабатываний нет, работает на Windows/linux/macos одинаково. Далее:
сравнение с `file_name()` идёт по чистому `path`; `text_point(int(line)-1, 0)`; `open_file` с
`encoded_position` передаётся только когда строка реально есть, иначе — обычный `open_file` по пути.

---

## P1 — белые дыры и хрупкость

### 2.1 `on_pre_close_project` — фантомный WS и непоследовательный project_folder
`QSP.py:609-616`. `project_folder` берётся из `extract_variables().get('folder','')` (пусто, если
папок нет), затем `_get_qsp_ws('')` **создаёт пустой WS** в реестре и зовёт `save_to_file('')`.
Везде в коде `project_folder == folders[0]`. **Фикс:** единый способ получения `folders[0]`
(см. 4.4); при отсутствии папок — ничего не делать; при закрытии **не создавать** WS.

### 2.2 `on_associate_buffer_async` — IndexError на пустом окне
`QSP.py:692-693`. `folders = window.folders(); project_folder = folders[0]` без проверки.
**Фикс:** `if not folders: return`.

### 2.3 `refresh_vars` — произвольный потолок `u > 999`
`workspace.py:399`. На файлах с >999 итерациями локальные переменные молча досрочно обрываются.
**Фикс:** переписать цикл без искусственного лимита (см. 4.5 — вынос в отдельный модуль).

### 2.4 Привязка переменных к воркспейсу вместо вью: гонка между вью
`workspace.py:416-422`, `QSP.py:294-311`. `_local_vars/_global_vars` хранятся на **проектовом**
объекте, но относятся к одному конкретному вью; команды вызывают `refresh_vars(view)` сразу перед
`get_*_vars()`. Если два вью подсвечиваются параллельно (async) — состояние затирается.
**Фикс:** хранить регионы переменных не в WS, а возвращать/кэшировать per-view
(`view.id() -> regions`), либо вообще убрать из WS (переменные — не «проектная» правда).

### 2.5 `close_project`/`project_is_closing` — маркер никогда не сбрасывается
`workspace.py:300-304`, `markers`-dict `workspace.py:60-62`. Единственный флаг живёт в словаре.
**Фикс:** заменить словарь на булево поле `self._closing`; либо вовсе убрать, если после
реструктуризации закрытия WS не переживает окно (см. 4.x).

### 2.6 Смешение типов в `place` (str|ViewId)
Ветвления по типу встречаются по всему WS (`isinstance(place, int)` в `get_json_struct`, `clear_old_qsplocs`,
`QspInvalidInput`, `QspShowDuplLocs`). **Фикс** (блок 4.2) — tagged-модель места локации.

---

## P2 — мёртвый код (безопасно удалить)

### 3.1 `absing_path` / `reling_path`
`workspace.py:478-496`. Ни одного вызова в репозитории. Удалить (возвратятся вместе с фичей
относительных путей из TODO в `get_json_struct`).

### 3.2 `_global_vars_names`
`workspace.py:57, 421`. Только запись, нет геттера/потребителя. Либо удалить, либо (если это
затравка для фичи todo.md:53 «вести список переменных») — добавить публичный геттер и реального
потребителя; иначе — удалить, поле ещё и накапливается без очистки между вью.

### 3.3 `QspWorkspace._log` и поле `save_temp_files`
`workspace.py:59, 64-66`. `_log` нигде не вызывается; `save_temp_files` кормит только его.
Удалить оба (не путать с одноимённым полем схемы билдера в `plugtypes` — оно живое).

### 3.4 Ссылка `self._all_ws`
`workspace.py:41, 244`. Используется только для само-сброса через `self.__init__(self._all_ws)`
в `extract_from_file`. После введения нормального `reset()` (4.3) — удалить поле.

### 3.5 `QspDeveloperTestCommand`
`QSP.py:722-728`. Дебажный `print` с прямым `QSP_WORKSPACES[...]` (KeyError-риск). Удалить или
вынести за пределы поставляемого пакета.

---

## P3 — производительность (зависания на старте) и реструктуризация

### 4.1 Реестр и получение экземпляра — единая точка
Сейчас 3 способа получения WS: `_get_qsp_ws`, `_extract_qsp_ws` (в EventListener) и ручные
`.get()/QspWorkspace(...)` в 6 командах. **Фикс:** ввести `QspWorkspaceRegistry` (или classmethod
`QspWorkspace.for_folder(folder)`, `QspWorkspace.load_from_file(folder)`), владеющий словарём
`QSP_WORKSPACES`. Политика «создать пустой / загрузить из файла» — в одном месте. Все потребители
ходят только через него.

### 4.2 Модель данных локаций — убрать параллельные списки
`names/regions/places/hashes` (`workspace.py:43-48, 70-106`) — 4 синхронно мутируемых списка,
`hashes` дублирует остальные три. **Фикс:** один `list[LocRecord]` (dataclass/NamedTuple:
`name, region, place`) либо `dict[id] -> LocRecord`. Убрать `loc_hash_update`, инвариант
синхронности становится недостижимым. `get_locs()` собирает кортежи по требованию.

### 4.3 `reset()` вместо вызова `__init__` на себе
`workspace.py:243-245`. Добавить явный метод `clear()/reset()`.

### 4.4 Единый `project_folder`
Ввести helper `project_folder_of(window) -> Optional[Path]` (=`folders[0] or None`) и использовать
везде вместо разнобоя `extract_variables`/`folders[0]`/`get_main_pathes`.

### 4.5 Вынос сканера переменных в отдельный модуль
`refresh_vars` (`workspace.py:310-422`, ~110 строк парсинга скоупов) не относится к учёту
проекта. **Фикс:** `qSpy/vars_scanner.py` с чистая функцией `scan_vars(view) -> (local, global)`;
WS только хранит результаты (или не хранит — см. 2.4).

### 4.6 Дедуп-поиск локаций — переписать
`locs_dupl` (`workspace.py:130-145`) даёт повторы (todo.md:48). **Фикс:** `defaultdict(list)`
name→records, вернуть группы с `len>=2`. Сложнее алгоритма не сделает.

### 4.7 Инкрементальное сканирование
Старт проходит `get_hash` по каждому файлу и синхронно `QspsFile.read+split` по каждому новому
(todo.md:54, history.md «Не исправлено»). **Фикс:** кэш по mtime, не перехэшировать неизменённое;
разбор новых файлов — не в горячем пути `on_init` целиком (объём — отдельно, по возможности).

### 4.8 Магические числа → константы Sublime
`flags=256` → `sublime.DRAW_NO_OUTLINE`; `2048+256+32` → `DRAW_SQUIGGLY_UNDERLINE |
DRAW_NO_OUTLINE | DRAW_NO_FILL`; `return (…, 24)` → `INHIBIT_WORD_COMPLETIONS |
INHIBIT_EXPLICIT_COMPLETIONS`; `find/find_all flags=2/4/1+2` — именовать. См.
`_disdocs/hist_docs_for_review/sublime_api_workspace.md`.

### 4.9 Логирование через жёсткий путь
`function.log` и `QspWorkspaceHandlers._log` пишут в `D:\my\GameDev\...\qsp-workspace-log.log` —
на чужой машине упадёт. **Фикс:** убрать хардкод, лог в ST-консоль (`print`) за настройкой.

---

## Порядок работ (предлагаемые коммиты)

1. `qwen fix(ws): guard replace_locs, get_hash, extract_from_file; fix dup-nav links` (P0 1.1-1.5)
2. `qwen fix(ws): project_folder & empty-window guards in close/associate handlers` (P1 2.1-2.2)
3. `qwen del(ws): remove dead absing/reling, _global_vars_names, _log/save_temp_files, _all_ws, dev cmd` (P2)
4. `qwen ref(ws): unify workspace registry accessor (for_folder/load)` (P3 4.1, 4.4)
5. `qwen ref(ws): LocRecord model, drop parallel lists + reset()` (P3 4.2, 4.3)
6. `qwen ref(ws): rewrite locs_dupl; extract vars_scanner` (P3 4.6, 4.5; P1 2.3-2.4)
7. `qwen ref(ws): sublime constants for flags; drop hardcoded logging` (P3 4.8, 4.9)
8. (отдельно, объёмно) `qwen perf(ws): incremental scan by mtime` (P3 4.7)

Регресс сверять по `_examples/.tests` (есть `_base test_.py`, golden-тесты). Каждый шаг —
небольшой, приемка/коммит вручную.
