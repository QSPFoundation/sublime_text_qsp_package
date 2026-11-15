# Пакет QSP

**Включает в себя:**

* `/Completions/` — папка, включающая файлы со списком автодополнений ключевых слов QSP.
* `/qSpy/` — py-пакет вспомогательных скриптов для плагина.
* `/Snippets/` - папка со стандартными сниппетами (фрагментами кода) для QSP.
* `.python-version` - версия встроенного интерпретатора python, в которой будет запускаться плагин
* `Comment Intendation.tmPreferences` - настройка поведения для вставки комментариев.
* `Default.sublime-commands` - файл настройки команд палитры команд (`Ctrl+Shift+P`) для QSP.
* `Default.sublime-keymap` - файл настройки сочетаний клавиш при работе с QSP-файлом
* `Fold.tmPreferences` - файл установки сворачивания локаций.
* `Indentation Rules.tmPreferences` - файл настройки поведения отступов
* `Location in Goto-List.tmPreferences` - файл настройки распознавания локаций в проекте
* `Main.sublime-menu` - файл настройки раздела главного меню для инструментов работы с QSP.
* `Markup in Goto-List.tmPreferences` - файл настройки распознавания меток на локации
* `QSP.py` - основная часть плагина ST, где и реализуется весь функционал.
* `qsp.qloc.sublime-syntax` — файл со схемой подсветки синтаксиса QSP для файлов формата qloc (один файл-одна локация).
* `QSP.sublime-build` - файл настройки build-system для сборки файлов `.qsp`.
* `QSP.sublime-settings` — пути плеера и TXT2GAM-совместимого конвертера (`player_path`, `converter_path`), настройки очистки кэшей workspace (`prune_interval_days`, `orphan_max_age_days`); пользовательские значения задаются в `Packages/User/QSP.sublime-settings`.
* `qsp.sublime-syntax` - файл со схемой подсветки синтаксиса QSP формата TXT2GAM (qsps).
* `qsp_base.sublime-syntax` - технический файл со схемой подсветки синтаксиса QSP.
* Файлы с образцами подсветки синтаксиса QSP:
	* `syntax_test_qsp.qloc`
	* `syntax_test_qsp.qsps`
	* `syntax_test_qsp_loc_end_guard.qsps`
	* `syntax_test_qsp_multiline_headers.qsps`