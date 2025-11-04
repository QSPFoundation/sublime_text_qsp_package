from typing import List, Callable

from pp_tokens import PpToken as tkn
from pp_tokens import PpTokenType as tt

import pp_stmts as stm

Stack = List[Callable[(tkn), None]]

class PpParser:

    def __init__(self, tokens:List[tkn]) -> None:
        self._tokens:List[tkn] = tokens

        self._curtok_num:int = 0
        self._curtok:tkn = None

        self._parse_funcs:Stack = [(self._qsps_file_parse, self._curtok_num)]

        self._qsps_file:List[stm.PpStmt] = []
        
        self._parents:Stack = [self._qsps_file]

        # table of statements /exclude recursion/
        # self._stmts_indexes:List[int] = []
        # self._stmts_type:List = [] #list of statements
        # self._stmts_
        # self._stmts_daughters:List[List[int]] = [] # Lists of daughters indexes

    def parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        for j, token in enumerate(self._tokens):
            self._curtok = token
            self._curtok_num = j
            self._parse_funcs[-1](token)

    def _qsps_file_parse(self, t:tkn) -> None:
        """ Распарсиваем целый файл из токенов. """
        if t.ttype == tt.LOC_OPEN:
            ...
        elif t.ttype == tt.OPEN_DIRECTIVE_STMT:
            ...
        elif t.ttype == tt.RAW_LINE:
            self._append_stmt(stm.RawLineStmt(t))
        elif t.ttype == tt.EOF:
            # однозначно последний токен
            return
        else:
            self._error('qsps_file_parse, wrong token')

    # вспомогательные методы
    def _append_stmt(self, stmt:stm.PpStmt) -> None:
        """ Добавляет стэйтмент в список. """
        # связываем элемент и номер
        l = len(self._stmts)
        stmt.index = l
        # добавляем
        self._qsps_file.append(stmt)

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        if self._curtok is not None:
            name = self._curtok.ttype.name
        else:
            name = 'None'
        print(f"Err. {message}: {name} ({self._curtok_num}).")