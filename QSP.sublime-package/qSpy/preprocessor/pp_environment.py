from typing import Dict, Union, Tuple

class PpEnvironment:
    """ Класс для обслуживания переменных в препроцессоре. """
    def __init__(self) -> None:
        self._labels:Dict[str, Union[str, bool]] = {
            'True': True,
            'False': False
        }
        # Таблица констант: имя -> (литерал без кавычек, is_string).
        # Отделена от _labels: const не объявляет метку var.
        # is_string — значение было STRING-литералом (нужно для обрамления кавычками
        # при подстановке); числа — False (подставляются как есть).
        self._consts:Dict[str, Tuple[str, bool]] = {}

    def def_const(self, name:str, literal:str, is_string:bool) -> None:
        """Объявление константы: имя -> (текстовый литерал, строковая ли она)."""
        name = name.strip()
        self._consts[name] = (literal, is_string)

    def get_consts(self) -> Dict[str, Tuple[str, bool]]:
        return self._consts

    def def_key_set_value(self, key:str, value:str='') -> None:
        self.def_var(key)
        if value:
            self.def_var(value)
            self.set_var(key, value)

    def def_var(self, key:str) -> None:
        """ Объявление переменной. """
        key = key.strip()
        if key in ('True', 'False'): return
        self._labels[key] = key

    def set_var(self, key:str, value:str='') -> None:
        """ Устанавливаем метку или значение """
        key = key.strip()
        if key in ('True', 'False'): return
        value = value.strip()
        if not value: value = key

        self._labels[key] = value

    def set_literal(self, key:str, value:str) -> None:
        """ Задаёт метке литеральное значение как есть, не объявляя value отдельной меткой.
        Используется для var(name = "текст"): в _labels хранится сам текст без кавычек. """
        key = key.strip()
        if key in ('True', 'False'): return
        self._labels[key] = value

    def get_var(self, key:str) -> Union[str, bool]:
        """ Извлекаем значение метки """
        return self._labels.get(key, False)

    def get_env(self) -> Dict[str, Union[str, bool]]:
        return self._labels