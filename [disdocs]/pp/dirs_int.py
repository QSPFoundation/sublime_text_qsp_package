from typing import List, Dict, Union, Literal, Tuple, cast, Optional

# from pp_tokens import PpTokenType as tt
from pp_tokens import LineNum

import dirs_stmts as stm
import pp_expr as expr
import pp_dir as dir

from pp_environment import PpEnvironment

AstNode = Union[None, bool, str]
Modes = Dict[
    Literal[
        'pp',
        'no_save_comm',
        'open_if',
        'include',
    ],
    bool]
QspsLine = str
NoSaveComm = Literal[True, False]
IncludeLine = Literal[True, False]
OutputLine = Tuple[
    QspsLine,
    NoSaveComm,
    IncludeLine
]

class DirsInt(stm.PpVisitor[AstNode], dir.PpVisitor[AstNode], expr.PpVisitor[AstNode]):
    """ Интерпретатор директив препроцессора.
    Размечает строки файла под удаление и сохранение спецкомментариев. """
    def __init__(self,
                 stmts:List[stm.DirStmt[AstNode]],
                 ns:PpEnvironment,
                 qsps_raw_lines:List[str]) -> None:
        self._ns = ns # ссылка на общий для всего препроцессора неймспейс
        self._stmts = stmts
        self._output_lines:List[OutputLine] = []
        self._qsps_raw_lines:List[QspsLine] = qsps_raw_lines


        self._is_true:Optional[bool] = None # маркер выполнения условия
        # TODO: сюда должен падать режим от препроцессора.
        # TODO: наверное его стоит прописывать в окружении
        self._modes:List[Modes] = [{
            'pp': True, # on True preprocessor is work
            'no_save_comm': True, # on True spec-comments don't saves in file
            'open_if': False, # on True condition block is open. На старте условие всегда закрыто!
            'include': True, # on True qsps-lines includes in result
        }]

    def get_output_lines(self) -> List[OutputLine]:
        return self._output_lines

    def run(self) -> None:
        """Обработка дерева разбора """
        for stmt in self._stmts:
            stmt.accept(self)
            print(self._output_lines[-1], self._modes)

    # Statements

    def visit_pp_directive(self, stmt: stm.DirectiveStmt[AstNode]) -> AstNode:
        # если (препроцессор включён) или (отключен блоком условия и это конец условия)
        sl = (stmt.pref.lexeme_start[0] if stmt.pref else stmt.lexeme.lexeme_start[0])
        el = stmt.end.get_end_pos()[0]
        if self._pp_is_on() or self._is_endif(stmt.body):
            stmt.body.accept(self) # выполняем
            self._output_lines.extend(self._gen_output(sl, el, True))
        else:
            # препроцессор выключен, 
            self._output_lines.extend(self._gen_output(sl, el))

    def visit_qsps_line(self, stmt: stm.QspsLineStmt[AstNode]) -> AstNode:
        sl = (stmt.pref.lexeme_start[0] if stmt.pref else stmt.value[0].lexeme_start[0])
        el = stmt.value[-1].get_end_pos()[0] if stmt.value else sl
        self._output_lines.extend(self._gen_output(sl, el))  

    # Directives

    def visit_assignment_dir(self, stmt: dir.AssignmentDir[AstNode]) -> AstNode:
        # объявление переменной (с присвоением, опционально)
        key = stmt.key.lexeme
        value = stmt.value.lexeme if stmt.value else ''
        self._ns.def_key_set_value(key, value)

    def visit_condition_dir(self, stmt: dir.ConditionDir[AstNode]) -> AstNode:
        # требует разрешения условия. Если условие верно, запускает цепочку переключения режимов
        self._is_true = cast(bool, stmt.condition.accept(self))
        self._new_modes()
        self._modes[-1]['open_if'] = True # текущий - режим открытого условия
        for dir in stmt.next_dirs:
            dir.accept(self)
        self._is_true = None

    def visit_endif_dir(self, stmt: dir.EndifDir[AstNode]) -> None:
        # здесь восстанавливаются значения, работавшие до выполнения условия
        # Закрыватся условие очень просто. Удаляем последний элемент списка
        if self._if_is_open():
            self._modes.pop()


    def visit_on_dir(self, stmt: dir.OnDir[AstNode]) -> AstNode:
        self._pp(cast(Literal['on', 'off'], {
            None:  'on',
            True:  'on',
            False: 'off'
        }[self._is_true]))

    def visit_off_dir(self, stmt: dir.OffDir[AstNode]) -> AstNode:
        mode = cast(Literal['on', 'off'], {
            None:  'off',
            True:  'off',
            False: 'on'
        }[self._is_true])
        self._pp(mode)
        print(mode)

    def visit_nosavecomm_dir(self, stmt: dir.NoSaveCommDir[AstNode]) -> AstNode:
        {
            None:   self._no_save_next_comms,
            True:   self._no_save_next_comms,
            False:  self._save_next_comms
        }[self._is_true]()

    def visit_savecomm_dir(self, stmt: dir.SaveCommDir[AstNode]) -> AstNode:
        {
            None:   self._save_next_comms,
            True:   self._save_next_comms,
            False:  self._no_save_next_comms
        }[self._is_true]()

    def visit_include_dir(self, stmt: dir.IncludeDir[AstNode]) -> AstNode:
        {
            None:   self._include_next_lines,
            True:   self._include_next_lines,
            False:  self._exclude_next_lines
        }[self._is_true]()
        
    def visit_exclude_dir(self, stmt: dir.ExcludeDir[AstNode]) -> AstNode:
        {
            None:   self._exclude_next_lines,
            True:   self._exclude_next_lines,
            False:  self._include_next_lines
        }[self._is_true]()
        
    def visit_cond_expr_stmt(self, stmt: dir.CondExprStmt[AstNode]) -> AstNode:
        return stmt.expr.accept(self)

    def visit_or_expr(self, stmt: expr.OrExpr[AstNode]) -> bool:
        left = stmt.left_oprnd.accept(self)
        right = stmt.right_oprnd.accept(self)
        print(('or', left, right))
        return bool(left or right)
        
    def visit_and_expr(self, stmt: expr.AndExpr[AstNode]) -> bool:
        left = stmt.left_oprnd.accept(self)
        right = stmt.right_oprnd.accept(self)
        print(('and', left, right))
        return bool(left and right)

    def visit_not_expr(self, stmt: expr.NotExpr[AstNode]) -> bool:
        print(('not'))
        return not bool(stmt.left.accept(self))
        
    def visit_var_name(self, stmt: expr.VarName[AstNode]) -> Union[str, bool]:
        v = self._ns.get_var(stmt.value.lexeme)
        print(('varname', v))
        return v
    
    def visit_equal_expr(self, stmt: expr.EqualExpr[AstNode]) -> bool:
        """
        Реализует сравнение, как в Python:
        a == b == c  -> (a == b) and (b == c)
        a != b != c  -> (a != b) and (b != c)
        и т.д. для смешанных == / !=.
        Операнды вычисляются один раз.
        """
        # Сначала вычисляем все операнды ровно по одному разу,
        # чтобы не было повторной оценки (как в цепочках сравнений Python).
        values = [op.accept(self) for op in stmt.operands]
        operators = stmt.operators

        print(("equals", values))

        # Если по какой‑то причине операторов нет, просто приводим
        # единственный операнд к bool (на практике сюда, вероятно, не попадаем).
        if not operators:
            return bool(values[0]) if values else False

        # Проверяем цепочку сравнений слева направо,
        # но не выполняем лишних логических операций.
        for i, token in enumerate(operators):
            op = token.lexeme.strip()
            left = values[i]
            right = values[i + 1]

            if op == "==":
                if left != right: return False
            elif op == "!=":
                if left == right: return False
            else:
                # Неожиданный оператор для EqualExpr — считаем это логической ошибкой.
                self._logic_error(f"Unknown equality operator {op!r}")
                return False

        return True

    # aux funcs
    def _if_is_open(self) -> bool:
        return self._modes[-1]['open_if']

    def _includes(self) -> bool:
        """ True if next lines need include in output """
        return self._modes[-1]['include']

    def _save_spec_comm(self) -> bool:
        """ True if speccomments need save in output """
        return not self._modes[-1]['no_save_comm']

    def _not_save_spec_comm(self) -> bool:
        """ True if speccomments need exclude from project """
        return self._modes[-1]['no_save_comm']

    def _include_next_lines(self) -> None:
        self._modes[-1]['include'] = True

    def _exclude_next_lines(self) -> None:
        self._modes[-1]['include'] = False

    def _save_next_comms(self) -> None:
        """Отключает обработку спецкомментариев"""
        self._modes[-1]['no_save_comm'] = False

    def _no_save_next_comms(self) -> None:
        """Включает обработку спецкомментариев"""
        self._modes[-1]['no_save_comm'] = True

    def _pp(self, switch:Literal['on', 'off']) -> None:
        self._modes[-1]['pp'] = (switch == 'on')

    def _pp_is_on(self) -> bool:
        return self._modes[-1]['pp']

    def _is_endif(self, body:dir.PpDir[AstNode]) -> bool:
        return self._modes[-1]['open_if'] and isinstance(body, dir.EndifDir)

    def _new_modes(self) -> None:
        cur = self._modes[-1]
        self._modes.append({})
        self._modes[-1].update(cur)

    def _gen_output(self, strt_ln:LineNum, end_ln:LineNum, exclude:bool=False) -> List[OutputLine]:
        """ Генерируем список выходных строк. """
        output_lines:List[OutputLine] = []
        include = False if exclude else self._modes[-1]['include']
        no_save_comm = self._modes[-1]['no_save_comm']
        for line in self._qsps_raw_lines[strt_ln:end_ln+1]:
            output_lines.append((line, no_save_comm, include))
        return output_lines

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        print(f"Err. {message}.")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")