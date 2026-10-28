# HANDOFF — контекст сессии refactor/fix подсветки QSP

> Переезжаемый документ. В новом чате: «читай `_disdocs/syntax_highlighting/HANDOFF.md`,
> продолжаем с шага <N>». Он дополняет (не заменяет) память Qoder — там уже лежат
> дискретные решения (см. §5).

**Дата:** 2026-10-28 · **Ветка:** `master` · **Гит-состояние:** шаги 1–3 + фиксы `else`
**закоммичены** (HEAD `331d035` = `dsf ref(syntax): fix newline between else and if`; до него
`d4acde5` = `dsf ref(syntax): hygienic of rules and comments`, `439584d` = `deepseek-flash
fix(syntax): comments after else without :`).
На диске НЕ закоммичен **фикс 1j** (мёртвый регион однострочных `else`/`elseif` = многострочный
комментарий той же структуры, что и обычные комментарии): `qsp_base.sublime-syntax` (общие состояния
`comment_in_quote/_apostroph/_brace` + `dead_code_comment`), `check_syntax_phase1.py` (PAIRS+2),
`syntax_test_qsp.qsps`, этот файл; плюс правки пользователя в
`_examples/example_syntax/conditionals/multilines_conditional.qsps`.
Внешний файл `_disdocs/syntax_highlighting/qsp_grammar.peg` — **РЕШЕНО (2026-10-28): не коммитим.**
Грамматика живёт в другом репозитории и обновляется там; сюда подтягивается **вручную**,
в этом репо не версионируется → добавлена в `.gitignore` (в `git status` больше не висит).
Автоматизация синхронизации не сделана (грамматика давно стабильна — сборка не зависит). ПЕРЕД продолжением выполни `git status`/`git diff` и, если пусто из-за сбоя
вывода PowerShell, — `git add -A; git status` (терминал в этой сессии искажал вывод
`git diff`; содержимое файлов на диске подтверждено чтением).

---

## 0. О каких файлах речь
- `QSP.sublime-package/qsp_base.sublime-syntax` — общая база подсветки тела локации (hidden, `extends`-родитель).
- `QSP.sublime-package/qsp.sublime-syntax` — формат `qsps` (блоки `# … --`).
- `QSP.sublime-package/qsp.qsrc.sublime-syntax` — формат `qsrc` (1 файл = 1 локация).
- `QSP.sublime-package/syntax_test_qsp.qsps` — фикстура-ассерты (1-я строка `// SYNTAX TEST "Packages/QSP/qsp.sublime-syntax"`).
- `_disdocs/syntax_highlighting/refactoring_review.md` — план аудита/рефакторинга (создан в этой сессии).
- `_disdocs/syntax_highlighting/qsp_grammar.peg` — **внешний** справочный файл (источник истины по
  грамматике QSP): не коммитится (в `.gitignore`), подтягивается вручную из другого репозитория.
- Контроль: `python _disdocs/syntax_highlighting/check_syntax_phase1.py` → ожид `RESULT: PASS`.

---

## 1. ЧТО СДЕЛАНО (на диске, подтверждено)

### 1a. Шаг 1 рефакторинга (P1.1) — поведение НЕЙТРАЛЬНО (1:1)
В `qsp_base` блок `variables:` дополнен переменными — побайтовые копии ранее инлайн-фрагментов:
`arm_anchor`, `kw_act`, `kw_if`, `kw_elseif`, `kw_loop`, `loop_strict_head`, `loop_no_while`,
`pend_block_strict` (`(?=:\s*?(!.*)?$)`), `pend_block_soft` (`(?=:\s*?(!.*?)?$)`), `pend_inline`,
`act_strict_tail`, `if_strict_tail`, `else_caret_tail`, `else_brace_tail`,
`elseif_strict_tail`, `elseif_permissive_tail`.
Заменено ~40 `match`-правил в plain- и braced-контекстах (правки зеркальные).
**Не тронуты (разные якоря/структура):** `wrong_end_else_elseif`, `illegal_multiline_else`,
«голый» else-arm (449), else-caret-arm (451/462), arm5 `else (?=\s*$)`.
**Отложено:** P1.7 нормализация `\s*?` → `\s*` (не делать в 1-м шаге, чтобы правка осталась 1:1).

