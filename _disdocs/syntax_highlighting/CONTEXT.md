# CONTEXT — переносимый контекст задачи (подсветка QSP)

> По реструктуризации (REFACTOR_PLAN): Фазы 1–5 сделаны (кроме ручного
> п.4.3 — скриншоты). Рефакторинг фактически завершён; для продолжения
> остаётся только ручная визуальная сверка. Приложи `REFACTOR_PLAN.md`.
> Последнее обновление: 2026-10-26.

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

- **`avs_*`-маркеры в scope'ах** — часть API плагина, терять нельзя. Стиль —
  ЕДИНЫЙ, нижнее подчёркивание (Фаза 4, п.4.1: `avs.`/`avs-` → `avs_`). Примеры:
  `avs_statements`, `avs_sysvar`, `avs_function`, `avs_numeric`,
  `avs_brace_begin`/`avs_brace_end`, `avs_begin_subexpression`/`avs_end_subexpression`,
  `avs_jumps_labels`, `avs_preprocessor`, `avs_locstart`/`avs_locend`,
  `avs_error`/`avs_wrongelse1`, `avs_wrong_*`, `avs_longstring`, `avs_star`,
  `avs_speccomments`, `avs_illegal_*`, `avs_wrong_type_prefix`, `avs_wrong_numeric`,
  `avs_wrongenter`.
- **Scope-маркеры навигации плагина:** `entity.name.location.qsp`,
  `callable_locs.qsp`, `label_to_jump.qsp`, `entity.name.qlabel.qsp`.
- **Ссылка плагина** на `Packages/QSP/qsp.sublime-syntax` должна оставаться валидной.
- **Корректный компилят YAML/regex**: синтаксис version 2; переменные `{{var}}` —
  текстовые подстановки (per-file, at compile time); правила контекста применяются
  по порядку, первое совпадение выигрывает; `extends` наследует variables+contexts.

## 5. Карта контекстов подсветки (что куда переносить в `qsp_base`)

ОБЩЕЕ (в `qsp_base`, актуальный список — синхронизирован с кодом при
реструктуризации, Фаза 1; контекста `operators` в коде никогда не было —
операторы живут в `operacion`/`operacion_subex`; `illegal_closed_brace` удалён
по итогам Шага 9):
`location_body`, `figure_brace`,
`brackets_multiline`/`multiline_round`/`multiline_square`/`continuation_tail`
(многострочные `( )` и `[ ]` + валидный хвост-оператор на переносе), `multiline_actions`,
`multiline_conditions`, `multiline_loop`, `multiline_actions_else`,
`illegal_multiline_else`, `multiline_actions_elseif`, `kw_declarations`,
`sugargosub`, `sugarfunc`, `wrong_end_else_elseif`, `wrongclose`,
`wrong_close_in_brace`, `users_variables`, `jump_to_label`, `location_call`,
`operacion`, `numeric`, `statements`, `system_variables`, `functions`, `labels`,
`strings`, `subexpression`, `subex`, `operacion_subex`, `comments`,
`comment_after_colon`, `comment_after_end_in_brace` (plain `comment_after_end`
удалён в Фазе 3 по Решению-1A — все `end` ведут brace-aware),
`comment_tail_common` (общий хвост comments/comments_in_brace, Фаза 3),
`brace_comments`,
`quote_apostroph_comments`, `special_comments`, `preprocessor`, `qspdocs`,
`htmlsupport`, `separator_continuation`. + все общие `variables`.

