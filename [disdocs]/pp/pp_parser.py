# from tracemalloc import start
import uuid
from typing import List, Callable, Dict, Optional, Any #, Union, Tuple

from pp_tokens import PpToken as Tkn
from pp_tokens import PpTokenType as tt

import pp_stmts as stm

from pp_state_machine import PpStateMachine as PPSM
from pp_state_machine import PpSmSignal as sgnl

from pp_tree import PpTree

Stack = List[Callable[[Tkn], None]]
PpStmt = stm.PpStmt[Any]


class PpParser:

    def __init__(self, tokens:List[Tkn]) -> None:
        self._tokens:List[Tkn] = tokens

        self._curtok_num:int = 0
        self._curtok:Optional[Tkn] = self._tokens[0] if self._tokens else None

        start_machine = PPSM(self._qsps_file_parse)
        self._cur_machine:uuid.UUID = start_machine.id
        self._parse_machines:Dict[uuid.UUID, PPSM] = {
            self._cur_machine: start_machine
        }

        self._code_tree:PpTree = PpTree()

    def parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        accept_signal = sgnl.DEFAULT
        # self._cur_machine выставлен заранее
        while self._curtok:
            machine:PPSM = self._parse_machines[self._cur_machine]
            accept_signal = machine.handler(machine, accept_signal)
            # Машина возвращает сигнал, который передаётся либо ей же, либо предыдущей, либо новой
            # в любом случае переполучаем id текущей машины, это последняя машина в словаре.
            if not self._parse_machines:
                # если машин больше нет, значит парсинг закончен
                break
            # получаем id последней машины в словаре
            self._cur_machine = list(self._parse_machines.keys())[-1]
        # Здесь возможно нужно разрешение оставшихся сигналов от машин
        ...


    def _qsps_file_parse(self, machine:PPSM, signal:sgnl) -> sgnl:
        """ Распарсиваем целый файл из токенов. """
        # переключение состояний
        machine.state_handler(signal)
        # получаем состояние
        state = machine.state
        # идентификатор машины
        mid = machine.id
        if state == 'close_machine': # найден конец файла
            del self._parse_machines[mid]
            return sgnl.EOF_FOUND
        elif state == 'error_eof': # ошибка поиска конца файла
            # об ошибке сообщает машина поиска конца файла
            del self._parse_machines[mid]
            return sgnl.ERROR
        elif state == 'loc_find':
            # нужно включить поиск локации, для этого создаём машину
            new_machine = PPSM(self._loc_parse, mid, self._curtok_num)
            self._add_machine(new_machine)
        elif state == 'dir_find':
            new_machine = PPSM(self._dir_parse, mid, self._curtok_num)
            self._add_machine(new_machine)
        elif state == 'raw_find':
            new_machine = PPSM(self._rawline_parse, mid, self._curtok_num)
            self._add_machine(new_machine)
        elif state == 'eof_find':
            new_machine = PPSM(self._eof_parse, mid, self._curtok_num)
            self._add_machine(new_machine)
        return sgnl.DEFAULT
        


    def _loc_parse(self, machine:PPSM, signal:sgnl) -> sgnl:
        ...

    def _dir_parse(self, machine:PPSM, signal:sgnl) -> sgnl:
        """ Парсинг директивы препроцессора. """
        machine.state_handler(signal)
        state = machine.state
        mid = machine.id

        if state == 'open_dir_stmt_find':
            # Нужно сопоставить текущий токен, если он не совпал, значит это не директива, а сырая строка
            if self._curtok.ttype == tt.OPEN_DIRECTIVE_STMT:
                # TODO: токен превращается в оператор директивы
                return 'open_dir_stmt_found'
            else:
                del self._parse_machines[mid] # удаляем машину
                return 'dir_not_found'
        if state == 'directive_parse':
            # Создаём машину парсинга непосредственной команды
            new_machine = PPSM(self._directive_parse, mid)
            self._add_machine(new_machine)
            return state
        if state == 'error_parse':
            del self._parse_machines[mid] # удаляем машину
            return 'dir_not_found'
        if state == 'close_machine': # найден конец файла
            del self._parse_machines[mid] # удаляем машину
            return 'dir_found'
        ...

    def _rawline_parse(self, machine:PPSM, signal:sgnl) -> sgnl:
        """ Распарсиваем цепочку токенов для сырой строки. """
        machine.state_handler(signal)
        state = machine.state
        mid = machine.id

        if self._curtok is None:
            # исключительный, невозможный случай
            self._logic_error('Unexpected end of input')
            return sgnl.ERROR
        
        curtok_type = self._curtok.ttype

        if curtok_type == tt.EOF:
            # при наборе токенов для строки, встретить конец файла,
            # значит напороться на ошибку
            del self._parse_machines[mid]
            self._error('Unexpected EOF')
            return sgnl.ERROR

        if state == 'raw_find':
            # поглощаем все токены, кроме eof
            next_token = self._next_peek()
            if next_token is None:
                # это ошибка. Подобный вариант возможен только для токена конца файла, а он обработан
                del self._parse_machines[mid] # удаляем машину
                self._eat_token() # поглощаем токен
                self._error('Unexpected end of input')
                return sgnl.ERROR
            if curtok_type in (tt.RAW_LINE, tt.NEWLINE) or next_token.ttype == tt.EOF:
                # Если текущий токен - токен сырой строки, или токен новой строки,
                # или следующий - токен конца файла:
                tokens_chain:List[Tkn] = self._tokens[machine.start_token:self._curtok_num+1]
                # создаём оператор сырой строки из цепочки токенов
                raw_line = stm.RawLineStmt[None](tokens_chain)
                self._code_tree.handle(raw_line)
                del self._parse_machines[mid]
                self._eat_token() # поглощаем токен
                return sgnl.FOUND
            self._eat_token()
        return sgnl.DEFAULT

    def _eof_parse(self, machine:PPSM, signal:sgnl) -> sgnl:
        """ Ожидаем, что текущий токен — конец файла. """
        # машина обрабатывает только один токен, поэтому нам не нужно
        # как-то альтернативно обрабатывать её состояния или сигналы.
        mid = machine.id
        del self._parse_machines[mid]
        if self._curtok is None:
            # исключительный, невозможный случай
            self._logic_error('Unexpected end of input')
            return sgnl.EOF_NOT_FOUND
        if self._curtok.ttype != tt.EOF:
            self._error('Expected EOF, but got something else')
            return sgnl.EOF_NOT_FOUND
        return sgnl.EOF_FOUND

    # вспомогательные методы
    # def _append_stmt(self, stmt:PpStmt) -> None:
    #     """ Добавляет стэйтмент в список. """
    #     # связываем элемент и номер
    #     l = len(self._stmts)
    #     stmt.index = l
    #     # добавляем
    #     self._stmts.append(stmt)

    def _add_machine(self, machine:PPSM) -> None:
        """ добавляет машину в очередь """
        self._parse_machines[machine.id] = machine
        self._cur_machine = machine.id

    def _next_peek(self) -> Optional[Tkn]:
        """ Возващает следующий токен, если есть; иначе None. """
        sk = self._curtok_num
        return self._tokens[sk + 1] if sk + 1 < len(self._tokens) else None 

    def _eat_token(self) -> None:
        """ Поглощает токен. Т.е. передвигает указатель на следующий. """
        self._curtok_num += 1
        if self._curtok_num >= len(self._tokens):
            self._curtok = None
        else:
            self._curtok = self._tokens[self._curtok_num]

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        if self._curtok is not None:
            name = self._curtok.ttype.name
        else:
            name = 'None'
        print(f"Err. {message}: {name} ({self._curtok_num}).")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")