### 1b. ФИКС БАГА — многострочный `else` без `:` красил тело как комментарий ✅
- **Корень:** в `multiline_actions_else` arm «else <текст>» имел **опциональное** `(:?)` и стоял
  раньше bare-arm'а → легальный «голый» `else` захватывался им и пушил контекст с catch-all
  `^.* → comment.qsp`, перекрашивавшим **все строки тела до `end`**.
- **Фикс:** `(:?)` → `(:)` (двоеточие обязательно). Голый `else` и `else !коммент` теперь
  проваливаются к нижнему bare-arm'у (`multiline_actions_else`, последний arm, push location_body).
- **Место:** `qsp_base.sublime-syntax` — контекст `multiline_actions_else` (arm с `(:)`, ~стр. 479)
  и **зеркало** `multiline_actions_else_braced` (~стр. 725). Правка зеркальная (parity-контракт §5.1).
- **Симуляция regex подтвердила:** `arm4-new | bare else: False | else: 4: True`; `arm5 bare: True`.
- **Регресс-ассерты** добавлены в `syntax_test_qsp.qsps` (перед секцией `# st.help`):
  ```
  if 1:
  <TAB>567
  else
  <TAB>$lvar=2
  end
  //  <- keyword.control.conditional.else.qsp
  //      ^ meta.user-variables.qsp -comment.qsp
  ```

**Контроль после обеих правок:** `check_syntax_phase1.py` → **PASS** (YAML/brace/vars/pairing OK, 14 пар).

### 1d. ФИКС РЕГРЕССА 1b — однострочный `else <statements>` без `:` стал invalid ✅ (2026-10-28)
- **Симптом (обнаружен в `_examples/example_syntax/conditionals/multilines_conditional.qsps`):**
  `else *pl '0'` (else + текст, **без** `:`) подсвечивался `invalid` (meta.excess_else),
  хотя `else: *pl '0'` — валидный keyword.control.
- **Корень:** фикс 1b сделал `:` обязательным в arm4 → пропали **все** не-колонные формы
  `else`. По `qsp_grammar.peg` (elseClause/elseSingleLine/elseMultiLine, стр. 112–115) двоеточие
  **факультативно** `(":" ws)?`: легальны `else`(голый), `else !коммент` (многострочные) И
  `else <statements>` (однострочный). Ни один arm их больше не ловил → fallthrough в
  `wrong_end_else_elseif` → invalid. Утверждение 1b «голый else и else !коммент доходят до
  bare-arm» было ВЕРНЫМ лишь для голого `else` (bare-arm был `(?=\s*$)`).
- **Фикс:** расширен НИЖНИЙ bare-arm `multiline_actions_else` (arm5): `(?=\s*$)` → `(?=\s|$)`
  + **зеркало** `multiline_actions_else_braced`. Теперь arm5 ловит все не-колонные формы; пушит
  тот же код-фрейм (`else_body_head_bare` + `else_body_guarded_tail` + `location_body[_braced]`) —
  БЕЗ catch-all `^.*→comment`, поэтому регресс 1b (тело=комментарий) НЕ возвращается.
  Колонные формы (`else:`, `else: <текст>`, `else <конд>:`) по-прежнему раньше (arm2/arm4/arm1).
- **Регресс-покрытие:** добавлен КОД внутрь локации `# st.death` в `syntax_test_qsp.qsps`
  (однострочный `else *pl '0'` + многострочный `else` с телом). ВАЖНОЕ открытие: регион между
  `--` и `#` — это `meta.gametext` (catch-all `.*` в `qsp.sublime-syntax#diff`), НЕ код →
  прежние `//`-ассерты 1b (перед `# st.help`) реально ничего не проверяли; в qsp комментарий
  — `!` (не `//`), так что фикстура = ВИЗУАЛЬНЫЙ корпус, финальный судья — Sublime (§2).

**Контроль после 1c+1d:** `check_syntax_phase1.py` → **PASS** (local=81, pairing 14 пар).

### 1e. УТОЧНЕНИЕ к 1d — не-колонный `else` делится на block/single (после коммита 1d)
- **Симптом:** фикс 1d объединил ВСЕ не-колонные формы в один bare-arm (arm5, код-тело).
  Но `else *pl '5'` / `else & !коммент` (однострочные: stmt-хвост на своей строке) красили
  последующие строки КОДОМ, тогда как колонная однострочная `else: <stmt>` красит их
  КОММЕНТАРИЕМ (мёртвый код до `end`). Пользователь: `multilines_conditional.qsps` 127–173.