BRACED-слой (Шаг 9, тоже в `qsp_base`) — зеркало тела для кода ВНУТРИ
открытого `{…}`: `location_body_braced`, `comments_in_brace`,
`multiline_actions_braced`, `multiline_loop_braced`, `multiline_conditions_braced`,
`multiline_actions_else_braced`, `multiline_actions_elseif_braced`. `figure_brace`
теперь пушит `location_body_braced` (а не `location_body`).

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
6. [OPEN] Раскрасить «игнорируемый текст между локациями» как комментарий —
   НЕ решается простой заменой `meta.diff`→`comment.block`. Решение A ПРОВАЛЕНО
   и откачено: Sublime подавляет tab-триггеры сниппетов в `comment.*`/`string.*`
   scope, ДАЖЕ если якорь `meta.gametext.qsp` присутствует. Сейчас снова рабочее
   `meta.diff meta.gametext.qsp`. Оставшиеся варианты:
     - A2: оставить meta-токен (не comment) и стилизовать его как комментарий
           через color-scheme пользователя (сниппеты целы);
     - B : вызывать сниппет новой локации явным keybinding'ом (insert_snippet
           работает и в comment-scope) — тогда comment.block допустим, но
           теряется триггер по набору `# `/`newloc`;
     - C : оставить как есть (`meta.diff`).
   Требует решения пользователя.
7. [RESH] Доп. рассинхрон найден на Шаге 4: в старом qsps было `constant.numeric
   avs_numeric;` (мусорная `;`), в qsrc — `avs_numeric`. В базе — единый
   `avs_numeric` (без `;`).

## 6b. Как плагин связан с подсветкой

Основной Python-код (`qSpy/*`) имеет собственный парсер/конвертер и в целом НЕ
полагается на scope-маркеры; scope-зависимый `QspAnalyzerCommand` в QSP.py
закомментирован. НО: `qSpy/workspace.py` (поиск границы конструкции, `sprtr`)
реально читает несколько scope'ов — `keyword.operator.one-sign.qsp`,
`keyword.control.qsp` и `avs_brace_end`. Поэтому эти имена менять нельзя.
Остальные `avs_*`/`meta.excess_*` — «декоративный» слой (цветсхемы/будущее);
именно они и переименованы в Фазе 4 (п.4.1) к единому `_`-стилю — grep по
`*.py` подтвердил, что ни один из затронутых маркеров (`avs_error`,
`avs_wrongelse1`, `avs_function`, `avs_speccomments`, `avs_preprocessor`,
`avs_locstart`/`avs_locend`) плагин не потребляет. Реальная связь плагина с
файлами — `QSP.py:195` ссылается на `Packages/QSP/qsp.sublime-syntax`
(имя qsps-файла нельзя менять).

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
- [x] Шаг 6 — `end` больше НЕ двойное ключевое слово: убраны `end act`/`end loop`/`end if`
      (в 6 правилах `qsp_base` и в переменной `elseif_else_final`). Поддерживается
      только `end`; весь текст после него — комментарий, который прерывается на `&`
      (но не внутри `{}`, кавычек и апострофов) или конце строки; многострочность —
      через вложенные `{...}`-области. Реализовано контекстами `comment_after_end`
      (блочная форма) и `comment_after_end_in_brace` (форма внутри `{...}`: `}`
      завершает и комментарий, и блок). Правило `end` теперь делает `pop+push`.
      Обновлён `syntax_test_qsp.qsps` (лок «фигурные скобки действия условия»).
- [x] Шаг 7 — поддержка многострочного кода внутри `( )` и `[ ]` (её не было:
      перенесённые строки ложно помечались «нет левого операнда», скобки не
      группировались). Новые контексты в базе: `brackets_multiline` (push только
      если на строке нет парного закрывания вне строковых литералов —
      сбалансированные в одной строке скобки живут прежними правилами),
      `multiline_round`/`multiline_square` (закрытие, guard `^\s+(?=[+\-*\/<>=,&])`
      против ложных `(^...)\K`-проверок, рекурсия, location_body). Новые маркеры:
      `avs_paren_begin/end`, `avs_bracket_begin/end`, `meta.group.*.multiline`,
      `meta.continuation.expression`. Переменная `nr_lookahead`. тесты:
      syntax_test_qsp.qsps (лок «многострочные скобки») + sample_location.qsrc.
