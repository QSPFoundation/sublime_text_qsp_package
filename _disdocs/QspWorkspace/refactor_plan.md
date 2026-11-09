# План рефакторинга: работа с QspWorkspace

Объект правок: `QSP.sublime-package/qSpy/workspace.py` (класс `QspWorkspace`) и
`QSP.sublime-package/QSP.py` (класс `QspWorkspaceHandlers` + команды-потребители).
Контекст модели данных — см. `structure.md`.

Архитектурные решения (идентичность проекта, хранилище кэша, живой индекс локаций) — см.
`cache_architecture.md`: они меняют формулировки пунктов 2.1, 2.4, 2.5, 3.2 и добавляют 2.7–2.9.
Где мы сейчас и что блокирует код — см. `handoff.md` (перенос контекста между чат-сессиями).

Приоритеты: **P0** — падающие/портящие данные баги; **P1** — белые дыры и хрупкость;
**P2** — мёртвый код; **P3** — производительность и реструктуризация.
Финальная приёмка, проверка и коммиты — вручную. Каждый пункт можно принимать отдельным коммитом
(`qwen fix(ws): ...` / `qwen ref(ws): ...`).

---

## P0 — логические ошибки, портящие данные

> Статус: 1.1–1.5 реализованы в `workspace.py` / `QSP.py` (**приёмка 09.11 пройдена, закоммичены**).

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

> Статус: **2.1–2.10, 3.1–3.5, 4.2/4.3, 4.5–4.9, 4.7 (R3/R4/R5) — приёмка 09.11 пройдена, ошибок
> не найдено, быстродействие повысилось, коммиты 6–9 + срез сделаны** (6: `bac61db`, 7:
> `cc971eb`/`72dd1aa`, 8: `068dc52`, 8+: `f0aba62`, 9: `61c35f4`). Переклейка реестра (4.A–D, коммит
> 5) закоммичена ранее. **Follow-up R3, шаг 1 (команды `qsp_show/reset_workspace_cache` +
> `Default.sublime-commands`) — реализован в дереве, коммит/приёмка за автором.** Остались:
> follow-up R3 шаг 2 (`index.json`, чистка сироток R6), хвост 4.1/4.4, замер дебаунса 2.8; техдолг —
> типизация `load_from_cache` без `Any`, pre-existing `reportOptionalMemberAccess` в `vars_scanner`.

### 2.1 ✅ `on_pre_close_project` — фантомный WS и непоследовательный project_folder
`QSP.py:609-616`. `project_folder` берётся из `extract_variables().get('folder','')` (пусто, если
папок нет), затем `_get_qsp_ws('')` **создаёт пустой WS** в реестре и зовёт `save_to_file('')`.
Везде в коде `project_folder == folders[0]`. **Фикс:** единый способ получения `folders[0]`
(см. 4.4); при отсутствии папок — ничего не делать; при закрытии **не создавать** WS.

> Уточнение по снимкам (`cache_architecture.md`, Д1/Д2): `${folder}` всегда равен `folders[0]`, так что
> «чужой ключ» возникает не из-за `extract_variables()`, а потому что сам `folders[0]` может быть
> посторонней папкой (у JAD первой стоит `[lib]\easy.math.3`). Поэтому фикс — не «везде брать
> `folders[0]`», а `identity_of(window)` + accessor без создания + `pop` при закрытии (R1/R5).
>
> Лог датчика (прогон 23:03–23:07) добавил к этому: внутри `on_pre_close_project` `project_file()` и
> `folders()` ещё заполнены (Д8) — фикс реализуем; но `folders()` к моменту закрытия уже мог
> **сузиться** (Д9), так что область индекса берём из сохранённого `scope`, а не из окна; записи
> закрытых проектов из реестра не удаляются (Д10) — `pop` обязателен; при смене проекта в том же
> окне `window.id()` сохраняется (Д11) — accessor обязан сверять `identity` записи.

### 2.2 ✅ `on_associate_buffer_async` — IndexError на пустом окне
`QSP.py:692-693`. `folders = window.folders(); project_folder = folders[0]` без проверки.
**Фикс:** `if not folders: return`.

### 2.3 ✅ `refresh_vars` — произвольный потолок `u > 999`
`workspace.py` (ранее). На файлах с >999 итерациями локальные переменные молча обрывались.
**Фикс (4.5, вариант a):** логика вынесена в `qSpy/vars_scanner.py:scan_vars(view) -> (local, global)`
как чистая функция; искусственный `u > 999` удалён, остановка естественная по границам/неудачному
`find`. Регионы переменных в WS не хранятся (см. 2.4).

