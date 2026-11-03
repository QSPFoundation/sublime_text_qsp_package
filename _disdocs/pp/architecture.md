# `qSpy/preprocessor`

Рабочий контекст рефакторинга препроцессора. Здесь фиксируются: архитектура,
найденные незакрытые места и логические ошибки, план правок.

Исходники: [`QSP.sublime-package/qSpy/preprocessor`](../../QSP.sublime-package/qSpy/preprocessor)
Грамматика-эталон: [`pp_scheme.pest`](./pp_scheme.pest), [`comment.pest`](./comment.pest)
Постановка/режимы: [`preprocessor_todo.md`](./preprocessor_todo.md), [`pp_modes.canvas`](./pp_modes.canvas)

---
## Архитектура (как есть)

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
