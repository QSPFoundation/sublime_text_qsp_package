# Конвертер `qsp_to_qsps`

Конвертирует бинарный файл QSP-игры (`.qsp`, формат QSPGAME) в текстовый qsps (он же TXT2GAM): разбирает исходник на локации, декодирует текст и раскладывает в qsps-разметку (`# …`, `! BASE`, `*P '…'`, `ACT … END`, `-- …`).

> формат TXT2GAM и qsps — это одно и то же: текстовый файл с особым форматом записи QSP-кода.

Основан на [JS-скрипте Werewolf'а](https://codepen.io/srg-kostyrko/full/QWqdwxv).

`qsp_to_qsps` — это часть пакета `converter`: `QSP.sublime-package/qSpy/converter/qsp_to_qsps.py`.

## Импорт

Класс `QspToQspsBuiltinConv` (и тип ошибки `ValidationFormatError`) экспортируются из пакета. Вне Sublime каталог `QSP` добавляем в `sys.path`:

```python
import sys, os
sys.path.insert(0, os.path.abspath('/Путь к пакету/QSP'))

from qSpy.converter import QspToQspsBuiltinConv
# или точечно: from qSpy.converter.qsp_to_qsps import QspToQspsBuiltinConv, ValidationFormatError
```

## Быстрый старт — один файл

```python
out_path = QspToQspsBuiltinConv().convert_file('tooloz.qsp')
```

`convert_file(input_file='')` — полный цикл в один вызов (чтение → разбор → конверсия → запись). Возвращает путь к созданному `.qsps`; при отсутствии файла или ошибке формата печатает сообщение и возвращает `''`. Результат пишется рядом с исходником под тем же именем (`tooloz.qsp` → `tooloz.qsps`).

## Пошаговый конвейер — гибкая работа

Полный цикл состоит из независимых этапов — можно вмешаться между ними (сконвертировать выборочно, обойти часть локаций и т.п.):

```python
c = QspToQspsBuiltinConv()
c.read_from_file('tooloz.qsp')   # выбрать кодировку, заполнить c._game_lines
c.split_qsp()                    # разобрать и декодировать → c._locations
locs = c.get_locations()         # список локаций-словарей (см. ниже)
c.to_qsps()                      # отконвертировать всё в c._qsps_lines (ничего НЕ возвращает)
c.save_to_file('out.qsps')       # записать; путь необязателен — по умолчанию свой
```

Важно: `to_qsps()` накапливает строки в поле `_qsps_lines` и не отдаёт текст наружу. `convert_location(location)` — статический, возвращает **список строк** одной локации (удобно для поштучной обработки).

## Методы экземпляра

| метод                                   | назначение                                                         |
| --------------------------------------- | ------------------------------------------------------------------ |
| `convert_file(input_file='') -> Path`   | весь цикл сразу; путь к `.qsps` или `''` при ошибке                |
| `read_from_file(input_file='') -> None` | подобрать кодировку, прочитать в `_game_lines`, задать пути        |
| `split_qsp() -> None`                   | разобрать `_game_lines` на `_locations`, декодировать              |
| `to_qsps() -> None`                     | сконвертировать `_locations` → накопить в `_qsps_lines`            |
| `save_to_file(output_file='') -> None`  | записать `_qsps_lines` (UTF-8); путь по умолчанию — `_output_file` |
| `get_locations() -> List[dict]`         | список разобранных локаций                                         |

### Подбор кодировки

`read_from_file` перебирает `['utf-16-le', 'utf-8-sig', 'utf-8', 'cp1251']` и берёт ту, в которой первая строка читается как `QSPGAME`. Канон `.qsp` (QGen 4.3.0-b1 / txt2gam 0.4.0) — **UTF-16LE без BOM, CRLF** (плюс легаси cp1251), поэтому `utf-16-le` идёт первым.

## Статические хелдеры декода и конверсии

```python
QspToQspsBuiltinConv.decode_qsp_line(line)        # декод: сдвиг кодовой точки на +5 (QSP_CODREMOV)
QspToQspsBuiltinConv.decode_cp1251_qsp_line(line) # декод для легаси cp1251 (побайтовый сдвиг)
QspToQspsBuiltinConv.escape_qsp_string(s)         # апострофы → ''  (экранирование от кода QSP)

QspToQspsBuiltinConv.convert_location(location)   # -> List[str]  (одна локация)
QspToQspsBuiltinConv.convert_description(desc)    # -> List[str]  (*P '…')
QspToQspsBuiltinConv.convert_actions(actions)     # -> List[str]
QspToQspsBuiltinConv.convert_action(action)       # -> List[str]  (ACT … END)
```

Все `convert_*` возвращают список строк qsps, а не склеенный текст.

## Ошибки: `ValidationFormatError`

Единый типизированный канал для битого входа:

- ни одна кодировка не дала заголовок `QSPGAME` (в `read_from_file`);
- файл короче 4 строк; заголовок не `QSPGAME` (старый формат — не поддерживается);
- обрезанный файл (ожидалась строка за границей); нечисловое поле числа локаций/действий (в `split_qsp`).

`convert_file` и сплиттер ловят эту ошибку (печатают и продолжают/отменяют разбор). При **расхождении** заявленного и фактического числа локаций — в консоль выводится предупреждение, но разбор продолжается.

## Формат результата

Первые строки `.qsps` описывают **исходный** `.qsp` и стоят до первой локации (то есть при сборке проекта обратно, в игру не попадут):

```qsp
QSP-Game tooloz
Число локаций: 134
Пароль на исходном файле: Pass

# Название локации
! BASE
*P 'базовое описание'
ACT 'имя действия':
    код действия
END
! END BASE
код при посещении
-- Название локации ---------------------------------

```

(секция `! BASE … ! END BASE` опускается, если у локации нет ни описания, ни действий; `No` в строке пароля означает «пароль не установлен»).

## Структуры данных

Локация (`get_locations()` и аргументы `convert_*`) — словарь:

```python
{
    "name": str,          # название локации
    "desc": str,          # базовое описание (сырая декодированная строка, может быть многострочной)
    "run_to_visit": List[str],  # код «выполнить при посещении», строки с переводами
    "actions": List[dict] # базовые действия
}
```

Действие:

```python
{
    "image": str,         # картинка действия (пусто — без картинки)
    "name": str,          # название действия
    "code": List[str]     # код действия, строки с переводами
}
```

## Поля экземпляра

Все служебные поля приватные (с `_`): `_input_file`, `_output_folder`, `_file_name`, `_output_file`, `_game_lines` (исходник), `_qsps_lines` (результат), `_locations`, `_location_count`, `_password`, `_encoding`, `_encode_handler`.