### 2.4 ✅ Привязка переменных к воркспейсу вместо вью: гонка между вью
`workspace.py`/`QSP.py` (ранее). `_local_vars/_global_vars` хранились на проектном WS, но относились
к одному вью. **Фикс (4.5, вариант a):** регионы в WS не хранятся — `scan_vars(view)` вычисляет их
on-demand; команды хайлайта (`QspLocalVarsHighlightCommand`/`QspGlobalVarsHighlightCommand`) вызывают
сканер напрямую и сразу рисуют регионы. `_global_vars_names` удалён (3.2 решён удалением: потребителя
нет; при появлении на этапе 2 — восстановить).

### 2.5 ✅ `close_project`/`project_is_closing` — маркер никогда не сбрасывается
`workspace.py:300-304`, `markers`-dict `workspace.py:60-62`. Единственный флаг живёт в словаре.
**Фикс:** заменить словарь на булево поле `self._closing`; либо вовсе убрать, если после
реструктуризации закрытия WS не переживает окно (см. 4.x).

> Измерено датчиком (Э4, `cache_architecture.md`, Д15): `on_pre_close(view)` действительно
> приходит **после** `on_pre_close_project` — закрывается окно с проектом — и в этот момент
> `view.window()` уже `None`. Значит маркер нельзя завязывать на «найти WS по окну вью»: окно
> теряется, а не остаётся «незакрытым». Точка флаша — сам `on_pre_close_project`, и он же
> покрывает закрытие окна.

### 2.6 ✅ Смешение типов в `place` (str|ViewId)
Ветвления по типу (`isinstance(place, int)`) были в `get_json_struct`, `clear_old_qsplocs`,
`QspInvalidInput`, `QspShowDuplLocs`. **Фикс:** tagged-модель места локации —
`FilePlace(path)` / `ViewPlace(vid)` (`NamedTuple`, `workspace.py`), `LocPlace = FilePlace|ViewPlace`.
Внутри WS хранятся только tagged-значения; в JSON пишутся/читаются только файловые пути (как и
раньше, `ViewPlace` не сериализуется). Разбор по типу — `isinstance(..., FilePlace|ViewPlace)`.

### 2.7 ✅ `on_post_save_async` индексирует файлы вне папок окна
`QSP.py:674-691`: в отличие от `on_load_async`, здесь нет проверки `is_path_in_project_folders` →
сохранение одиночного файла вне проекта заносит его локации и путь в WS проекта (нарушение И1 из
`cache_architecture.md`). **Фикс:** та же проверка, что в `on_load_async`.

### 2.8 ✅ `on_query_completions` пересканирует все вью на каждый запрос
`QSP.py:480, 495`: синхронный `refresh_from_views(...)` из UI-пути (блокирует попап и мутирует WS),
компенсирующий отсутствие живого обновления. Плюс метки берутся только из текущего вью
(`QSP.py:449, 512`), а глобальные переменные в подсказках отсутствуют вовсе. **Фикс (только
локации — этап 1):** живое обновление индекса по `on_modified_async` (дебаунс, перескан одного вью
уже реализованным `refresh_qsplocs`) + чтение готового индекса в completion (R5/R7). Метки и
глобальные в подсказках — **этап 2**, здесь только зафиксированы.

> Реализовано (коммит 6, ждёт приёмки): оба `refresh_from_views` из `on_query_completions` сняты;
> живое обновление — `QspWorkspaceHandlers.on_modified_async` с per-view дебаунсом (счётчик
> поколений `_locs_gen`, модульный `sublime.set_timeout_async`; `_LOCS_DEBOUNCE_MS = 250` —
> кандидат до замера) → перескан одного вью через `refresh_qsplocs` с проверками синтаксиса,
> живого окна, И1 и `peek_for_window` без создания. `QspInvalidInput` не тронут (черновая правка
> с переносом подсветки в async отменена).

### 2.9 ✅ `QspProject._work_dir_init` — IndexError на окне без папок
`project.py:81-83`: при пустом `point_file` берётся `self._window_folders[0]` без проверки (тот же
класс ошибки, что в 2.2). **Фикс:** ранний выход/фолбэк при пустом списке папок.

### 2.10 ✅ `is_path_in_project_folders` — не проверяла вложенность (Д27)
`function.py:67-80`: `if os.path.commonpath([path, folder])` — непустой общий корень есть у любых
путей одного диска, поэтому функция возвращала `True` для любого файла на том же диске. И1
нарушалась во всех проверках (`on_load_async`, `on_post_save_async`/2.7, `refresh_from_views`,
`on_modified_async`/2.8): чужой файл индексировался, а после закрытия его вью имя оставалось в
индексе (`on_pre_close` снимает локации только безымянных буферов). **Фикс:** `normcase(abspath)`
обоих путей и сравнение `commonpath == папка` (вложенность); `ValueError`-фолбэк для разных дисков
сохранён. Обнаружено приёмкой 2.8 (сценарий И1 «чужой файл», 09.11); исправлено в том же срезе.

