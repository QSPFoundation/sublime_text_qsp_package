from typing import List, Dict, Union, Literal, Callable

from pp_tokens import PpTokenType as tt

import pp_stmts as stm
import pp_expr as expr
import pp_dir as dir

from pp_environment import PpEnvironment

AstNode = Union[None, bool, str]

class PpInt(stm.PpVisitor[AstNode], dir.PpVisitor[AstNode], expr.PpVisitor[AstNode]):

    _SPEC_COMM_TTS = (
        tt.OPEN_DIRECTIVE_STMT,
        tt.LESS_SPEC_COMM,
        tt.SIMPLE_SPEC_COMM
    )

    def __init__(self,
                 stmts:List[stm.PpStmt[AstNode]],
                 ns:PpEnvironment,
                 qsps_raw_lines:List[str]) -> None:
        self._ns = ns # ссылка на общи для всего препроцессора неймспейс
        self._stmts = stmts
        self._qsps_pp_lines:List[str] = []
        self._qsps_raw_lines:List[str] = qsps_raw_lines

        # TODO: сюда должен падать режим от препроцессора.
        # TODO: наверное его стоит прописывать в окружении
        self._modes:Dict[
            Literal['pp', 'no_save_comm', 'open_if', 'include', 'loc'], bool] = {
            'pp': False, # on True preprocessor is work
            'no_save_comm': True, # on True spec-comments don't saves in file
            'open_if': False, # on True condition block is open
            'include': True, # on True qsps-lines includes in result
            'loc': False, # if location is opened - True
        }

    def run(self) -> None:
        """Обработка дерева разбора """
        for stmt in self._stmts:
            stmt.accept(self)

    def visit_raw_line_dclrt(self, stmt: stm.RawLineStmt[AstNode]) -> AstNode:
        # Сырую строку между локациями не возвращаем, обрабатывать её не нужно в любом режиме
        pass

    def visit_pp_directive(self, stmt: stm.PpDirective[AstNode]) -> AstNode:
        # если препроцессор включён, вне зависимости от того, где находится директива
        if self._pp_is_on():
            stmt.body.accept(self) # выполняем
        elif self._loc_is_open():
            # препроцессор выключен, но локация открыта - нужно сохранить директиву
            ...            

    def visit_on_dir(self, stmt: dir.OnDir[AstNode]) -> AstNode:
        # данная директива просто включает препроцессор до конца файла
        self._pp('on')

    def visit_off_dir(self, stmt: dir.OffDir[AstNode]) -> AstNode:
        # данная директива просто выключает препроцессор до конца файла
        self._pp('off')

    def visit_assignment_dir(self, stmt: dir.AssignmentDir[AstNode]) -> AstNode:
        # объявление переменной (с присвоением, опционально)
        key = stmt.key.lexeme
        value = stmt.value.lexeme if stmt.value else ''
        self._ns.def_key_set_value(key, value)
        print(self._ns.get_env())
    

    def visit_bracket_block(self, stmt: stm.BracketBlock[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'BracketBlock',
            'sub': stmt.left.ttype.name,
            'value': stmt.value.accept(self) if stmt.value is not None else None
        }

    def visit_other_stmt(self, stmt: stm.OtherStmt[AstNode]) -> AstNode:
        chain:List[AstNode] = []
        for el in stmt.chain:
            if isinstance(el, tkn.PpToken):
                chain.append(self._token(el))
            else:
                chain.append(el.accept(self))
        return {
            'type': 'stmt',
            'class': 'OtherStmt',
            'value': chain
        }

    def visit_string_literal(self, stmt: stm.StringLiteral[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'StringLiteral',
            'sub': stmt.left.ttype.name,
            'value': [s.accept(self) for s in stmt.value]
        }

    def visit_raw_string_line(self, stmt: stm.RawStringLine[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'RawStringLine',
            'value': [self._token(t) for t in stmt.value]
        }

    def visit_stmts_line(self, stmt: stm.StmtsLine[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'StmtsLine',
            'value': [el.accept(self) for el in stmt.stmts] + ([stmt.comment.accept(self)] if stmt.comment else [])
        }

    def visit_comment_stmt(self, stmt: stm.CommentStmt[AstNode]) -> AstNode:
        # если включён режим исключения строк, ни один комментарий не попадает в выходной файл
        if not self._includes(): return
        # если это обычный комментарий, либо спецкомментарий при включённом режиме сохранения
        # спецкомментариев. Сохраняем спецкомментарии
        sign = stmt.name.ttype
        if sign == tt.EXCLAMATION_SIGN or (sign in self._SPEC_COMM_TTS and self._save_spec_comm())):
            start_line = stmt.name.lexeme_start[0]
            end_line = stmt.value[-1].value.lexeme_start[0]
            new_lines = self._qsps_raw_lines[start_line:end_line+1]
            self._qsps_pp_lines.extend(new_lines)

    def visit_loc_open_dclrt(self, stmt: stm.PpQspLocOpen[AstNode]) -> AstNode:
        if self._includes():
            line = stmt.name.lexeme_start[0] # line from tuple(line, char)
            self._qsps_pp_lines.append(self._qsps_raw_lines[line])
        

    def visit_loc_close_dclrt(self, stmt: stm.PpQspLocClose[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpQspLocClose',
            'sub': stmt.name.ttype.name,
            'value': stmt.name.lexeme
        }

    def visit_pp_literal(self, stmt: stm.PpLiteral[AstNode]) -> AstNode:
        return {
            'type': 'stmt',
            'class': 'PpLiteral',
            'sub': stmt.value.ttype.name,
            'value': stmt.value.lexeme
        }

    def visit_endif_dir(self, stmt: dir.EndifDir[AstNode]) -> None:
        # здесь восстанавливаются значения, работавшие до выполнения условия
        ...

    # def visit_nopp_dir(self, stmt: dir.NoppDir[AstNode]) -> AstNode:
    #     return {
    #         'type': 'dir',
    #         'class': 'NoppDir',
    #         'value': stmt.name.lexeme
    #     }

    def visit_nosavecomm_dir(self, stmt: dir.NoSaveCommDir[AstNode]) -> AstNode:
        # директива выключает сохранение спецкомментариев
        self._no_save_next_comms()

    def visit_savecomm_dir(self, stmt: dir.SaveCommDir[AstNode]) -> AstNode:
        # включает сохранение спецкомментариев
        self._save_next_comms()

    def visit_condition_dir(self, stmt: dir.ConditionDir[AstNode]) -> AstNode:
        # требует разрешения условия. Если условие верно, запускает цепочку переключения режимов
        is_true = stmt.condition.accept(self)
        if is_true:
            for dir in stmt.next_dirs:
                dir.accept(self)
        
    def visit_include_dir(self, stmt: dir.IncludeDir[AstNode]) -> AstNode:
        self._include_next_lines()
        
    def visit_exclude_dir(self, stmt: dir.ExcludeDir[AstNode]) -> AstNode:
        self._exclude_next_lines()
        
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
        return self._ns.get_var(stmt.value.lexeme)
    
    def visit_equal_expr(self, stmt: expr.EqualExpr[AstNode]) -> bool:
        operands = stmt.operands
        operators = stmt.operators
        ok = False
        for i, o in enumerate(operators):
            equal = o.lexeme.strip()
            if equal == '==':
                ok = operands[i].accept(self) == operands[i+1].accept(self)
            elif equal == '!=':
                ok = operands[i].accept(self) != operands[i+1].accept(self)
            else:
                self._error(f'Interpretaton error. Expected equal but get {equal}')
            if not ok: return False
        return ok        

    # aux funcs
    def _includes(self) -> bool:
        """ True if next lines need include in output """
        return self._modes['include']

    def _save_spec_comm(self) -> bool:
        """ True if speccomments need save in output """
        return not self._modes['no_save_comm']

    def _not_save_spec_comm(self) -> bool:
        """ True if speccomments need exclude from project """
        return self._modes['no_save_comm']

    def _include_next_lines(self) -> None:
        self._modes['include'] = True

    def _exclude_next_lines(self) -> None:
        self._modes['include'] = False

    def _save_next_comms(self) -> None:
        """Отключает обработку спецкомментариев"""
        self._modes['no_save_comm'] = False

    def _no_save_next_comms(self) -> None:
        """Включает обработку спецкомментариев"""
        self._modes['no_save_comm'] = True

    def _pp(self, switch:Literal['on', 'off']) -> None:
        if switch == 'on':
            self._modes['pp'] = True
        else:
            self._modes['pp'] = False

    def _pp_is_on(self) -> bool:
        return self._modes['pp']

    def _loc_is_open(self) -> bool:
        return self._modes['loc']

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        print(f"Err. {message}.")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")