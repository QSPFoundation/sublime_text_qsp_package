# QspWorkspaceHandlers — актуальная логика (stage 1)

Обработчик жизненного цикла `QspWorkspace` в `QSP.sublime-package/QSP.py` (`class QspWorkspaceHandlers(sublime_plugin.EventListener)`). Реестр/модель — `qSpy.workspace` (`QSP_WORKSPACES`, `for_window/peek_for_window`, см. `../structure.md`).

> Примечание: соседние `*.canvas` и схемы в этой папке частично отражают старый поток (`_get/_extract_qsp_ws`, `qsp-project-workspace.json` в корне проекта) и могут быть неактуальны; за фактическим поведением — сюда и в `structure.md`.

## Ключевые поля/помощники

- `_log_it` / `_log` — отладочный вывод `[QSP WS]`.
- `_markers: Dict[wid, ...]` — per-window маркеры файловых операций (`rename_path`, `delete_files`), чтобы не полагаться на глобальное состояние.
- `_LOCS_DEBOUNCE_MS = 250`, `_locs_gen: Dict[view.id(), gen]` — per-view поколение для дебаунса перескана локаций (отмены таймеров нет; устаревшие колбэки гаснут по поколению, последний чистит запись).
- `_refresh_ws(window)` — восстановление/актуализация WS окна: `for_window` → `load_from_cache()` → `refresh_qsps_files(folders)` → `refresh_from_views(views, folders)`; окно без `window.folders()` пропускается.
- `_flush_ws(window)` — `for_window(window).save_to_cache()` (запись только при identity + `_built`).
- `_cleanup_window(window)` — `_flush_ws` + `sublime.set_timeout_async(prune_orphan_caches, 0)`.

## События

- **`on_init(views)` / `on_load_project_async(window)`** — `_refresh_ws` для каждого/целевого окна (старт, перезагрузка плагина, открытие/переключение проекта). При смене identity окно перепривязывается внутри `for_window` (`rebind` + сброс индекса).
- **`on_load_async(view)`** — если QSP-синтаксис, файл сохранён и лежит в `window.folders()`: `for_window(window).refresh_qsplocs(view, current_qsps)` (учёт локаций открытого файла).
- **`on_post_save_async(view)`** — для сохранённого QSP-файла в папках окна: `refresh_qsplocs(view, path)` + `refresh_qsps_files(folders)` (подхват изменений на диске/переименований) + `refresh_from_views(window.views(), folders)`.
- **`on_modified_async(view)`** — живой индекс локаций (И3): только QSP-вью, инкрементирует поколение вью и планирует `_refresh_qsplocs_debounced(view, gen)` через `set_timeout_async(..., _LOCS_DEBOUNCE_MS)`.
  - **`_refresh_qsplocs_debounced`**: выходит, если поколение устарело или синтаксис/окно/WS отсутствуют; берёт WS через `peek_for_window` (без создания, R5/Д11), пересканирует локации только этого вью `refresh_qsplocs(view, file_name)`.
- **`on_window_command` / `on_post_window_command` / `on_associate_buffer_async`** — отслеживание rename/delete (через `_markers`) с последующим обновлением индекса (перепривязка/перескан) по факту операции.
- **`on_pre_close_project(window)` / `on_pre_close_window(window)`** — `_cleanup_window(window)`: flush кэша v2 (если ведётся) и async-чистка сироток.
- **`on_exit()`** — `flush_workspaces_on_exit(QSP_WORKSPACES)`: **только чистый IO**, без `sublime.*` (Д20–Д22), для надёжного сохранения на выходе из ST.

## Где больше НЕ так

- Нет `_get_qsp_ws`/`_extract_qsp_ws` и ручной работы с `QSP_WORKSPACES` по первой папке — используется `for_window/peek_for_window` по `window.id()` и identity.
- Нет файла `qsp-project-workspace.json` в корне проекта как рабочего кэша — v2 в `<cache_path>/QSP/workspaces/<base>-<hash8>.json`; legacy в `scope[0]` лишь мигрируется в `.bak`.
- Нет глобального `QSP_MARKERS` — маркеры per-window в `_markers`.
- Переменные не обновляются в WS при событиях — сканируются on-demand (`scan_vars`).
