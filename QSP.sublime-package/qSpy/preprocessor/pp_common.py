"""Общий слой препроцессора: словарь типов «строка QSPS + разметка» и мелкие хелперы сканеров.

Модуль не импортирует ничего из `qSpy` — циклов импорта не создаёт.
"""
from typing import List, Literal, Tuple

# ------------------------------ Модель строк ------------------------------ #
# Одна сырая строка исходника.
QspsLine = str
QspsLines = List[QspsLine]

# Флаги разметки строки, которые выставил DirsInt и на которые опирается PpInt:
#   no_save_comm — спецкомментарии в строке удаляются;
#   include_line — строка попадает в выходной файл.
NoSaveComm = Literal[True, False]
IncludeLine = Literal[True, False]
MarkedLine = Tuple[QspsLine, NoSaveComm, IncludeLine]


# ------------------------------ Хелперы сканеров ------------------------------ #
def is_word_char(c: str) -> bool:
    """Символ-«буква/цифра/подчёркивание» (\\w)?"""
    return c.isalnum() or c == '_'


def expected_chars(chars: str) -> List[str]:
    """Ожидаемая последовательность символов в обратном порядке — стек для `pop()`."""
    seq = list(chars)
    seq.reverse()
    return seq
