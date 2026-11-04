# Конвертер `qsps_to_qsp`

Собирает бинарный файл QSP-игры (`.qsp`, формат QSPGAME) из текстовых qsps-файлов (он же TXT2GAM): разбирает qsps на локации, выделяет базовые описания/действия и кодирует текст в формат `.qsp`.

> формат TXT2GAM и qsps — это одно и то же: текстовый файл с особым форматом записи QSP-кода.

Основан на [JS-скрипте Werewolf'а](https://codepen.io/srg-kostyrko/full/QWqdwxv).
`qsps_to_qsp` — это часть пакета `converter` (`QSP.sublime-package/qSpy/converter/converters.py`), разбитая на несколько модулей.

## Импорт

```python
import sys, os
sys.path.insert(0, os.path.abspath('/Путь к установленному пакету/QSP'))

from qSpy.converter import QspsToQspBuiltinConv, QspsToQspOuterConv, QspsFile, QspsLoc
```

## Два режима конвертации

Оба наследуют абстрактный `QspsToQspConverter` и строятся одинаково:

```python
Conv(output_file, save_temp_files, conv_path='', conv_args='')
```

- `output_file` — путь целевого `.qsp` (у builtin — дефолт для `save_to_file`; у outer — куда внешний конвертер пишет файл).
- `save_temp_files` — сохранять ли промежуточные файлы.
- `conv_path` / `conv_args` — путь к внешнему конвертеру и строка доп. аргументов (нужны только `QspsToQspOuterConv`; builtin их намеренно игнорирует).

| класс                  | что делает                                                          |
| ---------------------- | ------------------------------------------------------------------- |
| `QspsToQspBuiltinConv` | кодирует в памяти (свой енкодер), пишет `.qsp` сам                  |
| `QspsToQspOuterConv`   | запускает внешний конвертер (ориентир — txt2gam) через `subprocess` |

## Основной способ — сборка проекта (BuildQSP)

Штатная точка входа — не прямое использование класса, а сборка проекта из `qsp-project.json` через `qSpy.builder.BuildQSP`. Он по ключу `converter.capi` выбирает реализацию (`'builtin'` → встроенный, иначе внешний), прогоняет препроцессор и для каждого модуля делает цикл:

```python
converter = Conv(module_path, save_temp_files, conv_path, conv_args)
converter.convert_lines(src_lines)   # собрать game-строки (builtin) или запустить внешний (outer)
converter.save_to_file()             # builtin: записать .qsp; outer: no-op (файл уже создан)
converter.handle_temp_file()         # builtin: debug-дамп; outer: удалить temp-вход
```

## Методы экземпляра (builtin)

| метод                                           | назначение                                                                   |
| ----------------------------------------------- | ---------------------------------------------------------------------------- |
| `convert_lines(qsps_lines) -> List[str]`        | строки qsps → список закодированных строк `.qsp` (в память, ничего не пишет) |
| `convert_file(input_file, output_file) -> None` | прочитать qsps-файл → `convert_lines` → `save_to_file`                       |
| `save_to_file(output_file='') -> None`          | записать `_game_lines`; путь по умолчанию — `output_file` из конструктора    |
| `handle_temp_file() -> None`                    | если `save_temp_files` — записать рядом `.txt`-дамп исходных qsps-строк      |
| `encode_qsps_line(line) -> str`                 | статический; закодировать одну qsps-строку (см. «Правило кодирования»)       |

Три штатных сценария: строки→строки (`convert_lines`), файл→файл (`convert_file`), строки→файл (`convert_lines` + `save_to_file`).

## Внешний конвертер (outer)

`convert_lines(qsps_lines)` пишет qsps во временный `.txt`, запускает `[conv_path, temp.txt, output_file, conv_args?]` и **возвращает `[]`** — продукт (`.qsp`) внешний конвертер кладёт на диск сам, in-memory строк не производит. `save_to_file` — заглушка (`pass`), `handle_temp_file` удаляет temp-вход, если не просили сохранить. `convert_file` у outer существует только ради контракта ABC и builder'ом не вызывается.

## Правило кодирования строки (сдвиг «±5»)

Отдельного метода кодирования символа нет — вся qsps-строка кодируется за один вызов `str.translate` по неизменяемой таблице `ENCODE_TABLE`:

```python
qsp_line = qsps_line.translate(ENCODE_TABLE)   # cp → cp - 5 (QSP_CODREMOV = 5)
```

- Кодирование `qsps → qsp` — чистый посимвольный сдвиг кодовой точки на `-5` (обратная операция декода `qsp → qsps` — `+5`).
- Таблица строится один раз при импорте, покрывает **BMP** начиная с `U+0006`; **неизменяемая**, только читается → `encode_qsps_line` безопасно звать из `ThreadPoolExecutor` (гонки общего кэша нет).
- Точки `< 6` не сдвигаются; астральные символы (`> U+FFFF`, эмодзи) `translate` оставляет без изменения — движок QSP фактически BMP-only.
- Базовая (`! BASE`) и служебные части локации парсятся потоком из 32 воркеров (`ThreadPoolExecutor`), порядок результатов сохраняется (`executor.map`).

## Структура выходного `.qsp`

Записывается в **UTF-16LE без BOM**, перевод строк — **CRLF** (`newline=''`, канон реальных QGen/txt2gam). Первые две строки — открытый текст, далее закодированные поля:

```qsp
QSPGAME
SublimeText QSP-Package
<код 'No'>          # пароль (qsps метаданных не несёт → всегда дефолт 'No')
<код числа локаций>
<код имени локации><CR><LF>
<код базового описания><CR><LF>
<код «выполнить при посещении»><CR><LF>
<код числа действий><CR><LF>
  ...по 3 строки на каждое действие (image, name, code)...
```

## Разбор локаций: `QspsFile` и `QspsLoc`

qsps-текст представляет собой поток локаций: начало `# <имя>`, конец `-- <имя> ---…` (хвост из ≥3 дефисов — эталонный маркер). Внутри — блок `! BASE … ! END BASE` (базовое описание `*P '…'` и действия `ACT … END`) и код «выполнить при посещении».

### `QspsFile` — файл целиком

| метод                                                 | назначение                                                               |
| ----------------------------------------------------- | ------------------------------------------------------------------------ |
| `QspsFile(qsps_lines=None)`                           | создать; можно сразу передать список строк                               |
| `read_from_file(input_file)` / `set_src_lines(lines)` | заполнить исходные строки                                                |
| `split_to_locations()`                                | разобрать строки на `QspsLoc` (учёт кавычек/скобок через `parse_string`) |
| `get_locations() -> List[QspsLoc]`                    | список локаций                                                           |
| `get_loc_symbols()`                                   | пары `(имя, регион)`                                                     |
| `get_src()` / `file_name()` / `file_path()`           | доступ к исходным строкам и путям                                        |

### `QspsLoc` — одна локация

Создаётся сразу с данными и автоматически извлекает base при конструировании: `QspsLoc(name, code, region)`.

| метод                                                | возвращает / делает                                                              |
| ---------------------------------------------------- | -------------------------------------------------------------------------------- |
| `name()` / `desc()` / `actions()` / `run_on_visit()` | имя, базовое описание (строка), список действий, код при посещении (`List[str]`) |
| `split_base()`                                       | разобрать base: scanner → parser → interpreter; заполнить `desc`/`actions`       |
| `base_errors()`                                      | накопленные диагностики разбора base (с именем локации)                          |
| `get_sources()`                                      | собрать qsps-текст локации обратно (для round-trip; не `.qsp`)                   |

`actions()` отдаёт список словарей:

```python
{ 'image': str, 'name': str, 'code': List[str] }   # code — строки кода действия
```

### Единый канал ошибок base-разбора

`ParserError` (парсер) и `RuntimeIntError` (интерпретатор) больше не роняют сборку и не глотаются молча: они накапливаются в `base_errors()` и печатаются в консоль с именем локации; сборка продолжается. Незакрытый `! BASE` — base не выделяется, весь код уходит в `run_on_visit`, печатается предупреждение.

## Поля экземпляра (внутренние)

У конвертера приватные: `_module_path` (цель), `_temp_file_path`, `_game_lines` (результат), `_qsps_file` (у builtin); у outer — `_conv_path`, `_conv_args`. У `QspsLoc`: `_name`, `_code`, `_base_code`, `_base_desc`, `_base_actions`, `_run_on_visit`, `_base_errors`.
