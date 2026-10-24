# CONTEXT — переносимый контекст задачи (подсветка QSP)

> **Как использовать в новом чате:** приложи этот файл и `PLAN.md` и попроси
> «продолжить по плану, шаг N». Окно контекста не нужно — всё важное здесь.
> Последнее обновление: 2026-10-24.

## 1. Что за проект

QSP-пакет для Sublime Text (язык Quest Soft Player, qsp.org). Подсветка
синтаксиса описана YAML-файлами `.sublime-syntax` (version 2). Плагин на Python
(`QSP.py`, `qSpy/`) использует синтаксис как API: по scope-маркерам строит
диагностики, goto-списки локаций/меток, переименования.

Рабочая директория подсветки: `QSP.sublime-package/`.
Файлы подсветки:
- `QSP.sublime-package/qsp.sublime-syntax`
- `QSP.sublime-package/qsp_locations.sublime-syntax`

## 2. Постановка задачи (от пользователя)

Поддерживать ДВЕ группы расширений и переиспользовать общую подсветку:

- **qsps** — `.qsps`, `.qsp-text`, `.text-qsp`. Файл целиком: локации-блоки
  (`# …` … `--`), между локациями игнорируемый текст (подсвечивается как
  комментарий), кроме первой строки `QSP-Game`. Правила qsps/txt2gam.
  Поиск начала локации (`# …`) идёт ТОЛЬКО вне тела локации (в `location_def`
  до `--`); внутри тела `#` новым началом не считается.
- **qsrc** — `.qsrc`. Каждый файл = ОДНА локация: начало локации = начало файла,
  конец локации = конец файла. `main` = весь файл как `include: location_body`.
  `first_line_match` НЕ обязателен; строка `!@ QSP-Game …` — обычный комментарий.
  Если внутри тела встречается строка, похожая на qsps-начало (`#…`) или
  qsps-конец (`-…`), она подсвечивается как САМОСТОЯТЕЛЬНЫЙ statement
  (`avs.locstart`/`avs.locend`), но НЕ открывает/не закрывает блок.

Переиспользование: либо qsps поверх qsrc, либо оба поверх третьей общей.
Общее у обоих — подсветка **кода тела локации**. Разное — **границы локации**
и **текст между локациями**. Делать пошагово, пользователь тестирует вручную.

## 3. Принятые решения

- **Архитектура = Option B: третий общий базовый файл `qsp_base`.** qsps и qsrc
  наследуют его через `extends`. Причина: `main` форматов конфликтует, а общая
  часть (`location_body`) — это «лист», который и выносим в нейтральную базу.
- **Имя `qsp.sublime-syntax` НЕ менять** — на него ссылается плагин
  (`QSP.py:195` `syntax='Packages/QSP/qsp.sublime-syntax'`). Это файл формата qsps.
- `qsp_locations.sublime-syntax` перерабатывается/переименовывается в формат
  qsrc (`qsp.qsrc.sublime-syntax`, scope `source.qsrc.qsp`) — внешних ссылок на
  него нет, переименование безопасно.
- Общая логика живёт в `qsp_base`; правки багов делаем один раз там.

## 4. Инварианты (НЕ нарушать при рефакторинге)

- **`avs_*`-маркеры в scope'ах** — часть API плагина, терять нельзя. Примеры:
  `avs_operators`, `avs_sysvar`, `avs_function`, `avs_numeric`,
  `avs_brace_begin`/`avs_brace_end`, `avs_begin_subexpression`/`avs_end_subexpression`,
  `avs_jumps_labels`, `avs-preprocessor`, `avs.locstart`/`avs.locend`,
  `avs.error`/`avs.wrongelse1`, `avs_wrong_*`, `avs_longstring`, `avs_star`,
  `avs-speccomments`, `avs_illegal_*`, `avs_wrong_type_prefix`, `avs_wrong_numeric`,
  `avs_wrongenter`.
- **Scope-маркеры навигации плагина:** `entity.name.location.qsp`,
  `callable_locs.qsp`, `label_to_jump.qsp`, `entity.name.qlabel.qsp`.
- **Ссылка плагина** на `Packages/QSP/qsp.sublime-syntax` должна оставаться валидной.
- **Корректный компилят YAML/regex**: синтаксис version 2; переменные `{{var}}` —
  текстовые подстановки (per-file, at compile time); правила контекста применяются
  по порядку, первое совпадение выигрывает; `extends` наследует variables+contexts.

