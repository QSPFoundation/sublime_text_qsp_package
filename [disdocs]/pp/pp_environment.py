from typing import Dict, Union

class PpEnvironment:
    """ Класс для обслуживания переменных в препроцессоре. """
    def __init__(self) -> None:
        self._labels:Dict[str, Union[str, bool]] = {
            'True': True,
            'False': False
        }

    def set_var(self, key:str, value:str='') -> None:
        """ Устанавливаем метку или значение """
        key = key.strip()
        if key in ('True', 'False'): return
        value = value.strip()
        if not value: value = key

        self._labels[key] = value

    def upd_var(self, key:str) -> None:
        """ Создание метки из под условия """
        key = key.strip()
        if key in ('True', 'False'): return
        if not key in self._labels:
            self._labels[key] = False

    def get_var(self, key:str) -> Union[str, bool]:
        """ Извлекаем значение метки """
        return self._labels.get(key, False)

    def get_env(self) -> Dict[str, Union[str, bool]]:
        return self._labels