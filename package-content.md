# Пакет QSP

**Включает в себя:**
* `Completions` — папка, включающая файлы со списком автодополнений ключевых слов QSP.
* `qSpy` — py-пакет вспомогательных скриптов для плагина.
* `QGC` — [QSP Game Converter](https://qsp.org/index.php?option=com_agora&task=topic&id=1339&p=1&prc=25&Itemid=57) от Alex (studentik), ускоряющий сборку проекта на Windows.
* `Snippets` - папка со стандартными сниппетами (фрагментами кода) для QSP.
* `.python-version` - версия встроенного интерпретатора python, в которой будет запускаться плагин
* `Comment Intendation.tmPreferences` - настройка поведения для вставки комментариев.
* `Default.sublime-keymap` - файл настройки сочетаний клавиш при работе с QSP-файлом
* `Indentation Rules.tmPreferences` - файл настройки поведения отступов
* `Location in Goto-List.tmPreferences` - файл настройки распознавания локаций в проекте
* `Markup in Goto-List.tmPreferences` - файл настройки распознавания меток на локации
* `QSP.sublime-build` - файл настройки build-system для сборки файлов `.qsp`.
* `qsp.sublime-syntax` - файл со схемой подсветки синтаксиса QSP
* `qsp_locations.sublime-syntax` - дополнительный файл со схемой подсветки синтаксиса QSP, предназначенный для встраивания подсветки QSP в схемы подсветки других языков.
* `syntax_test_qsp.qsps` - файл с образцом синтаксиса QSP для теста подсветки (не билдится сублаймом).
* `QSP.py` - основная часть плагина ST, где и реализуется весь функционал.