import uuid
from typing import List, Callable, Dict, Union, Tuple, Optional

from pp_tokens import PpToken as tkn
from pp_tokens import PpTokenType as tt

import pp_stmts as stm

Stack = List[Callable[(tkn), None]]

class PpParser:

    def __init__(self, tokens:List[tkn]) -> None:
        self._tokens:List[tkn] = tokens

        self._curtok_num:int = 0
        self._curtok:tkn = None

        self._parse_machines:Dict[uuid.UUID, Dict[str, Union[Callable, str, uuid.UUID]]] = {
            # uuid-of-machine: {
                # 'machine': Callable,
                # 'state': str,
                # 'parent': uuid.UUID,
                # 'signal': str
            # }
        }
        self._cur_machine:uuid.UUID = uuid.uuid4()
        self._parse_machines[self._cur_machine] = {
            'handle': self._qsps_file_parse,
            'state': 'loc_find',
            'parent': None,
            'signal': 'default',
            'scheme': None
        }

        self._stmts:List[stm.PpStmt] = []

    def parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        while self._cur_machine:
            handle = self._parse_machines[self._cur_machine]['handle']
            state = self._parse_machines[self._cur_machine]['state']
            signal = self._parse_machines[self._cur_machine]['signal']
            parent = self._parse_machines[self._cur_machine]['parent']
            signal = handle(state, signal, self._cur_machine)
            # Машина возвращает сигнал. Этот сигнал передаётся родителю
            # Цикл останавливается, если cm становится None
            ...

    def _qsps_file_parse(self, state:str, signal:str, mid:uuid.UUID) -> str:
        """ Распарсиваем целый файл из токенов. """
        # переключение состояний
        machine = self._parse_machines[mid]
        if not machine.get('scheme'):
            machine['scheme'] = {
                'loc_find': {
                    'default': 'loc_find',
                    'loc_not_found': 'dir_find'
                },
                'dir_find': {
                    'default': 'loc_find',
                    'dir_not_found': 'raw_find'
                },
                'raw_find': {
                    'default': 'loc_find',
                    'raw_not_found': 'eof_find'
                },
                'eof_find': {
                    'default': 'eof_find',
                    'eof_not_found': 'error_eof',
                    'eof_found': 'close_machine'
                },
                'error_eof': {'default': 'error_eof'},
                'close_machine': {'default': 'close_machine'}
            }
        scheme = machine['scheme']
        state = self._state_handler(scheme, state, signal)
        if state == 'close_machine':
            del self._parse_machines[mid] # удаляем машину
            return 'eof'
        if state == 'error_eof':
            del self._parse_machines[mid] # удаляем машину
            self._error('EOF not found.')
            return state
        

    # вспомогательные методы
    def _append_stmt(self, stmt:stm.PpStmt) -> None:
        """ Добавляет стэйтмент в список. """
        # связываем элемент и номер
        l = len(self._stmts)
        stmt.index = l
        # добавляем
        self._qsps_file.append(stmt)

    def _state_handler(self, scheme:Dict[str, Dict[str, str]],
                       state:str, signal:str) -> str:
        """ Переключатель состояний. """
        if signal in scheme[state]:
            return scheme[state][signal]
        else:
            return scheme[state]['default']

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        if self._curtok is not None:
            name = self._curtok.ttype.name
        else:
            name = 'None'
        print(f"Err. {message}: {name} ({self._curtok_num}).")