## 5. Карта контекстов подсветки (что куда переносить в `qsp_base`)

ОБЩЕЕ (в `qsp_base`): `location_body`, `figure_brace`, `multiline_actions`,
`multiline_conditions`, `multiline_loop`, `multiline_actions_else`,
`illegal_multiline_else`, `multiline_actions_elseif`, `kw_declarations`,
`sugargosub`, `sugarfunc`, `wrong_end_else_elseif`, `wrongclose`,
`wrong_close_in_brace`, `users_variables`, `jump_to_label`, `location_call`,
`operacion`, `numeric`, `operators`, `system_variables`, `functions`, `labels`,
`strings`, `subexpression`, `subex`, `operacion_subex`, `comments`,
`comment_after_colon`, `brace_comments`, `illegal_closed_brace`,
`quote_apostroph_comments`, `special_comments`, `preprocessor`, `qspdocs`,
`htmlsupport`, `separator_continuation`. + все общие `variables`.

ТОЛЬКО qsps (остаётся в `qsp.sublime-syntax`): `main`, `diff`, `location_def`
(блок `# … --`), `qspgame_header`.

ТОЛЬКО qsrc (в `qsp.qsrc.sublime-syntax`): свой `main` — весь файл =
`include: location_body`; плюс два statement-правила для `#…`/`-…`
(`avs.locstart`/`avs.locend`), НЕ пушащие блок. Без header/first_line_match.

## 6. Известные баги/шероховатости (к исправлению на Шаге 4)

1. `scope: iinvalid.illegal.qsp` — лишняя `i`. Места: `qsp.sublime-syntax:642`,
   `qsp_locations.sublime-syntax:605` (оба в `operacion_subex`, правило запятой).
2. `kw_operators` рассинхрон: в `qsp.sublime-syntax:26` есть `modobj|resetobj`,
   в `qsp_locations.sublime-syntax:20` — нет.
3. `meta.excess_manilines_else` — опечатка (manilines → multiline).
4. `htmlsupport` комментарий «THanks» — косметика.
5. TODO `qsp.sublime-syntax:16` (про вынос в qsp_locations) — снять после рефакторинга.
6. `meta.diff` используется как фолбэк-комментарий между локациями (TODO автора —
   заменить на `comment.block` когда появятся сниппеты). Решить отдельно.

## 7. Статус выполнения

- [x] Изучены оба файла, найдены связи с плагином.
- [x] Согласована архитектура (Option B) и составлены PLAN.md / CONTEXT.md.
- [x] Шаг 0 — зафиксировать эталон подсветки вручную (пользователь тестирует).
- [x] Шаг 1 — создан `qsp_base.sublime-syntax` (hidden, scope `source.qsp.base`);
      общие variables + общие контексты тела локации (verbatim из qsp.sublime-syntax,
      поведение пока не меняем). На него ещё никто не ссылается.
- [x] Шаг 2 — `qsp.sublime-syntax` переведён на `extends: qsp_base.sublime-syntax`;
      всё общее удалено, локально остались main/diff/location_def/qspgame_header;
      file_extensions приведены к `qsps, qsp-text, text-qsp` (794→~60 строк).
      Ждёт ручной проверки: qsps должен выглядеть как прежде.
      (TODO со строки 16 про вынос в qsp_locations — снят автоматически.)
- [ ] Шаг 3 — сделан qsrc-синтаксис.
- [ ] Шаг 4 — исправлены баги рассинхрона.
- [ ] Шаг 5 — зачистка TODO/маркеров.

## 8. Материалы для тестов

- Примеры qsps: `_examples/` (например `example_preprocessor/*.qsps`,
  `examples_splitter/*.qsps`, `examples_qsps_to_qsp/*.qsps`).
- Тест-файл синтаксиса: `QSP.sublime-package/syntax_test_qsp.qsps`.
- Примеров `.qsrc` в репо пока нет — для ручного теста qsrc создать вручную
  файл-локацию (начало `#имя`, тело кода, при необходимости конец-маркер).

## 9. Правила общения/кода (из памяти пользователя)

- Общение на русском.
- Пояснять, что и почему меняется в коде.
