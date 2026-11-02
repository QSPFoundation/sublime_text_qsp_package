# Handoff: рефакторинг модуля `qSpy/preprocessor`

Рабочий контекст рефакторинга препроцессора. Здесь фиксируются: архитектура,
найденные незакрытые места и логические ошибки, план правок.

Исходники: [`QSP.sublime-package/qSpy/preprocessor`](../../QSP.sublime-package/qSpy/preprocessor)
Грамматика-эталон: [`pp_scheme.pest`](./pp_scheme.pest), [`comment.pest`](./comment.pest)
Постановка/режимы: [`preprocessor_todo.md`](./preprocessor_todo.md), [`pp_modes.canvas`](./pp_modes.canvas)

---

## 1. Архитектура (как есть)

Точка входа — [`main.py`](../../QSP.sublime-package/qSpy/preprocessor/main.py) `QspsPP.pp_this_lines()`.
Обработка делится на **две последовательные стадии**, каждая = сканер → парсер → интерпретатор:

**Стадия директив** (видит только `!@pp:` и сырые строки, не понимает скобок/строк):
- [`dirs_scanner.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_scanner.py) `DirsScaner` — токены директив;
- [`dirs_parser.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_parser.py) `DirsParser` → [`dirs_stmts.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_stmts.py)/[`pp_dir.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_dir.py)/[`pp_expr.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_expr.py);
- [`dirs_int.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_int.py) `DirsInt` — считает режимы (`pp/savecomm/include/open_if`), размечает строки `MarkedLine = (line, no_save_comm, include)`.

**Стадия кода/локаций** (работает по размеченным строкам, понимает локации, строки, блоки, комментарии):
- [`pp_scanner.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_scanner.py) `PpScanner` →
- [`pp_parser.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_parser.py) `PpParser` →
- [`pp_int.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_int.py) `PpInt` — собирает выходные строки, применяя флаги разметки.

Общее: [`pp_tokens.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_tokens.py) (токены/enum), [`pp_common.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_common.py) (модель строк `QspsLine`/`MarkedLine` + хелперы `is_word_char`/`expected_chars`), [`pp_environment.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_environment.py) (метки), [`error.py`](../../QSP.sublime-package/qSpy/preprocessor/error.py), printing: `dirs_ast_printer.py`, `pp_ast_printer.py`.

Вызов из [`builder.py`](../../QSP.sublime-package/qSpy/builder.py) (`pp_switch != 'Hard-off'` → создаётся `QspsPP`).

Тестовый контур: [`_examples/.tests/_pp_test_.py`](../../_examples/.tests/_pp_test_.py), фикстуры в [`_examples/example_preprocessor`](../../_examples/example_preprocessor).

---

## 2. Найденные проблемы

### Критичные (реальные баги)

**B1. `main.py:66` — потерянный `= True`.**
```python
if self._dirs_scanner.errored(): self._error_check   # no-op, ничего не присваивается
```
Должно быть `self._error_check = True`. Сейчас ошибка сканера директив не помечает статус.
Остальные шаги (78, 102, 113) делают это корректно — править по образцу.