- **Правило:** различаем не «есть/нет `:`», а «однострочный (есть stmt-хвост) / многострочный
  (голый или только `!коммент`)». Колонное разделение arm2(block)/arm4(single) перенесено на
  не-колонные формы.
- **arm5 (block, КОД-тело):** `^(\s*?)(else)(?=[ \t]*(!.*?)?$)` — голый `else` и `else !коммент`;
  тело со след. строки = код (откат 1b не возвращается: нет catch-all `^.*`).
- **arm6 (single, КОММЕНТАРИЙ-тело):** `(?:^|(?<=\{))(\s*?)(else)[ \t]+(?=[^!\s])` — зеркало arm4
  без colon-части. `[ \t]+` — ГОРИЗОНТАЛЬНЫЙ пробел (НЕ `\s`: иначе `\n` через перенос ложно
  ловил голый многострочный `else`); lookahead `[^!\s]` — хвост начинается не с `!`. Пушит кадр
  arm4: head_bare + `^.*`→comment + guarded_tail + location_body[_braced]. Обе правки — plain+braced.
- Regex-симулятор порядка arm'ов (11 кейсов) → все OK. `check_syntax_phase1.py` → **PASS**, 14 пар.
  Fixture `syntax_test_qsp.qsps` (# st.death) обновлён: однострочный `else *pl` + мёртвая строка
  (коммент) и многострочный `else` + код-тело.

### 1f. БАГ — комментарий после `else` без ':' (исправлен в 1g, 2026-10-28) ✅
- **Симптом:** `else !коммент` (без ':' и без '&') — `!` после else подсвечивается как
  оператор one-sign (NOT), а не как открытие комментария (`multilines_conditional.qsps` 127–142).
- **МЕХАНИЗМ комментария после заголовка (важно для будущего фикса):**
  `comment_after_colon` завязан на lookbehind `(?<=:)` → красит `!…` как комментарий
  ТОЛЬКО ПОСЛЕ двоеточия. `if`/`act`/`loop`/`elseif` обязательны с ':' (их `*_body`
  включают comment_after_colon в начале), поэтому «после заголовка» = «после ':'».
  У `else` ':' факультативен → без него lookbehind не срабатывает. Контекст `comments`
  ловит `!` как комментарий лишь на начале строки (`^\s*!`) или после `&` (`\&\s*!`),
  причём `\&`-ветка в ЛЮБОЙ позиции и поддерживает МНОГОСТРОЧНОСТЬ (продолжение `&`).
- **Почему ОТКАТАН вариант фикса:** arm5 разбивался на arm5-comment (`^(else)([ \t]+)(!)([^\n\r]*)$
  с captures `!`→comment punct, остаток→comment.qsp) + arm5-bare. Но match с `[^\n\r]*$`
  ЖЁСТКО ограничивает комментарий ОДНОЙ строкой → НЕ поддерживает `&`-многострочность
  (пользователь заметил без рендера). Откатано к единому arm5 `(?=[ \t]*(!.*?)?$)` (после 1e).
- **Что нужно вместо этого:** решение задействует механизм comment-контекста
  (push-мини-контекст с `comment_tail_common`-подобным телом, а НЕ потребление в match),
  НО якорится на позицию СРАЗУ после else, чтобы не задеть оператор `!` в теле (`x = !y`).
  Реализовано как arm5a — см. **1g**.
- Контроль после откатa: `check_syntax_phase1.py` → PASS, 14 пар.

### 1g. ФИКС 1f — новый arm `else !коммент` (2026-10-28) ✅
- **Корень (коротко):** `!` после `else` — это `elseMultiLine` + `commentStatement`;
  `comment_after_colon` завязан на lookbehind `(?<=:)`, а `comments` видит `!` только
  в `^\s*!`/`\&\s*!` → `else !коммент` падал в `operacion_one_sign` (NOT).
- **Решение (хвост НЕ потребляется):** в `multiline_actions_else` **перед** bare-arm
  добавлен arm `^(\s*?)(?i:(\belse\b))[ \t]+(!)` — в match берётся `else` + пробелы +
  ТОЛЬКО открывающий `!` (capture → `punctuation.definition.comment.begin.qsp
  main_comment_start.qsp`), а тело живёт в НОВОМ общем контексте `comment_after_else`
  (pop по newline; внутри `quote_apostroph_comments`/`brace_comments`/`special_comments`,
  т.е. `"…"`/`'…'`/`{…}`/`'@'` — как после ':'). `meta_content_scope` (НЕ `meta_scope`),
  чтобы scope комментария не накрывал сам `else`; поэтому сам `!` берёт `comment.qsp`
  из capture (`3: comment.qsp punctuation.definition.comment.begin.qsp main_comment_start.qsp`)
  — итоговый набор scope ровно как у `comment_after_colon`.
- **Стек:** `push: [else_body_block, comment_after_else]` — правый контекст верхний
  (ST docs: «rightmost … becomes the topmost»), поэтому после pop'а комментария по
  newline верхним становится ТЕЛО else: новый именованный `else_body_block` =
  head_bare + guarded_tail + `location_body` (зеркало `else_body_block_braced`;
  добавлено в PAIRS чекера).
- **Почему НЕ lookbehind-правило в голове тела:** правило живёт до `end`, и `(?<=\belse)`
  ложно срабатывало бы на `'else !…'` внутри строкового литерала. Line-anchor + потребление
  только `!` — точная фиксация «сразу после else»; NOT в теле (`x = !y`, `$lvar = !0`) не задет.
- **Bare-arm сужен:** `(?=[ \t]*(!.*?)?$)` → `(?=[ \t]*$)` (хвост-комментарий теперь выше).
- **Покрытие:** `syntax_test_qsp.qsps` (# st.death) — plain-блок `else !коммент` +
  `$lvar = !0` (NOT в теле) и braced-блок в `{…}`; аннотации в
  `_examples/example_syntax/conditionals/multilines_conditional.qsps` 138–142 обновлены.
- **Контроль:** `check_syntax_phase1.py` → **PASS** (local=84, pairing **15** пар).

### 1h. Шаг 3 рефакторинга (P1.6) + гигиена — поведение НЕЙТРАЛЬНО (1:1, доказано) ✅
Сделано в одном заходе с гигиеной шапок (выбор пользователя: «Шаг 3 + гигиена»).
- **Новые переменные** (`qsp_base`, после `elseif_permissive_tail`):
  `final_guard` (`(?=^\s*{{elseif_else_final}}([^\&\n\r]*))`), `kw_calls`
  (`(goto|gt|xgoto|xgt|gosub|gs)`), `left_ctx_anchor` (якорь + `\K`) и
  `left_ctx_lookbehind` (lookbehind-вариант для подвыражений `<< … >>`, где нет `^` строки).
  NB: у `final_guard`/`kw_calls`/`left_ctx_*` **захватывающие группы сохранены** — нумерация
  `captures` в правилах не сдвинулась; глубина раскрутки `{{}}` не выросла (3 уровня уже были:
  правило → `left_operand` → `quote`).
- **`final_guard`**: заменены **5** копий (не 12+, как ошибочно указано в P1.6) — в
  `else_body_head_bare`, `elseif_body_head_strict`, `elseif_body_head_permissive`,
  `multiline_elseif_body`, `multiline_elseif_body_braced`.
- **`kw_calls`**: 2 правила `location_call` (`(goto|gt|…)(?=\s*($|&))` и
  `…\s*(({{ap}}|{{quote}}).*?\3)`). Второе правило переписано через `{{ap}}`/`{{quote}}` (не через
  литеральные кавычки), т.к. YAML-скаляр в одинарных кавычках нельзя чисто экранировать.
- **Comma-сегменты**: порядок значим (`with_out_right → with_out_left → sign`), а
  `with_out_left` в `operacion` (`(^\s*?|\&\s*?|\(\s*?|\{\s*?|\[\s*?)\K`) и в
  `operacion_subex` (`(?<=(<|\&|\(|\{|\[))`) РАЗНЫЕ → одним блоком не вынести. Сделано два
  сегмента: `operacion_comma_with_out_right` и `operacion_comma_sign`; между ними остаётся
  своё `with_out_left` правило на `{{left_ctx_anchor}}`/`{{left_ctx_lookbehind}}`.
- **Гигиена**: шапка `multiline_actions_else` переписана — теперь это карта 7 arms
  (invalid-условие / colon-caret / colon-brace / colon-single / stmt-single /
  `else !коммент` / bare) с явным водоразделом «код-тело (arms 6–7) vs мёртвый код (4–5)»;
  bare-arms пушат ОДИН именованный контекст (`push: else_body_block[_braced]`) вместо
  трёхстрочного inline-стека; шапка самого `else_body_block` актуализирована.
- **Доказательство 1:1** (ad-hoc верификатор, удалён после прогона): обе версии
  (`git show HEAD:` vs диск) канонизировались — раскрутка `{{var}}` во всех `match`, инлайн
  новых comma-сегментов, приведение `push: имя` и `push: [{include: …}]` к списку имён — и
  посериализованно сравнивались. Итог: **84 старых контекста IDENTICAL**, расхождений ровно 2 —
  новые `operacion_comma_*`. Заодно доказано, что `push: else_body_block` ≡ прежний inline-стек.
- **Контроль:** `check_syntax_phase1.py` → **PASS** (local=**86** = 84+2 новых, refs=84, pairing **15** пар,
  `declared-but-unused: none`).
- **Что НЕ делалось (сознательно):** P1.5 (слияние `no` + переименование scope — намеренная смена
  поведения), P1.7 (`\s*?`→`\s*`), P1.3 (удаление 5-го/bare-arm — **стало неактуально**, см. §3).

### 1i. `else if` как единый оператор + фикс перехода через строку (2026-10-28) ✅
**Вопрос:** поддерживается ли `else if` так же, как `elseif`? — **Да, поддерживалось и осталось:**
- `kw_elseif` = `(?i:(\b(?:else[ \t]+if|elseif)\b))`, используется во ВСЕХ трёх elseif-arms ×2
  (plain + braced), а `multiline_actions_elseif` инклюдится **ДО** `multiline_actions_else`
  (и в `multiline_conditions_body`, и в `multiline_actions`), поэтому `else if cond:` до else-arms
  не доходит: оба слова — ОДИН токен со scope `keyword.control.conditional.else.qsp
  markup.italic.qsp meta.else_body.qsp` (как `elseif`).
- Покрыто в `syntax_test_qsp.qsps` (plain + braced): блок `else if 1:` / `else if 2: ! хвост`.

**НАЙДЕН ДЕФЕКТ (исправлен):** в `kw_elseif` стоял `\s+`, а `\s` в Onigmo включает перенос
строки → легальный **вложенный `if` в теле else**
(`else` ⏎ `<TAB>if $a <> '':`, реальный код:
`_examples/example_project/drive/objects.sys/предметы/add nocount object in purse.qsps` 24–28)
склеивался в ОДИН elseif-токен (`else\n\tif`), а сам `if` переставал быть открывателем блока.
По грамматике `ws = (lineContinuation | space)*` — ПЕРЕНОС строки в `ws` НЕ входит, значит
`else` и `if` обязаны быть на одной строке.
- **Фикс 1:** `kw_elseif`: `else\s+if` → `else[ \t]+if` (горизонтальный пробел/таб).
- **Фикс 2 (обязательный, иначе баг всплывает в другом месте):** arm1
  `multiline_actions_else` (invalid `else <условие>:`) матчил и его: `\s*?` + `[^:]+` в `[^:]+`
  попадают `\n`/`\r`. Сужено до строки: `^[ \t]*?(else)([ \t]*?)([^:\n\r]+)(:)` — plain и braced.
- **Симуляция arm-порядка** (re.M, как края строки в Sublime):
  `else if 1:` → elseif-arm1 (`else if`); `else\tif 1:` → arm1; `else   if $x > 1: !c` → arm1;
  `else if $a: & !c` → arm2 (permissive); `else if (1 +` → arm3 (pending); `elseif 1:` → arm1;
  `else` ⏎ `\tif $a <> '':` → **elseif-arms: нет**, else-arm7 (bare) ✓; `else !коммент` → arm6;
  `else $lvar = 3` → arm5; `else` → arm7.
- **Остаточное ограничение (осознанно):** `else _` ⏎ `if …:` (lineContinuation в `ws`)
  как единый `else if` НЕ подсвечивается — мост через `_`-продолжение в базе отсутствует
  вообще (известный пробел, отдельная тема); `else if` в ОДНОСТРОЧНОЙ цепочке
  (`if a: b else if c: d`) тоже не keyword — arms якорятся на `^`/`{`.
- **Контроль:** `check_syntax_phase1.py` → **PASS** (local=86, pairing 15 пар).

### 1j. Мёртвый регион однострочных `else`/`elseif` = многострочный комментарий (2026-10-28) ✅
**Симптом:** `multilines_conditionals.qsps` 186–188 — `else: & ! вариант по умолчанию` ⏎ `<TAB>*pl '0'`:
мёртвая строка красилась **плоским однострочным** комментарием (catch-all `^.*`), хотя плеер
сканирует её с учётом кавычек/апострофов/скобок.

**Корень:**
- arms 4–5 `multiline_actions_else` (`colon-single` / `stmt-single`) пушили inline-стек с
  `- match: "^.*"` → оно совпадает в **колонке 0** каждой строки и перебивает правила кавычек/скобок,
  а конец региона решал только `final_guard`;
- `elseif_body_head_permissive` (однострочный `elseif …: <stmt>`) имел **тот же** `^.*` — та же проблема.

**Фикс — переиспользование машинерии комментариев (а НЕ своя копия структуры):**
- состояния внутри комментария вынесены в **именованные** контексты (были inline в push-стеках):
  `comment_in_quote` / `comment_in_apostroph` / `comment_in_brace`; обёртки-входы
  `quote_apostroph_comments` / `brace_comments` теперь только `push:` этих состояний;
- у состояний **нет catch-all'а, и он не нужен**: пока состояние на вершине стека, контексты ниже
  не рассматриваются — кадр кавычки «не пускает» поиск вниз. Это не новое следствие рефакторинга,
  а поведение, которое было и до него: `}` внутри `"…"` не закрывает `{…}`-блок, а `&` после `end`
  внутри кавычки не рвёт `comment_after_end_in_brace`. Для обычных комментариев рефакторинг — **1:1**;
- все три состояния **живут через переносы строк** (литерал QSP бывает многострочным — в корпусе
  `$args['…'] = '` ⏎ … ⏎ `'`; `{…}` — блок комментария). Раньше в моём промежуточном варианте кавычки
  pop'ались по EOL → «работали только фигурные скобки» — ЭТО ИСПРАВЛЕНО;
- новый **общий** регион `dead_code_comment` (`meta_scope: comment.qsp`): `final_guard`→pop,
  затем `include: quote_apostroph_comments` + `brace_comments` + `special_comments` — **ровно те же
  include'ы, что у обычного комментария** (`comment_tail_common`), только вместо pop'а по newline — pop
  по final-guard. Catch-all не нужен: текст без своего правила просто остаётся под `meta_scope`.
  Кавычка/`{…}` на вершине стека делают `final_guard` недостижимым — т.е. `end` внутри литерала или
  вложенных `{…}` регион не закрывает;
- входные кадры (plain + braced — единственное, где нужно зеркало): `else_dead_line`,
  `elseif_dead_line` — `match: '^'` → `pop` + `push: dead_code_comment`; хвост САМОЙ строки
  else/elseif = обычное тело (`location_body[_braced]`);
- arms: else 4–5 → `push: else_dead_line[_braced]`; elseif permissive (plain+braced) →
  `push: elseif_dead_line[_braced]`; `elseif_body_head_permissive` **удалён** (его `^.*` больше не нужен).

**Почему `^`, а НЕ `$`/newline:** хвост `else: & !…` живёт в `comment_after_else`, который pop'ается,
**съедая newline** → правило по `$`/newline уже никогда не сработает. `^` — нулевая ширина в начале
следующей строки, до всякого кода.

**Почему регион без braced-зеркала:** внутри мёртвого кода `{…}` — это структура КОММЕНТАРИЯ, а не блок
кода, т.е. тело региона от окружения не зависит; зеркалятся только входные кадры (parity 5.1).

**Побочных эффектов нет.** Промежуточный вариант с «трапами» в общих состояниях комментария был
основан на неверной модели (якобы поиск проваливается в нижние кадры стека) и эту модель опровергает
поведение самих комментариев: `! "}"` внутри `{…}` не закрывает блок, кавычка после `end` защищает `&`.
Трапы убраны — общие состояния вернулись к 1:1 с прежним поведением, регион работает на той же
структуре. Регресс закреплён в фикстуре: `syntax_test_qsp.qsps` — `! "}"` внутри `{…}` с ассертом
`// ^ comment.qsp -punctuation.section.block.end.qsp`.

**Покрытие:** `multilines_conditionals.qsps` 191–216 — однострочный `elseif` + многострочный литерал
(`end` на отдельной строке внутри), вложенные `{…}` + `'end'` внутри, `else: *pl` с литералом `"…"`;
`syntax_test_qsp.qsps` (`# st.death`) — те же случаи с ассертами `// ^ comment.qsp` на мёртвых строках и
`// ^ -comment.qsp` на вернувшемся коде.

**Контроль:** `check_syntax_phase1.py` → **PASS** (local=**93**, refs=91, pairing **17** пар;
в PAIRS: `else_dead_line`, `elseif_dead_line`).

**Сопутствующее уточнение в 1c:** `elseif_body_head_permissive` из списка «6 новых контекстов» шага 2
выбыл — его роль перешла к `elseif_dead_line` + `dead_code_comment`.

### 1c. Шаг 2 рефакторинга (P1.2 + P1.4) — поведение НЕЙТРАЛЬНО (1:1, доказано)
Вынесены построчно-идентичные inline-тела push-стеков в общие include-сегменты
(`qsp_base.sublime-syntax`, блок перед `multiline_actions_else`), 6 новых контекстов:
- `pending_inline_pop` — `{{pend_inline}}→pop` (был 10 копий во всех pending plain+braced → 1);
- `else_body_head_bare` = `illegal_multiline_else` + final-guard;
- `else_body_common_head` = `comment_after_colon` + `else_body_head_bare` (arms caret/brace);
- `else_body_guarded_tail` = `wrongclose` + `wrong_close_in_brace` (хвост всех else-arms);
- `elseif_body_head_strict` = `comment_after_colon` + final-guard; `elseif_body_head_permissive`
  = final-guard + `^.*`comment.
**Ключ:** различие plain↔braced осталось ТОЛЬКО в финальном `include location_body[_braced]`,
поэтому сами сегменты не содержат `_braced` и инклюдятся зеркалами одинаково (sync-контракт цел).
**Доказательство 1:1:** ad-hoc верификатор разворачивал include'ы (только новые сегменты,
остальные — токены) и сверял с HEAD — все 14 затронутых контекстов `IDENTICAL` (потом удалён).
Экономия: ~−38 строк исходника. **Контроль:** `check_syntax_phase1.py` → PASS (local=81, pairing 14 пар).

---

## 2. ЧТО ПРОВЕРИТЬ ВРУЧНУЮ (Sublime Text — окончательный судья)
Headless-прогон `run_syntax_test` невозможен при открытом окне Sublime (запущен 1 экземпляр).
Открой `syntax_test_qsp.qsps` + свои qsps/qsrc, глянь (Шаг 2 ничего не должен был сменить, но
проверь регресс по else/elseif/pending после рефакторинга inline-тел):
1. `else` без `:` в многострочном `if` — тело ниже НЕ должно быть комментарием; `end` ловится.
2. `else:` (блок), `else !коммент` (`!` = comment, тело ниже = код), `else <текст>:` (хвост = комментарий, как и было), `else` с `&`-продолжением.
3. То же внутри `{…}` (braced-двойники).
4. Pending-заголовки `if`/`act`/`loop`/`elseif` с многострочной `( …`/`[ …` (шаг 1a мог задеть).
5. После шага 3 (доказано 1:1, но глазами — обязательно): операторный блок (`+ - < > = / * !`,
   `no`, `and/or/mod`), запятые в `x, y` / `x,` / `,y`, подвыражения `<< … >>` и вызовы
   локаций `goto "…"` / `gosub '…'` / `gt` / `gs` (в т.ч. битые `goto` без цели).
6. `else if 1:` — ОДИН токен (как `elseif`); `else` ⏎ `<TAB>if …:` — `else` отдельно, `if` открывает свой блок.

7. Фикс 1j (мёртвый регион однострочных `else`/`elseif`, `multilines_conditionals.qsps` 191–216):
   весь регион — ОДИН многострочный комментарий той же структуры, что и обычный `!`-комментарий:
   `"…"`/`'…'` тянутся через строки (литерал с `end` на отдельной строке остаётся комментарием),
   `{…}` считает вложенность и защищает `if`/`end`; `elseif <cond>: <stmt>` красит так же, как `else`;
   выйти можно только строкой, начинающейся с end/else/elseif/if — всё после неё снова код.

Если рендер чистый → зафиксируй коммит (`git add -A; git commit`).

---

## 3. ОСТАВШИЕСЯ ШАГИ (порядок из refactoring_review.md §«Предлагаемый порядок работ»)
| Шаг | Что | Статус |
|---|---|---|
| 1 | P1.1 (переменные якорей/lookahead) | ✅ сделано (1a) |
| 1.7 | нормализация `\s*?`→`\s*` | ⏸ отложено (сделать отдельным прогоном + тесты) |
| 2 | P1.2 + P1.4 — вынос inline-тел else/elseif/pending в общие include-сегменты | ✅ сделано (1c) |
| 3 | P1.6 — общие comma-сегменты, `final_guard`, `kw_calls` | ✅ сделано (1h) |
| 3+ | P1.5 — слияние правил `no` в общий сегмент + scope `avs_wrong_no_with_out_right` | ⬜ (см. §4) |
| 4 | Вариант A — генерация `_braced`-слоя препроцессором сборки | ⬜ |
| 5 | P4 фиксы (`qspdocs` `...`, `qspgame_header`, meta-scope act/if/loop) | ⬜ |
| — | P1.3 «удалить 5-й arm» | ❌ **неактуально**: после 1b/1d/1e/1g arm'ов стало 7 и у каждого своя роль (см. шапку `multiline_actions_else`); сливать нечего |

Отдельный **БАГ-лист (P4)**, ещё не решён: `qspdocs` 1-е правило содержит литеральные `...`
(матчит ровно 3 символа — похоже на незакрытый placeholder); `(?<![\s\S])` в `qspgame_header`
хрупкий суррогат «первой строки»; разнородные meta-scope на act/if/loop-заголовках.

---

## 4. КЛЮЧЕВОЕ РЕШЕНИЕ P1.5 (для шага 3+) — принято, ещё НЕ реализовано
Оператор `no` **регистронезависим** (как все ключевые слова/имена переменных QSP) → различие
`(?i:)` vs без флага в `operacion_subex` — недосмотр, а не зафиксированное поведение. Значит:
- правила `no` из `operacion` и `operacion_subex` **можно слить** в общий сегмент с `(?i:\bno\b)`;
- ошибочный scope `avs_wrong_comma_with_out_left` у `no` (copy-paste от запятой; правило с `(?!)` —
  это «без **правого**») → переименовать в **`avs_wrong_no_with_out_right`**;
- внешние привязки к `avs_wrong_comma_with_out_left` (color scheme/TCE) grep'ом не найдены → безопасно;
- НЕ трогать остальные вхождения `avs_wrong_comma_with_out_left` (они про реальные запятые/амперсанды);
- **намеренная поведенческая правка** (для `NO`/`No` в `<< … >>` подсветка станет invalid) → обновить `syntax_test_*.qsps`.

---

## 5. НЕПРИКОСНОВЕННЫЕ ИНВАРИАНТЫ (зафиксированы в памяти — подтянутся сами)
- Поведение (набор scopes) при рефакторинге шагов 1–3 держать **1:1**.
- **Sync-контракт** plain↔`_braced`: любая правка в `multiline_*` дублируется зеркально в `multiline_*_braced`;
  парность проверяет `check_syntax_phase1.py` (**17** пар) — расхождение валит FAIL.
- **Нельзя:** слияние arms через внешнюю альтернацию якорей `^|{` (ложно расширяет позиции);
  `(?|…)` branch-reset (не поддержан Onigmo этой сборки); менять порядок `wrongclose → wrong_close_in_brace → тело`.
- **Порядок правил значим** (search слева-направо, первое совпадение).
- Фикстуры с незакрытыми конструкциями «отравляют» последующие строки — ставь их в конце/отдельным файлом.
- В `sublime-syntax` внутри regex не использовать `\xNN` (Oniguruma UTF-8 падает).

---

## 6. КАК ПРОДОЛЖИТЬ В НОВОМ ЧАТЕ
1. Открой воркспейс `d:\my\GameDev\QuestSoftPlayer\projects\JAD`.
2. Скажи: «читай `_disdocs/syntax_highlighting/HANDOFF.md` и `refactoring_review.md`; делаем шаг <N>».
3. Перед первой правкой — `git status` (сверь, закоммичен ли §1); после — `check_syntax_phase1.py` (ожид PASS).
4. Память Qoder уже содержит: «no регистронезависим…», «опциональное (:?) у else-arm…», конвенции
   avs-маркеров/parity/операторов — уточнять их не нужно, но **проверяй актуальность** чтением кода.
