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

**B4. сканер директив не контекстный → ложные срабатывания** ([`dirs_scanner.py`](../../QSP.sublime-package/qSpy/preprocessor/dirs_scanner.py)).
`_qsps_file_expect` видит `!@pp:` на начале строки (col 0 или после преформаттера) и считает её
директивой, **не зная**, что строка может быть продолжением многострочной строковой литеры или
`{...}`-блока, начатого выше. Директива-подобная строка внутри литеры будет ошибочно исполнена.
Нужен хотя бы минимальный кросс-строчный контекст (открытая кавычка/блок) либо перенос разбора
директив внутрь стадии кода (см. план).

**B5. `pp_int.py:63` — недоинициализированный `Context` + мёртвый код.**
Начальный `_contexts = [{'in_literal_string': False}]` не содержит ключа `loc_open`,
хотя `Context` (TypedDict) его объявляет, а `_loc()`/`_loc_is_open()` обращаются к нему.
`_loc_is_open()` при этом нигде не вызывается (состояние локации ведёт парсер через
`_loc_is_open` в `pp_parser`). Либо довести семантику, либо удалить ключ и метод как мёртвые.

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

**U3. Значения в `var`/присваивании ограничены идентификатором; константы не сделаны.**
`_assignment_dir` ждёт `IDENTIFIER` справа ([`dirs_parser.py:282-294`](../../QSP.sublime-package/qSpy/preprocessor/dirs_parser.py)),
то есть `!@pp:var(name = August)` работает лишь как метка-строка; числовые/кавычковые литералы и
множественные метки (`var(a, b, c)`) — TODO ([preprocessor_todo.md:44-51](./preprocessor_todo.md)).
`const(...)` ([preprocessor_todo.md:53-68](./preprocessor_todo.md)) не реализовано.
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

### Фаза 3. Корректность стадии директив (B2/B3/B4)
- **B2/B3:** в `DirsInt` ввести счётчик глубины `if` (инкремент на `if`-директиве независимо от
  истинности; декремент на `endif`), separate «фрейм режима» от «фрейма условия». На EOF —
  проверка, что стек вернулся к базовому кадру; ошибка при осиротевшем/незакрытом `if`.
- **B4:** добавить в `DirsScaner` отслеживание кросс-строчного контекста (незакрытая кавычка/`{`),
  чтобы не распознавать директивы внутри литер/блоков; ЛИБО перенести распознование `!@pp:`
  внутрь стадии кода (обсудить объём — это крупнее, закладывать отдельной веткой).
- **Q6:** гарантировать verbatim-путь строк при `pp Off`.

### Фаза 4. Стадия кода: честный AST (U2)
- Ввести `ParenBlock`/`CodeBlock` ноды (или единый `GroupBlock` с discriminator), убрать пометку
  «Временно» и `_QUOTES`-костыль. Обновить visitor'ы, printer'ы, `PpInt`-реконструкцию.
- **Q2:** заменить индексные `pop(-2)` в `visit_stmts_line` на явное условие по типу/позиции токена.

### Фаза 5. Новый функционал по грамматике (U3)
- **U1 `nopp`:** НЕ реализуем. Убрать упоминания из `pp_scheme.pest` и `preprocessor_todo.md`,
  снести закомментированные заглушки в `dirs_parser.py` / `pp_dir.py` (`NoppDir`, `NOPP_STMT`).
- **U3:** значения в `var` (числа/строки), далее — множественные метки и `const`; блоки
  `change/by/endchange` — решить: препроцессор vs постпроцессор (доки склоняют к постпроцессору).

### Фаза 6. Синхронизация документации
- Сверить [`pp_scheme.pest`](./pp_scheme.pest) с фактическим поведением после фаз 3–5; расхождения
  фиксировать здесь. Обновить [preprocessor_todo.md](./preprocessor_todo.md) (перенести закрытые пункты).

---

## 4. Открытые вопросы к владельцу
1. B4: лёгкий кросс-строчный контекст в `DirsScaner` или перенос разбора директив в стадию кода?
2. ~~U1: `nopp` — реализуем или вычёркиваем из спецификации?~~ ЗАКРЫТО: вычёркиваем, `off`/`on` достаточно.
3. U2: `ParenBlock`/`CodeBlock` — отдельные ноды или единая параметризованная?
4. U3: блоки `change` — препроцессор или постпроцессор?
