from typing import List, Dict, Union, Literal, cast, Optional
import re

from .pp_tokens import LineNum
from .pp_tokens import PpTokenType as tt
from .pp_common import QspsLine, MarkedLine

from . import dirs_stmts as stm
from . import pp_expr as expr
from . import pp_dir as dir

from .pp_environment import PpEnvironment
from . import error as er

AstNode = Union[None, bool, str]
Modes = Dict[
    Literal[
        'pp',
        'no_save_comm',
        'include',
    ],
    bool]

class DirsInt(stm.PpVisitor[AstNode], dir.PpVisitor[AstNode], expr.PpVisitor[AstNode]):
    """ Интерпретатор директив препроцессора.
    Размечает строки файла под удаление и сохранение спецкомментариев. """
    def __init__(self,
                 stmts:List[stm.DirStmt[AstNode]],
                 ns:PpEnvironment,
                 qsps_raw_lines:List[str],
                 global_pp:bool=False) -> None:
        self._ns = ns # ссылка на общий для всего препроцессора неймспейс
        self._stmts = stmts
        self._marked_lines:List[MarkedLine] = []
        self._qsps_raw_lines:List[QspsLine] = qsps_raw_lines


        self._is_true:Optional[bool] = None # маркер выполнения условия

        # Структурный стек открытых if: True — блок вычислен и выполнен, False — пропущен
        # (pp был выключен на момент if). Глубина вложенности отвязана от вычисления условий,
        # поэтому парный endif всегда снимает свой фрейм, а не внешний.
        self._if_stack:List[bool] = []

        self._modes:List[Modes] = [{
            'pp': global_pp, # on True preprocessor is work
            'no_save_comm': True, # on True spec-comments don't saves in file
            'include': True, # on True qsps-lines includes in result
        }]

    def get_marked_lines(self) -> List[MarkedLine]:
        return self._marked_lines

    def run(self) -> None:
        """Обработка дерева разбора """
        for stmt in self._stmts:
            stmt.accept(self)

    # Statements

    def visit_pp_directive(self, stmt: stm.DirectiveStmt[AstNode]) -> AstNode:
        sl = (stmt.pref.lexeme_start[0] if stmt.pref else stmt.lexeme.lexeme_start[0])
        el = stmt.end.get_end_pos()[0]
        body = stmt.body

        if isinstance(body, dir.ConditionDir):
            # Каждый if структурно открывает блок, который обязан закрыться парным endif.
            if self._pp_is_on():
                # Условие вычисляется, режимы внутри применяются.
                self._if_stack.append(True) # visit_condition_dir пушит фрейм режимов
                body.accept(self)
                self._marked_lines.extend(self._gen_output(sl, el, True)) # строка if убирается
            else:
                # pp выключён — блок пропускается, но фрейм заводится, чтобы парный
                # endif снял именно его, а не внешний.
                self._if_stack.append(False)
                self._new_modes()
                self._marked_lines.extend(self._gen_output(sl, el)) # строка if остаётся как есть
            return

        if isinstance(body, dir.EndifDir):
            if self._if_stack:
                executed = self._if_stack.pop()
                self._modes.pop() # симметричный pop: и выполненный, и пропущенный if пушили фрейм
                if executed:
                    self._marked_lines.extend(self._gen_output(sl, el, True)) # endif убирается
                else:
                    self._marked_lines.extend(self._gen_output(sl, el)) # endif как есть (в pp-off)
            else:
                # Осиротевший endif (без парного if) — стек режимов не трогаем;
                # при включённом pp строка убирается, иначе проходит как есть.
                if self._pp_is_on():
                    self._marked_lines.extend(self._gen_output(sl, el, True))
                else:
                    self._marked_lines.extend(self._gen_output(sl, el))
            return

        # Прочие директивы
        if self._pp_is_on():
            body.accept(self)
            self._marked_lines.extend(self._gen_output(sl, el, True))
        elif self._is_on_dir(body):
            # !@pp:on возвращает препроцессор даже когда он был выключен
            body.accept(self)
            self._marked_lines.extend(self._gen_output(sl, el, True))
        else:
            # pp выключен — директива проходит в файл дословно
            self._marked_lines.extend(self._gen_output(sl, el))

    def visit_qsps_line(self, stmt: stm.QspsLineStmt[AstNode]) -> AstNode:
        sl = (stmt.pref.lexeme_start[0] if stmt.pref else stmt.value[0].lexeme_start[0])
        el = stmt.value[-1].get_end_pos()[0] if stmt.value else sl
        self._marked_lines.extend(self._gen_output(sl, el))

    # Directives

    def visit_assignments_dir(self, stmt: dir.AssignmentsDir[AstNode]) -> AstNode:
        # var(a, b, c = value, ...): каждый элемент применяется по той же семантике
        for item in stmt.assignments:
            item.accept(self)

    def visit_consts_dir(self, stmt: dir.ConstsDir[AstNode]) -> AstNode:
        # const(a, b, c = 'literal', 123, -1): позиции имён и значений сопоставлены парсером
        # (числа совпадают); каждая пара имя=литерал заводится в таблицу констант со флагом
        # «строковая» (значение — STRING-токен). Метку var не объявляет; подстановка @name
        # выполняется в _gen_output по позиции (строковые константы обрамляются кавычками).
        for item in stmt.assignments:
            # парсер гарантирует литерал-значение у каждой константы (AssignmentDir.value обязан быть задан)
            if item.value is None:
                raise er.DirsInterpreterError(f"const-элемент '{item.key.lexeme}' обязан иметь литерал-значение")
            self._ns.def_const(item.key.lexeme, item.value.lexeme, item.value.ttype == tt.STRING)

    def visit_assignment_dir(self, stmt: dir.AssignmentDir[AstNode]) -> AstNode:
        # объявление переменной (с присвоением, опционально)
        key = stmt.key.lexeme
        if stmt.value is None:
            # просто заводим метку
            self._ns.def_key_set_value(key)
        elif stmt.value.ttype == tt.STRING:
            # литеральное значение ("текст") — храним как есть, не объявляя метку из него
            self._ns.set_literal(key, stmt.value.lexeme)
        else:
            # идентификатор-значение — метка ссылается на другую метку/число (как в label-цепочке)
            self._ns.def_key_set_value(key, stmt.value.lexeme)

    def visit_condition_dir(self, stmt: dir.ConditionDir[AstNode]) -> AstNode:
        # требует разрешения условия. Если условие верно, запускает цепочку переключения режимов
        self._is_true = cast(bool, stmt.condition.accept(self))
        self._new_modes()
        for d in stmt.next_dirs:
            d.accept(self)
        self._is_true = None

    def visit_endif_dir(self, stmt: dir.EndifDir[AstNode]) -> None:
        # endif обрабатывается структурно в visit_pp_directive (работа со стеком if/фреймов);
        # сюда попадаем только если endif встретился вне контекста директивы-обёртки.
        pass


    def visit_on_dir(self, stmt: dir.OnDir[AstNode]) -> AstNode:
        self._pp(cast(Literal['on', 'off'], {
            None:  'on',
            True:  'on',
            False: 'off'
        }[self._is_true]))

    def visit_off_dir(self, stmt: dir.OffDir[AstNode]) -> AstNode:
        self._pp(cast(Literal['on', 'off'], {
            None:  'off',
            True:  'off',
            False: 'on'
        }[self._is_true]))

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
        return bool(left or right)

    def visit_and_expr(self, stmt: expr.AndExpr[AstNode]) -> bool:
        left = stmt.left_oprnd.accept(self)
        right = stmt.right_oprnd.accept(self)
        return bool(left and right)

    def visit_not_expr(self, stmt: expr.NotExpr[AstNode]) -> bool:
        return not bool(stmt.left.accept(self))

    def visit_var_name(self, stmt: expr.VarName[AstNode]) -> Union[str, bool]:
        # строковый литерал-операнд — это значение как есть, а не имя метки
        if stmt.value.ttype == tt.STRING:
            return stmt.value.lexeme
        return self._ns.get_var(stmt.value.lexeme)

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
                if True in (left, right):
                    if bool(left) != bool(right): return False
                elif left != right:
                    return False
            elif op == "!=":
                if True in (left, right):
                    if bool(left) == bool(right): return False
                elif left == right:
                    return False
            else:
                # Неожиданный оператор для EqualExpr — считаем это логической ошибкой.
                raise er.DirsInterpreterError(f"Unknown equality operator {op!r}")

        return True

    # aux funcs
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

    def _is_on_dir(self, body:dir.PpDir[AstNode]) -> bool:
        return isinstance(body, dir.OnDir)

    def _new_modes(self) -> None:
        cur = self._modes[-1]
        self._modes.append(cast(Modes, {}))
        self._modes[-1].update(cur)

    def _gen_output(self, strt_ln:LineNum, end_ln:LineNum, exclude:bool=False) -> List[MarkedLine]:
        """ Генерируем список выходных строк. Текст каждой строки пропускается через
        подстановку констант @name с таблицей, набранной к текущей позиции (строго после
        объявления: DirsInt идёт по директивам в порядке позиций файла). """
        output_lines:List[MarkedLine] = []
        include = False if exclude else self._modes[-1]['include']
        no_save_comm = self._modes[-1]['no_save_comm'] and self._pp_is_on()
        for line in self._qsps_raw_lines[strt_ln:end_ln+1]:
            output_lines.append((self._subst_consts(line), no_save_comm, include))
        return output_lines

    _CONST_RE = re.compile(r'@(\w+)')

    def _subst_consts(self, line:QspsLine) -> QspsLine:
        """ Заменяет каждое вхождение @<имя> на литерал уже объявленной константы.
        Строковая константа обрамляется апострофами: вне текстового литерала '...' — как
        'literal'; внутри литерала '...' — как ''literal'' (спаренные апострофы = экранированный
        апостроф, чтобы вложенный литерал отобразился дословно). Числовая константа вставляется
        как есть, без кавычек, независимо от контекста. Необъявленные @foo остаются как есть;
        рекурсии по результату подстановки нет. Комментарий/код — не различаются. """
        consts = self._ns.get_consts()
        if not consts:
            return line
        inside_sq = self._single_quote_mask(line)
        out:List[str] = []
        pos = 0
        for m in self._CONST_RE.finditer(line):
            out.append(line[pos:m.start()])
            pos = m.end()
            entry = consts.get(m.group(1))
            if entry is None:
                out.append(m.group(0))  # необъявленная @foo — как есть
                continue
            value, is_string = entry
            if not is_string:
                out.append(value)  # число — как есть
            elif inside_sq[m.start()]:
                out.append("''" + value + "''")  # внутри '...' — спаренные апострофы
            else:
                out.append("'" + value + "'")  # вне — одиночные апострофы
        out.append(line[pos:])
        return ''.join(out)

    @staticmethod
    def _single_quote_mask(line:QspsLine) -> List[bool]:
        """ По-символьная маска: True для символов внутри текстового литерала, ограниченного '...'.
        Корректно учитывает двойные кавычки (апостроф внутри "..." — не разделитель) и
        экранирование удвоением ('' внутри '...', "" внутри "..."). """
        inside = [False] * len(line)
        state = 0  # 0 — вне, 1 — внутри '...', 2 — внутри "..."
        i = 0
        n = len(line)
        while i < n:
            c = line[i]
            if state == 0:
                if c == "'":
                    state = 1
                elif c == '"':
                    state = 2
                i += 1
            elif state == 1:
                if c == "'":
                    if i + 1 < n and line[i + 1] == "'":
                        inside[i] = inside[i + 1] = True  # '' — экранированный апостроф
                        i += 2
                    else:
                        state = 0  # закрывающая кавычка
                        i += 1
                else:
                    inside[i] = True
                    i += 1
            else:  # state == 2 — внутри "...": одиночная кавычка не трогает состояние '...'
                if c == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        i += 2  # "" — экранированная кавычка
                    else:
                        state = 0
                        i += 1
                else:
                    i += 1
        return inside
