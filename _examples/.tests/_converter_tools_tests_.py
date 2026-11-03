# _converter_tools_tests_.py

if __name__ == "__main__":
    import time
    def test_parse_string():
        mode:ParseStringMode = {'open_base': False, 'quote': []}
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

        # Тест 9: Кавычки внутри фигурных скобок учитываются (закрытый блок)
        mode = {'open_base': False, 'quote': []}
        parse_string("x = {'abc'}", mode)
        assert mode['quote'] == [], f"Закрытый блок с апострофами внутри не должен оставлять слой: {mode['quote']}"

        # Тест 10: Кавычки внутри фигурных скобок учитываются (незакрытая кавычка)
        mode = {'open_base': False, 'quote': []}
        parse_string('text = {"one', mode)
        assert mode['quote'] == ['{', '"'], f"Ожидается слой фигурной скобки и кавычки: {mode['quote']}"
        parse_string('two" }', mode)
        assert mode['quote'] == [], f"Кавычка и скобка должны закрыться по слоям: {mode['quote']}"

        # Тест 11: Вложенные фигурные скобки
        mode = {'open_base': False, 'quote': []}
        parse_string('{{}', mode)
        assert mode['quote'] == ['{'], f"Ожидается одна незакрытая внешняя скобка: {mode['quote']}"

        # Тест 12: Фигурные скобки внутри апострофов не учитываются
        mode = {'open_base': False, 'quote': []}
        parse_string("say = '{не {важно} для стека}' + 'text'", mode)
        assert mode['quote'] == [], f"Скобки в апострофах должны игнорироваться: {mode['quote']}"

        # print("Все тесты parse_string пройдены корректно.")

    # Для ручного запуска
    old = time.time()
    for i in range(100):
        test_parse_string()
    new = time.time()
    print(new - old)