- [x] Шаг 8 — фикс ложных «нет правого операнда» внутри многострочных скобок:
      Sublime матчит правила только в границах текущей строки, поэтому
      `(?!\s*?{{right_operand}})` не видит операнд на следующей строке и красит
      `+`/`,`/`<>`/`and` в конце строки. Новый контекст `continuation_tail`
      (оператор/запятая + только пробелы до конца строки → валидный оператор)
      подключён РАНЬШЕ location_body в multiline_round/multiline_square/figure_brace.
      Вне многострочных скобок поведение не изменилось.
- [x] Шаг 9 — brace-aware `{…}` (реструктуризация подсветки фигурных скобок).
      Модель: `{…}` — не «незакрываемый блок», а запись строки; закрывающая `}`
      — это первая `}` нулевого уровня вложенности, а `}`, спрятанная в
      строковом литерале (`"…"`/`'…'`) или во вложенных `{…}` внутри
      `!`-комментария (через `brace_comments`), блок НЕ закрывает. Реализовано
      отдельным braced-слоем в базе (наследуют оба формата — qsps и qsrc):
      `location_body_braced` + `comments_in_brace` + braced-двойники
      `multiline_actions/loop/conditions/else/elseif`; `figure_brace` пушит
      `location_body_braced`. `comments_in_brace` схлопывается НУЛЕВЫМ
      `(?=\})` (не поглощая `}`) — скобку тогда ловит `\}`-поп `figure_brace`.
      Верхний уровень НЕ тронут: обычный `comments` с `illegal_closed_brace`
      (одиночная `}` вне `{…}` остаётся ошибкой). `end` внутри блока →
      `comment_after_end_in_brace` (уже было) — `}` после end-комментария
      закрывает блок. Тесты: новый лок «скобки и комментарии» в
      `syntax_test_qsp.qsps` + секция в `sample_location.qsrc`. YAML-парс и
      резолв всех `include/push` — чистые. Осталась известная мелкая
      граничная ниша: `}` на строке-комментарии ВНУТРИ незакрытого act/if/else
      (вложенного в `{…}`) по-прежнему ловится `wrong_close_in_brace` как
      ошибка — это согласовано с «незакрытая конструкция» семантикой.
      Дополнение: убрана подсветка одиночной «}» в комментариях как ошибки
      (`illegal_closed_brace`/`open_brace_dont_exist`) — контекст удалён за
      ненадобностью (braced-слой сам различает «}»-закрытие блока и защищает
      `}` в кавычках/вложенных {…}); обычный `comments` теперь просто ведёт
      `}` до конца строки как текст комментария.
- [ ] Шаг 5 — зачистка: цель «comment.block для между-локационного текста»
      НЕ достигнута (решение A сломало tab-триггеры сниппетов — см. §6.п6).
      Откачено к `meta.diff`. Открытый выбор: A2 (color-scheme) / B (keybinding)
      / C (как есть). Остальная зачистка (manilines и прочее) уже в Шаге 4.

**Реструктуризация (REFACTOR_PLAN.md):**

- [x] Фаза 1 (расчистка) — выполнена 2026-10-25: удалены мёртвые `variables`
      (`opener`/`closer`/`braces_open`/`braces_close`; `quote`/`ap` остались —
      используются в operand-переменных); подчищены whitespace-only строки
      (7 в базе, 4 в тест-фикстуре); §5 карты выше приведён к фактическому
      списку из 50 контекстов базы; контроль прогнан скриптом
      `_disdocs/syntax_highlighting/check_syntax_phase1.py` — PASS
      (YAML-load + резолв include/push + баланс скобок + переменные;
      переиспользуется после каждой фазы). Поведение подсветки не менялось —
      ручная проверка не требовалась, но не вредна.
