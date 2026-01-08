from typing import Dict, Union

class PpEnvironment:
    """ Класс для обслуживания переменных в препроцессоре. """
    def __init__(self) -> None:
        self._labels:Dict[str, Union[str, bool]] = {
            'True': True,
            'False': False
        }

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

    def get_var(self, key:str) -> Union[str, bool]:
        """ Извлекаем значение метки """
        return self._labels.get(key, False)

    def get_env(self) -> Dict[str, Union[str, bool]]:
        return self._labels