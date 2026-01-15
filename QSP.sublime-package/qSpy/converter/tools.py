# auxiable tools
from typing import List, Literal, TypedDict

QspsLine = str

class BaseFindMode(TypedDict):
    open_base: bool
    quote: List[Literal['"', "'", "{"]]

def parse_string(qsps_line:QspsLine, mode:BaseFindMode) -> None:
    """ Parse opened string for location code and return open string chars """
    for char in qsps_line:
        if not mode['quote']:
            if char in ('"', '\'', '{'): mode['quote'].append(char)
        else:
            if not char in ('"', "'", "{", "}"): continue
            if char in ('"', '\'') and mode['quote'][-1] == char:
                mode['quote'].pop()
            elif char == '}' and mode['quote'][-1] == '{':
                mode['quote'].pop()
            elif char == '{' and not mode['quote'][-1] in ('"', '\''):
                mode['quote'].append(char)
    

if __name__ == "__main__":
    import time
    def test_parse_string():
        # Тест 1: Обычные закрытые двойные кавычки
        mode = {'open_base': False, 'quote': []}
        parse_string('print("Hello, world")', mode)
        assert mode['quote'] == [], f"Закрытые кавычки ошибочно остались в стеке: {mode['quote']}"

        # Тест 2: Незакрытые двойные кавычки
        mode = {'open_base': False, 'quote': []}
        parse_string('print("Hello, world)', mode)
        assert mode['quote'] == ['"'], f"Ожидается незакрытая кавычка: {mode['quote']}"

        # Тест 3: Обычные закрытые одинарные кавычки
        mode = {'open_base': False, 'quote': []}
        parse_string("print('Hello, world')", mode)
        assert mode['quote'] == [], f"Закрытые кавычки ошибочно остались в стеке: {mode['quote']}"

        # Тест 4: Незакрытые одинарные кавычки
        mode = {'open_base': False, 'quote': []}
        parse_string("print('Hello, world)", mode)
        assert mode['quote'] == ["'"], f"Ожидается незакрытая кавычка: {mode['quote']}"

        # Тест 5: Открытый блок скобок без закрытия
        mode = {'open_base': False, 'quote': []}
        parse_string('func({ do_something()', mode)
        assert mode['quote'] == ['{'], f"Ожидается незакрытая фигурная скобка: {mode['quote']}"

        # Тест 6: Открытый блок фигурных скобок внутри двойных кавычек (не учитывается)
        mode = {'open_base': False, 'quote': []}
        parse_string('say("{Hello}")', mode)
        assert mode['quote'] == [], f"Вложенная скобка в кавычках не должна учитываться: {mode['quote']}"

        # Тест 7: Одинарные кавычки внутри двойных (и наоборот)
        mode = {'open_base': False, 'quote': []}
        parse_string('print("He said: \'hi\'")', mode)
        assert mode['quote'] == [], f"Вложенные разные кавычки не должны мешать: {mode['quote']}"

        mode = {'open_base': False, 'quote': []}
        parse_string("print('He said: \"hi\"')", mode)
        assert mode['quote'] == [], f"Вложенные разные кавычки не должны мешать: {mode['quote']}"

        # Тест 8: Незакрытые и закрытые вложенные кавычки и скобки
        mode = {'open_base': False, 'quote': []}
        parse_string('text = "{something', mode)
        assert mode['quote'] == ['"'], f"В стеке только кавычка, т.к. скобка не учитывается: {mode['quote']}"
        parse_string('}', mode)
        assert mode['quote'] == ['"'], f"После закрытия скобки должна остаться кавычка: {mode['quote']}"
        parse_string('"', mode)
        assert mode['quote'] == [], f"Стек должен быть пуст после закрытия кавычки: {mode['quote']}"

        # print("Все тесты parse_string пройдены корректно.")

    # Для ручного запуска
    old = time.time()
    for i in range(100):
        test_parse_string()
    new = time.time()
    print(new - old)