---

## P2 — мёртвый код (безопасно удалить)

### 3.1 ✅ `absing_path` / `reling_path`
`workspace.py` (ранее). Ни одного вызова в репозитории. Удалены (возвратятся, если для R4
понадобятся относительные пути в кэше).

### 3.2 ✅ `_global_vars_names` — удалён (решён вариантом a, 4.5/2.4)
`workspace.py` (ранее). Только запись, читателя нет. Удалён вместе с хранением переменных в WS (2.4,
вариант a). Если на этапе 2 имена глобальных пойдут в индекс сущностей (R7) — восстановить с
очисткой в `reset()` (4.3).

### 3.3 ✅ `QspWorkspace._log` и поле `save_temp_files`
`workspace.py` (ранее). `_log` нигде не вызывался; `save_temp_files` кормил только его.
Удалены (4.9). (Не путать с одноимённым полем схемы билдера в `plugtypes` — оно живое.)

### 3.4 ✅ Ссылка `self._all_ws` / аргумент конструктора
`workspace.py` (ранее): `self._all_ws` и само-сброс через `self.__init__` на себе ушли ещё в 4.3.
Неиспользуемый аргумент `all_workspaces` конструктора удалён, `for_window` создаёт WS без него.

### 3.5 ✅ `QspDeveloperTestCommand`
`QSP.py` (ранее). Дебажная команда с прямым `QSP_WORKSPACES` — удалена. (Модульная `foo()` оставлена
как отладочный хелпер вне поставляемых команд.)

---

## P3 — производительность (зависания на старте) и реструктуризация

### 4.1 Реестр и получение экземпляра — единая точка
Сейчас 3 способа получения WS: `_get_qsp_ws`, `_extract_qsp_ws` (в EventListener) и ручные
`.get()/QspWorkspace(...)` в 6 командах. **Фикс:** ввести `QspWorkspaceRegistry` (или classmethod
`QspWorkspace.for_folder(folder)`, `QspWorkspace.load_from_file(folder)`), владеющий словарём
`QSP_WORKSPACES`. Политика «создать пустой / загрузить из файла» — в одном месте. Все потребители
ходят только через него.

> Статус (шаг 4): способы получения сведены к двум accessor-ам `QspWorkspaceHandlers.for_window` /
> `peek_for_window` с ключом `window.id()` и сверкой `identity` (срез B, handoff §6); реестр пока
> остаётся модульным dict в `QSP.py`. Закрытие сделано в C: флаш по `qsp_ws.scope` (Д9),
> `on_pre_close_window` чистит RAM для безпроектных окон (Д24/И2). Осталось: маркер (D);
> v2-загрузка с диска и флаш `on_exit` — шаг 9.

### 4.2 ✅ Модель данных локаций — убрать параллельные списки
`names/regions/places/hashes` (`workspace.py:43-48, 70-106`) — 4 синхронно мутируемых списка,
`hashes` дублирует остальные три. **Фикс:** один `list[LocRecord]` (dataclass/NamedTuple:
`name, region, place`) либо `dict[id] -> LocRecord`. Убрать `loc_hash_update`, инвариант
синхронности становится недостижимым. `get_locs()` собирает кортежи по требованию.

### 4.3 ✅ `reset()` вместо вызова `__init__` на себе
`workspace.py:243-245`. Добавить явный метод `clear()/reset()`.

### 4.4 Единый `project_folder`
Ввести helper `project_folder_of(window) -> Optional[Path]` (=`folders[0] or None`) и использовать
везде вместо разнобоя `extract_variables`/`folders[0]`/`get_main_pathes`.

### 4.5 ✅ Вынос сканера переменных в отдельный модуль
`refresh_vars` (~110 строк) не относится к учёту проекта. **Сделано (вариант a):**
`qSpy/vars_scanner.py` с чистой функцией `scan_vars(view) -> (local, global)`; WS регионы не хранит
(2.4). Потолок `u > 999` снят (2.3), остановка естественная. `refresh_from_views`/`on_load_async`
переменные не трогают; команды хайлайта сканируют on-demand.

### 4.6 ✅ Дедуп-поиск локаций — переписать
`locs_dupl` давал повторы (todo.md:48). **Сделано:** группировка `name -> [LocRecord]` за один проход
(`defaultdict/setdefault`), возврат групп с `len>=2` в плоском списке; порядок групп — по первому
появлению. Сигнатура и форма результата прежние.

