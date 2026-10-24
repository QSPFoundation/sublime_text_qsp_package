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
Файлы подсветки (после реформы):
- `qsp_base.sublime-syntax`        — общая база (hidden, scope `source.qsp.base`)
- `qsp.sublime-syntax`            — формат qsps (visible, scope `source.qsp`)
- `qsp.qsrc.sublime-syntax`       — формат qsrc (visible, scope `source.qsrc.qsp`)
- ~~`qsp_locations.sublime-syntax`~~ — УДАЛЁН (функции разнесены по base + qsrc)

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

## 6. Известные баги/шероховатости

1. [RESH] `scope: iinvalid.illegal.qsp` (опечатка) — УЖЕ исправлена при переносе
   в базу (в `qsp_base` правило запятой operacion_subex = `invalid.illegal.qsp`).
2. [RESH] `kw_operators` рассинхрон (`modobj|resetobj`) — база взята из
   qsp.sublime-syntax, где они есть → qsrc теперь тоже их получает (единый набор).
3. [RESH] `meta.excess_manilines_else` → `meta.excess_multiline_else` — исправлено
   на Шаге 4 в `qsp_base` (контекст `illegal_multiline_else`). Маркер нигде
   в Python-коде не потребляется → переименование безопасно.
4. [RESH] `htmlsupport` комментарий «THanks» — в базе уже «Thanks».
5. [RESH] TODO `qsp.sublime-syntax:16` — снят (реализовано через base+extends).
6. [OPEN] `meta.diff` как фолбэк-комментарий между локациями (TODO автора —
   заменить на `comment.block`). Решить отдельно на Шаге 5.
7. [RESH] Доп. рассинхрон найден на Шаге 4: в старом qsps было `constant.numeric
   avs_numeric;` (мусорная `;`), в qsrc — `avs_numeric`. В базе — единый
   `avs_numeric` (без `;`).

## 6b. Как плагин связан с подсветкой

Текущий Python-код (`qSpy/*`) НЕ читает scope-маркеры подсветки — у него
собственный парсер/конвертер; scope-зависимый `QspAnalyzerCommand` в QSP.py
закомментирован. Значит `avs_*`/`meta.excess_*` — пока «декоративный» слой
(для цветсхем/будущего). Отвественно, но менять их имени безопасно.
Единственная реальная связь плагина с файлами — `QSP.py:195` ссылается на
`Packages/QSP/qsp.sublime-syntax` (имя qsps-файла нельзя менять).

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
- [x] Шаг 3 — создан `qsp.qsrc.sublime-syntax` (extends base, file_extensions qsrc,
      main: qspdocs + statement-правила `#…`/`-…` (avs.locstart/avs.locend) +
      include location_body); старый `qsp_locations.sublime-syntax` УДАЛЁН.
      Ждёт ручной проверки на тестовом `.qsrc` (в репо их нет — создать вручную).
- [x] Шаг 4 — в базе исправлен `manilines→multiline`; проверено, что других
      stray-ошибок нет (`iinvalid`, `;` в avs_numeric, THanks — уже чисто);
      наборы kw_operators/functions/system_vars теперь едины для обоих форматов
      (общий источник = база).
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
