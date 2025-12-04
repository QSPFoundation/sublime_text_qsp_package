import pp_stmts as stm
from typing import Any, Union

_Node = stm.PpStmt[Any]
_Data = Union[
    stm.QspsFileBlock[Any],
    stm.RawLineStmt[Any],
    None
]

class PpTree(stm.PpVisitor[Any]):

    """ Класс для построения дерева операторов препроцессинга. """
    def __init__(self) -> None:
        self.tree:stm.QspsFileBlock[Any] = stm.QspsFileBlock([])
        self.current_node:_Node = self.tree
        self.data:_Data = None

    def handle(self, data:Any) -> None:
        """ Обработка данных, переданных в метод. """
        self.data = data
        self.current_node.accept(self)
        self.data = None

    def visit_qsps_file_block(self, stmt:stm.QspsFileBlock[Any]) -> None:
        """ Блок одноуровневых операторов наполняем узлами. """
        if self.data is None:
            return
        stmt.statements.append(self.data)
        # if isinstance(self.data, stm.QspsFileBlock):


    def visit_raw_line_stmt(self, stmt: stm.RawLineStmt[Any]) -> None:
        """ Строка не становится узлом. """