### 4.7 ✅ Инкрементальное сканирование (R3/R4, коммит 9)
Старт: `load_from_cache()` читает v2 из `<cache_path>/QSP/workspaces/<base>-<hash8>.json` (по
`identity`), отбрасывая мёртвые пути (Д6) и принимая только `version==2, built==true`; иначе —
полный перескан. `refresh_qsps_files()` сверяет файлы по **mtime+size** (не хэширует неизменённое):
при смене содержимого — перепарс локаций и новый md5, при том же md5 — только метаданные;
добавление/удаление/переименование (общий md5) сохраняют локации где возможно. Запись: атомарный
флаш v2 (`payload` + `_cache_path` подготовлен заранее) на `on_pre_close_project` и на `on_exit()`
(чистый IO без sublime-API, R5/Д20–Д22). Окно без `.sublime-project` на диск не пишет (И2). Старый
`<scope[0]>/qsp-project-workspace.json` уводится в `.bak` (R6). **Follow-up R3 (шаг 1, в дереве, ждёт
приёмки/коммита):** команды `qsp_show_workspace_cache`/`qsp_reset_workspace_cache` (`QSP.py`) + палитра
`Default.sublime-commands`; `QspWorkspace.rebind`. **Не сделано (follow-up R3, шаг 2):** `index.json`,
чистка сироток (R6).

### 4.8 ✅ Магические числа → константы Sublime
`flags=256` → `sublime.DRAW_NO_OUTLINE`; `2048+256+32` → `DRAW_SQUIGGLY_UNDERLINE | DRAW_NO_OUTLINE |
DRAW_NO_FILL`; `return (…, 24)` → `INHIBIT_WORD_COMPLETIONS | INHIBIT_EXPLICIT_COMPLETIONS`;
`find/find_all` в `vars_scanner.py` именованы (`LITERAL`/`IGNORECASE`). См.
`_disdocs/hist_docs_for_review/sublime_api_workspace.md`.

### 4.9 ✅ Логирование через жёсткий путь
`function.log` и `QspWorkspaceHandlers._log` писали в жёсткий Windows-путь — на чужой машине падает.
**Сделано:** `function.log` удалён (единственный вызов был мёртвый `QspWorkspace._log`, см. 3.3);
`QspWorkspaceHandlers._log` пишет в консоль ST (`print('[QSP WS] ...')`) под тем же флагом
`_log_it`. `QspWorkspace._log`/`save_temp_files` удалены (3.3).

---

## Порядок работ (предлагаемые коммиты)

1. `qwen fix(ws): guard replace_locs, get_hash, extract_from_file; fix dup-nav links` (P0 1.1-1.5)
2. ✅ `qwen fix(ws): workspace identity + empty-window guards; drop out-of-folder indexing` (P1 2.1-2.2, 2.7, 2.9)
3. `qwen del(ws): remove dead absing/reling, _log/save_temp_files, _all_ws, dev cmd` (P2 3.1, 3.3-3.5)
4. `qwen ref(ws): registry with identity_of(window) + window.id() keys, load + pop` (P3 4.1, 4.4; R1, R5)
   — A–D закоммичены автором
5. `qwen ref(ws): SymbolRecord model, drop parallel lists + reset()` (P3 4.2, 4.3; R7)
   — сделан как LocRecord (этап 1; SymbolRecord — этап 2), закоммичен автором (`e640063`)
6. ✅ `qwen ref(ws): live loc index by on_modified_async; completion reads ready index` (P1 2.8; R5/R7 этап 1) — `bac61db` (250 мс — кандидат, замер при необходимости), приёмка пройдена
7. ✅ `qwen ref(ws): rewrite locs_dupl; extract vars_scanner` (P3 4.6, 4.5; P1 2.3-2.4) — `cc971eb`/`72dd1aa` (вариант a), приёмка пройдена; 3.2 снят удалением
8. ✅ `qwen ref(ws): sublime constants for flags; drop hardcoded logging` (P3 4.8, 4.9) — `068dc52`, приёмка пройдена; попутно 3.3
9. ✅ `qwen perf(ws): cache v2 in cache_path + incremental scan by mtime` (P3 4.7; R3, R4) — `61c35f4`, приёмка пройдена (ошибок не найдено, быстродействие выше)
10. (follow-up R3, шаг 1) `qsp_show/reset_workspace_cache` + `Default.sublime-commands` (+ `rebind`) — **реализовано в дереве, коммит/приёмка за автором**
11. (follow-up R3, шаг 2) `index.json`, чистка сироток (R6); затем хвост 4.1/4.4

Регресс сверять по `_examples/.tests` (есть `_base test_.py`, golden-тесты). Каждый шаг —
небольшой, приемка/коммит вручную.