**B2. Вложенные `if` ломают стек режимов** ([`dirs_int.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_int.py)).
`_modes` — стек, `_new_modes()` пушит кадр на `if`, `visit_endif_dir()` делает `pop` если
`_if_is_open()`. Но внутри «ложной» ветки `pp` выключен, и вложенный `if` **не выполняется**
(нет пуша), а его `endif` проходит через `_is_endif()` и **снимает внешний кадр**. Блоки разъезжаются.
Подтверждено задачей: [preprocessor_todo.md «Вложенные блоки условий»](./preprocessor_todo.md).
Нужен счётчик глубины `if`, независимый от выполнения тела.

**B3. нет валидации `endif`/незакрытого `if`.**
Осиротевший `endif` (без открытого `if`) молча игнорируется; незакрытый `if` к EOF не
детектируется. Нет ни ошибки, ни предупреждения — тихое расхождение.

**B4. ~~сканер директив не контекстный → ложные срабатывания~~ — НЕ БАГ, снято.**
Проверено на [`pptest.qsps`](../../_examples/example_preprocessor/pptest.qsps): строка 56
`!@pp:if(l):exclude` стоит отдельной строкой внутри многострочной литеры (53–62) и намеренно
исполняется (см. `expected.qsps`), а строка 63 `"!@pp:if(layer1):exclude"` (директива прижата
кавычкой, не с начала строки) — НЕ исполняется. Правило языка: директива срабатывает, если `!@pp:`
стоит в начале физической строки (col 0 или после преформаттера), даже если это продолжение литеры.
Это документированная фича; кросс-строчный контекст в сканере не нужен.

**B5. `pp_int.py:63` — недоинициализированный `Context` + мёртвый код. — ЗАКРЫТО (вычищено как мёртвое).**
Проверено: вся конструкция `_contexts` в `PpInt` мертва. Начальный контекст не содержал `loc_open`
(`KeyError` при вызове), `_loc_is_open()` не вызывался нигде, а реальное состояние локации ведёт
парсер своим булевым флагом `PpParser._loc_is_open`; `in_literal_string` тоже только писался,
никогда не читался (решение «включать строку» идёт по `token.include_line`). Удалены: тип `Modes`,
тип `Context`, стек `_contexts`, методы `_loc`/`_loc_is_open`/`_new_context` и их вызовы в
`visit_loc_*`/`visit_string_literal`. Golden зелёный, sha не изменился.

### Незакрытые места (обещано грамматикой/доками, но не реализовано)

**U1. Директива `nopp` — РЕШЕНО: не реализуем, вычёркиваем.**
Была в грамматике ([pp_scheme.pest:78,123](./pp_scheme.pest)) и в постановке
([preprocessor_todo.md:81](./preprocessor_todo.md)). В коде — только закомментированные заглушки
([`dirs_parser.py:160-163`](../../QSP.sublime-package/qSpy/preprocessor/dirs_parser.py),
`NoppDir` в [`pp_dir.py:128`](../../QSP.sublime-package/qSpy/preprocessor/pp_dir.py)); токена `NOPP_STMT`,
keyword-а, разбора, узла и `visit_nopp_dir` нет.
**Решение владельца:** `nopp` больше не актуален — `off`/`on` полностью покрывает отключение/включение
препроцессора до конца файла. Убрать `nopp` из `pp_scheme.pest` и `preprocessor_todo.md`; закомментированные
заглушки в коде удалить попутно (Фаза 2/5).

**U2. `ParenBlock`/`CodeBlock` не имеют своих AST-узлов.**
Парсер возвращает `BracketBlock` для `(`/`{` с пометкой «Временно используем BracketBlock»
([`pp_parser.py:176-246`](../../QSP.sublime-package/qSpy/preprocessor/pp_parser.py)); `PpInt._QUOTES` —
костыль для восстановления скобок. Грамматика различает их
([pp_scheme.pest:60-62](./pp_scheme.pest)). Нужны отдельные ноды либо явное единое представление.

**U3. Значения в `var`/присваивании и множественные метки.**Числовые/строковые литералы
и список через запятую (`var(a, b, c = label, 'string', 123)`) реализованы в Фазе 5 — см.
[## Фазы](#). `const(...)` ([preprocessor_todo.md:53-68](./preprocessor_todo.md)) не реализовано.
`!@pp:change/by/endchange` (блоки замены, [preprocessor_todo.md:25-38](./preprocessor_todo.md)) — не реализовано,
предложено отнести к постпроцессору.

### Качество / надёжность

**Q1. Дублирование.** `MarkedLine`, `QspsLine`, `LineNum`, `Point`, `_is_alnum`,
`_add_expected_chars`, работа со стеком — повторяются в `dirs_scanner`/`pp_scanner`/`dirs_int`/`pp_int`.
Два почти идентичных набора классов ошибок в `error.py`. Вынести в общий модуль типов/утилит.

**Q2. Хрупкие индексные «хаки» сборки строки** в `pp_int.visit_stmts_line`
([`pp_int.py:131-134`](../../QSP.sublime-package/qSpy/preprocessor/pp_int.py)): `pop(-2)` по
предположению о структуре «`&` + пробел/перевод» перед спецкомментарием. Легко ломается.

**Q3. `errored()` врёт в докстринге.** В `main.py` комментарий «resets PP state», но сброса нет
(сброс реально происходит в начале `pp_this_lines`). Поправить формулировку.

**Q4. Границы peek.** `_eat_tokens` утверждает «выход за пределы невозможен», но `_next_peek()`
на EOF читает `[sk+1]` за гранью; `_prev_peek()` на нулевом индексе читает `[-1]` (хвост списка).
В текущих потоках не срабатывает, но хрупко.

**Q5. Несогласованные типы/возвраты.** `QspsPP.__init__` подписан `Literal['Off','On']` при
`PpMode = Literal['Hard-off','Off','On']` ([`plugtypes.py:13`](../../QSP.sublime-package/qSpy/plugtypes.py)).
`pp_fastlines()` возвращает сырой `_prepare_lines` (без склейки по переводам), а `get_output()` —
склеенный; `main` при пустом результате возвращает `['\n']` — смешение форм. Унифицировать контракт.

**Q6. Режим `pp Off` + стадия кода.** Когда `pp` выключен, директива проходит в вывод как есть,
но `PpScanner`/`PpInt` всё равно перечитывают строку как код и пересобирают из токенов — риск
искажения «прокидных» строк, которые по доку [preprocessor_todo.md:15-17](./preprocessor_todo.md) должны
сохраняться дословно. Проверить/гарантировать verbatim-путь.

---

## 3. План рефакторинга (по фазам)

Принцип: сначала — не менять поведение, закрепить контуром (B-баги правятся точечно); затем —
структурные упрощения; в конце — новый функционал (U1–U3). Каждая фаза = зелёные тесты + коммит.

### Фаза 0. Контур проверки — ГОТОВО
- Золотой контур: [`_examples/.tests/_pp_golden_run.py`](../../_examples/.tests/_pp_golden_run.py)
  (запуск из любого каталога: `python _examples/.tests/_pp_golden_run.py`). Гоняет `QspsPP('On')`
  на [`pptest.qsps`](../../_examples/example_preprocessor/pptest.qsps), сверяет с
  [`expected.qsps`](../../_examples/example_preprocessor/expected.qsps), пишет фактический вывод в
  [`_baseline_output.qsps`](./_baseline_output.qsps).
- Базовый golden (до Phase-1): `current == expected`, `out_lines=33`,
  `golden_sha=4b36084f8f60baa3`, `errored=True` (3 штатных recovery-сообщения «Unexpected token,
  get IDENTIFIER» на строках 37/47/65 — неизвестные директивы). Перед каждой фазой сверять этот sha:
  совпал — поведение не изменилось; разошёлся — сравнить diff и подтвердить, что изменение намеренное.
- Не заведено: отдельные фикстуры на B2 (вложенный if) / B4 (директива в многострочной литерe) /
  сочетания `pp+savecomm`, `pp+no include` ([preprocessor_todo.md:5-21](./preprocessor_todo.md)) —
  завести по мере подхода к этим пунктам (Фаза 3).

### Фаза 1. Очевидные баги (микроправки, без смены архитектуры) — ГОТОВО (golden зелёный, sha не изменился)
- **B1** [`main.py:66`](../../QSP.sublime-package/qSpy/preprocessor/main.py) → `self._error_check = True`. ✅
- **Q3** докстринг `errored()` приведён в соответствие (сброс идёт в начале `pp_this_lines`). ✅
- **Q4** `_next_peek`/`_prev_peek` в `dirs_parser.py` и `pp_parser.py` клампят границы (EOF/первый токен). ✅
- **Q5** ОТСРОЧЕНО. Подпись `mode: Literal['Off','On']` корректна для того, что реально доходит до
  `QspsPP` (builder отфильтровывает `'Hard-off'`). Унификация контракта возврата
  (`fast_output` vs `get_output`, фолбэк `['\n']`) трогает debug-артефакты и путь пустого вывода —
  поведенчески рискованна, переносится на Фазу 2 (общий слой) / отдельной правкой.

### Фаза 2. Общий слой типов/утилит (Q1) — ГОТОВО (golden зелёный, sha не изменился)
- создан [`pp_common.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_common.py): модель строк
  (`QspsLine`, `QspsLines`, `NoSaveComm`, `IncludeLine`, `MarkedLine`) + хелперы
  (`is_word_char`, `expected_chars`). Единственный источник этих типов.
- `dirs_scanner`/`pp_scanner`: убраны локальные дубли `QspsLine`/`MarkedLine`/`Point`,
  методы `_is_alnum`/`_add_expected_chars` заменены на вызовы `pp_common`; мёртвый `_is_alnum`
  в `pp_scanner` удалён.
- `dirs_int`/`pp_int`/`main`: типы строк-модели импортируются из `pp_common` (не переобъявляются).
- `error.py`: 6 почти-копий `*RunError` свёрнуты в базу `_RunError` (наследники различаются только
  `label`); имена классов и текст `__str__` сохранены дословно → `except` в `main.py` работает.
- Оставлено на потом: `SyntaxError`-семья не трогалась (у них разная сигнатура конструкторов —
  не «копии»); мёртвый `Modes`/`loc` в `pp_int` — это B5, чинится в Фазе 3; унификация контракта
  возврата (`fast_output`/`get_output`, `['\n']`, Q5) — отдельной правкой.

### Фаза 3. Корректность стадии директив (B2/B3) — ГОТОВО
- **B2 (вложенные `if`):** в [`dirs_int.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_int.py)
  введён структурный стек `_if_stack: List[bool]` (True — if выполнен, False — пропущен при pp-off).
  `visit_pp_directive` переписан: каждый `if` пушит фрейм режимов (исполненный — через
  `visit_condition_dir`, пропущенный — через `_new_modes`), каждый `endif` делает симметричный pop
  и решает «убрать строку» (исполненный) vs «дословно» (пропущенный). Глубина вложенности отвязана
  от вычисления условий → парный endif больше не снимает чужой фрейм.
- **B3 (сиротский endif):** обрабатывается щадяще — при пустом `_if_stack` стек режимов НЕ трогаем,
  строка убирается (pp on) или проходит дословно (pp off). Жёсткий `raise` НЕ сделан осознанно:
  незакрытый `if` на EOF — легитимный способ «выключить pp до конца файла» (вместо отменённого `nopp`).
- Убраны мёртвые `_if_is_open`/`_is_endif` и ключ `open_if` из `Modes`; `visit_endif_dir` — заглушка
  (endif живёт в `visit_pp_directive`). Попутно устранено затенение модуля `dir` в цикле `next_dirs`.
- **B4:** снят (см. §2 — по языковому дизайну).
- **Q6 (verbatim при pp Off):** подтверждён тестом вложенности — строки-директивы внутри off-блока
  проходят в вывод дословно без искажения. Отдельной правки не потребовалось.
- Контур: [`_pp_nesting_test.py`](../../_examples/.tests/_pp_nesting_test.py) — 4 сценария
  (off-вложенность, exclude-вложенность, сиротский endif, 3 уровня вложенности — глубина не съезжает).
  Golden `pptest.qsps` не затронут (нет вложенных if) → `sha=4b36084f8f60baa3` сохранился.

### Фаза 4. Стадия кода: честный AST (U2) — ГОТОВО (golden зелёный, sha не изменился)
- **U2 (решение владельца: отдельные ноды по грамматике):** в [`pp_stmts.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_stmts.py)
  наряду с `BracketBlock` заведены `ParenBlock` и `CodeBlock` (поля `left/value/right` идентичны)
  и абстрактные `visit_paren_block`/`visit_code_block`. [`pp_parser.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_parser.py):
  `_paren_block`/`_code_block` возвращают честные ноды, пометки «Временно» сняты. Visitor'ы обновлены:
  [`pp_ast_printer.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_ast_printer.py) печатает точный `class`,
  [`pp_int.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_int.py) сводит три блока к одному `_gen_block`.
- **`_QUOTES`-костыль удалён.** Скобки/кавычки сканируются одно-символьными токенами, у которых
  `.lexeme` уже равен символу → `_QUOTES[ttype]` ≡ `token.lexeme`. Реконструкция блоков и строковых
  литералов теперь читает `.lexeme`. Различие Content-правил (директивы внутри `CodeBlock`) — вне
  объёма фазы, это U3/Фаза 5.
- **Q2:** два позиционных `pop(-2)` в `visit_stmts_line` свёрнуты в `_strip_trailing_separator()` —
  снятие хвостового разделителя «&» с обрамляющими пробелами по содержимому, а не по жёстким
  индексам (ушёл и незащищённый `[-2]` на коротких строках). Ветка `base_comment`/исключённого
  комментария не затронута: `&` там остаётся дословно (подтверждено expected.qsps строк 9/12/16/19/20).
- Не заведено: фикстура, прямо упражняющая скобочные блоки в теле локации (`pptest.qsps` их не содержит);
  правка `_QUOTES→.lexeme` доказуемо эквивалентна статически.

### Фаза 5. Новый функционал по грамматике (U3) — ГОТОВО (кроме отложенного)
- **U1 `nopp`:** ЗАКРЫТО. Закомментированные заглушки снесены из
  [`dirs_parser.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_parser.py) (`_cond_resolves`) и
  [`pp_dir.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_dir.py) (`ConditionResolve`). Упоминания
  убраны из [`pp_scheme.pest`](./pp_scheme.pest) (`noppStmt`) и [`preprocessor_todo.md`](./preprocessor_todo.md).
  Токена `NOPP_STMT` и класса `NoppDir` в коде не было (только комментарии) — проверено grep: ноль вхождений.
- **U3 — строковые литералы в значениях `var`: ГОТОВО (golden не затронут, sha сохранён).**
  Числа работали и раньше (цифры — word-chars → IDENTIFIER; `def_key_set_value` заводит значение и
  меткой, и значением → `name==123` совпадает). Добавлена поддержка строк сквозняком:
  токен `STRING` ([`pp_tokens.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_tokens.py)) →
  распознавание `"..."`/`'...'` в сканере директив (`_dir_string_expect`,
  [`dirs_scanner.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_scanner.py)) → приём в значении
  `var` и в операндах сравнения ([`dirs_parser.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_parser.py))
  → хранение литерала без объявления метки (`PpEnvironment.set_literal`,
  [`pp_environment.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_environment.py)) →
  разрешение `STRING`-операнда как литерала в [`dirs_int.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_int.py)
  (`visit_assignment_dir`, `visit_var_name`). Строка завершается первой парной кавычкой; удвоенное
  экранирование (`""`) в значениях директив сознательно НЕ поддержано (значения кратки).
  Контур: [`_pp_var_string_test.py`](../../_examples/.tests/_pp_var_string_test.py) — 4 сценария
  (равенство строки, литерал≠метка, апострофы+спецсимволы, несовпадение→без exclude).
- **U3 — множественное объявление меток `var(a, b, c = label, 'string', 123)`: ГОТОВО
  (golden не затронут, sha сохранён).** `var(...)` теперь принимает список через запятую.
  Сканер директив выдаёт токен `COMMA` ([`pp_tokens.py`](../../QSP.sublime-package/qSpy/preprocessor/pp_tokens.py),
  [`dirs_scanner.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_scanner.py)); разбор
  (`_assignment_dir`/`_assignment_item`, [`dirs_parser.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_parser.py))
  собирает новый узел [`pp_dir.AssignmentsDir`](../../QSP.sublime-package/qSpy/preprocessor/pp_dir.py) — контейнер из
  `AssignmentDir`. Каждый элемент применяется по прежней per-item семантике
  (`visit_assignments_dir` → `visit_assignment_dir`, [`dirs_int.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_int.py));
  голое имя/число/строка объявляет метку, `имя = значение` — присваивает (строка через `set_literal`).
  Контур: [`_pp_var_multi_test.py`](../../_examples/.tests/_pp_var_multi_test.py) — 5 сценариев
  (голые метки, смешанный список из todo, пример владельца со строкой и числом, необъявленная метка,
  битый `var(a,,b)` без падения).
- **Отложено (по указанию владельца):** `const(...)` — семантика/необходимость не утверждены;
  `change/by/endchange` — черновик, не реализуем.

### Фаза 6. Синхронизация документации
- Сверить [`pp_scheme.pest`](./pp_scheme.pest) с фактическим поведением после фаз 3–5; расхождения
  фиксировать здесь. Обновить [preprocessor_todo.md](./preprocessor_todo.md) (перенести закрытые пункты).

---

## 4. Открытые вопросы к владельцу
1. B4: лёгкий кросс-строчный контекст в `DirsScaner` или перенос разбора директив в стадию кода?
2. ~~U1: `nopp` — реализуем или вычёркиваем из спецификации?~~ ЗАКРЫТО: вычёркиваем, `off`/`on` достаточно.
3. ~~U2: `ParenBlock`/`CodeBlock` — отдельные ноды или единая параметризованная?~~ ЗАКРЫТО: отдельные ноды (Фаза 4).
4. U3: блоки `change` — препроцессор или постпроцессор? — ОТЛОЖЕНО владельцем (черновик, формат не решён).
5. ~~U3: `const(...)` и множественные метки `var(a,b,c)`~~ — множественные метки ЗАКРЫТО (Фаза 5,
   [`_pp_var_multi_test.py`](../../_examples/.tests/_pp_var_multi_test.py)). `const(...)` остаётся открытым.