- [x] Фаза 2 (сжатие дублей) — выполнена 2026-10-25. Контроль-скрипт PASS
      (в базе стало 54 контекста: +body_common_head/_mid/_tail +string_common).
      2.1: arms `(?<=\{)X`+`^X` слиты через не-захват. альтернацию якорей
      `(?:^|(?<=\{))` (branch-reset `(?|…)` НЕ работает — Onigmo Sublime даёт
      "undefined group option"); actions/loop/conditions 2→1,
      elseif 4→2, else 6→5 (две формы после двоеточия оставлены раздельно).
      2.2: string_common. 2.3: body_common_head/_mid/_tail (общие сегменты
      двух location_body). 2.4: operacion/operacion_subex НЕ слиты (5 реальных
      поведенческих различий), TODO закрыт комментарием.
      ⚠ ВНИМАНИЕ: 2.1 вынужденно применил Решение-1 (§3) — top-level
      `act/loop/if` теперь тоже ведут `comment_after_end_in_brace`; отличие
      от прежнего поведения проявляется лишь на редком `… end текст }`.
      Ждёт ручной проверки подсветки + подтверждения Решения-1.

- [x] Фаза 3 (модель end/brace) — выполнена 2026-10-26, ручная сверка
      пройдена успешно: вынесен `comment_tail_common` (4 копии тела
      comments/comments_in_brace убраны; arms НЕ слиты — альтернация якорей
      ^/\& ложно расширила бы позиции); мёртвый `comment_after_end` удалён
      (Решение-1A зафиксировано в коде); порядок wrongclose/wrong_close_in_brace
      задокументирован инвариантом. Контроль PASS.
- [x] Фаза 5 (защита braced-двойников) — выполнена 2026-10-26:
      5.1 — автотест парности в `check_syntax_phase1.py` (срез суффикса
      `_braced` + посериализованная сверка 5 пар; расхождение → FAIL; ловушка
      self-tested); комментарий-инвариант над braced-секцией обновлён.
      5.2 — автогенерация build-скриптом ОЦЕНЕНА и ОТВЕРГНУТА (Решение-3B:
      автотест снимает риск дрейфа дешевле второго источника правды).
      Контроль PASS. Поведение подсветки в Фазе 5 НЕ менялось — ручная
      проверка не требовалась.
- [x] Фаза 4 (гигиена имён) — п.4.1/4.2 выполнены 2026-10-26: все `avs`-маркеры
      сведены к единому `_`-стилю (`avs.`/`avs-` → `avs_`; затронуты база и qsrc,
      всего 8 уникальных имён). `avs.function` слился с `avs_function`. Суффикс
      `.qsp` не трогали (Решение-2A). Grep: consumed-плагином маркеров среди
      переименованных нет (только `avs_brace_end` в workspace.py — не менялся).
      readme фикстуры + CONTEXT §4/§6b синхронизированы. Контроль PASS.
      4.3 (скриншоты до/после) — ждёт ручного рендера в Sublime. Явных изменений
      matching нет (только имена scope'ов), но цвет `avs`-маркеров в схемы
      проверяется визуально.

## 7b. Открытые решения (спросить пользователя в новом чате; статус на 2026-10-26)

> Фазы 1–3 и 5 REFACTOR_PLAN сделаны (Фаза 3 вручную сверена — OK). Осталась
> только опциональная Фаза 4 (гигиена имён): по суффиксу `.qsp` Решение-2A уже
> отменила её основную часть; остаётся п.4.1 (единый стиль `avs_*`-маркера) —
> отдельное решение, визуальный риск. Каждый пункт ниже: что решается /
> варианты / что стоит по умолчанию.
>
> Фазы 1–5 REFACTOR_PLAN сделаны (Фаза 3 вручную сверена — OK; Фазу 4 п.4.1/4.2
> выполнено, 4.3 — скриншоты — ждёт ручного рендера). Открытых решений по
> реструктуризации НЕ осталось: все выборы (§7b) сделаны и реализованы.
> Вне REFACTOR_PLAN открыт только Шаг 5 (цвет текста между локациями в qsps,
> см. §6.п6 / Решение-5 — отложено сознательно).
>
> **Статус решений (обновлено 2026-10-26):**
> Решение-1 — ПРИНЯТО 1A: оставляем унификацию end-модели (top-level и braced
>   `act/loop/if/else/elseif` ведут единый `comment_after_end_in_brace`). Де-факто
>   уже в коде с Фазы 2.1 — подтверждено, откат не нужен.
> Решение-2 — ПРИНЯТО 2A: суффикс `.qsp` НЕ трогаем (Фаза 4 по суффиксу не делается).
> Решение-3 — ПРИНЯТО 3B: сжимать braced-двойники общими сегментами до минимума
>   (часть двойников неизбежна — Sublime не параметризует include). ИСПОЛНЕНИЕ —
>   часть в Фазе 2/3 (end-хвосты едины, comment_tail_common); оценка
>   автогенерации (5.2) — впереди (Фаза 5).
> Решение-4 — ПРИНЯТО 4B: `operacion`/`operacion_subex` слиты через общие сегменты (сделано 2026-10-25).
> Решение-5 — ОТЛОЖЕНО: цвет «текста между локациями» (`meta.diff`) пока не трогаем.

- **Решение-1 — end-модель (де-факто уже применён в Фазе 2.1, нужен «ок/откат».)**
  Склейка arms заставила выбрать один end-tail; top-level `act/loop/if/else/elseif`
  теперь ведут единый `comment_after_end_in_brace`.
  - 1A ✔ ПРИНЯТО (2026-10-26) (= текущий код): оставить унификацию. Цена —
    меняется редкий top-level `… end текст }` (`}` теперь завершает комментарий).
  - 1B: откатить к отдельному `comment_after_end` для `^`-форм → тогда
    `multiline_actions/loop/conditions` нельзя слить в 1 arm (сжатие 2.1 для них теряет смысл).

- **Решение-2 — суффикс `.qsp` у scope'ов (Фаза 4, ещё не трогали).**
  - 2A (рекомендую): оставить общесхемные (`constant.numeric`, `meta.block`,
    `markup.raw`, …) без `.qsp` — не трогать цветовые схемы.
  - 2B: унифицировать всё с `.qsp` — риск задеть user color-scheme; protected-
    маркеры плагина (CONTEXT §4) трогать нельзя.

- **Решение-3 — судьба braced-двойников (Фаза 3/5).**
  - 3A: держать как есть + синхрон-контракт (комментарий/тест парности).
  - 3B ✔ ПРИНЯТО (2026-10-26, исполнение впереди; частично сделан в Фазе 2):
    сжать до минимума общими сегментами; часть двойников неизбежна (Sublime не
    параметризует include).
  - 3C: генерировать `*_braced` build-скриптом из plain — нет ручных дублей, но
    шаг сборки + второй источник правды.

- **Решение-4 — `operacion` vs `operacion_subex` — ПРИНЯТО 4B, ИСПОЛНЕНО 2026-10-25.**
  Слиты только построчно идентичные сегменты (`operacion_word_two_signs_common`,
  `operacion_ampersand_common`); различающиеся группы (`one_sign`, `comma`, `no`)
  оставлены локально — подсветка сохранена 1:1, контроль PASS (база 54→56).

- **Решение-5 — Шаг 5 (вне REFACTOR_PLAN, но открыт): раскраска «текста между
  локациями» в qsps (`meta.diff`).** Требует выбора пользователя (см. §6.п6).
  - A2: color-scheme для meta-токена; B: явный keybinding сниппета новой локации
    (тогда допустим comment.block); C (по умолчанию): оставить `meta.diff`.

## 8. Материалы для тестов

- Примеры qsps: `_examples/` (например `example_preprocessor/*.qsps`,
  `examples_splitter/*.qsps`, `examples_qsps_to_qsp/*.qsps`).
- Тест-файл синтаксиса: `QSP.sublime-package/syntax_test_qsp.qsps`.
- Примеров `.qsrc` в репо пока нет — для ручного теста qsrc создать вручную
  файл-локацию (начало `#имя`, тело кода, при необходимости конец-маркер).
- **qsrc-фикстура (создана):** `_examples/example_syntax_qsrc/sample_location.qsrc`
  (+ `readme.md` рядом) — покрывает scope'ы тела локации и частные
  statement-случаи `#…`/`-…`. Использовать для ручной проверки после правок.

## 9. Правила общения/кода (из памяти пользователя)

- Общение на русском.
- Пояснять, что и почему меняется в коде.
