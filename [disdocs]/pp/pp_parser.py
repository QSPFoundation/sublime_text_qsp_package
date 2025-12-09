# from tracemalloc import start
from typing import List, Callable, Union, Optional, Any # Dict, Tuple, cast

from pp_tokens import PpToken as Tkn
from pp_tokens import PpTokenType as tt

import pp_stmts as stm
import pp_dir as dir
import pp_expr as expr

Stack = List[Callable[[Tkn], None]]
PpStmt = stm.PpStmt[Any]

class PpParser:

    def __init__(self, tokens:List[Tkn]) -> None:
        self._tokens:List[Tkn] = tokens

        # валидация цепочки токенов
        
        if not self._tokens:
            self._logic_error(f'Init-stage. Tokens-chain is empty')
            return None
        if self._tokens and self._tokens[-1].ttype != tt.EOF:
            self._logic_error(f'There is not EOF in tokens-chain on initial stage')
            self._tokens.append(Tkn(tt.EOF, '', None, (-1,-1)))        

        self._curtok_num:int = 0
        self._curtok:Tkn = self._tokens[0]

        self._loc_is_open:bool = False

        self._qsps_file:List[PpStmt] = []

    def qsps_file_parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        statements = self._qsps_file
        while not self._is_eof():
            statements.append(self._declaration())
        ...


    def _declaration(self) -> stm.PpStmt[None]:
        """ Распарсиваем целый файл из токенов. """
        # запоминаем стартовый токен
        start_declaration:int = self._curtok_num
        if self._loc_is_open:
            ...
        else:
            # _open_loc
            if self._check_type(tt.LOC_OPEN):
                return self._open_loc()
            elif self._check_type(tt.RAW_LINE):
                return self._raw_line()
            elif self._check_type(tt.OPEN_DIRECTIVE_STMT):
                validate_directive:Optional[stm.PpDirective[None]] = self._directive()
                if validate_directive:
                    return validate_directive
                else:
                    self._reset_curtok(start_declaration)
                    return self._raw_line_eating()
            else:
                self._logic_error(f'Expected LOC_OPEN, RAW_LINE or OPEN_DIR_STMT. Get {self._curtok.ttype.name}')
        ...

    def _directive(self) -> Optional[stm.PpDirective[None]]:
        """ Получаем директиву препроцессора, если возможно. """
        self._eat_tokens(1) # пожираем токен объявления директивы
        start_declaration:int = self._curtok_num
        next_is_newline = self._next_peek().ttype == tt.NEWLINE
        if self._curtok.ttype == tt.ENDIF_STMT and next_is_newline:
            body = dir.EndifDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.PpDirective(body)
        if self._curtok.ttype == tt.NOPP_STMT and next_is_newline:
            body = dir.NoppDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.PpDirective(body)
        if self._curtok.ttype == tt.OFF_STMT and next_is_newline:
            body = dir.OffDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.PpDirective(body)
        if self._curtok.ttype == tt.ON_STMT and next_is_newline:
            body = dir.OnDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.PpDirective(body)
        if self._curtok.ttype == tt.NO_SAVECOMM_STMT and next_is_newline:
            body = dir.NoSaveCommDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.PpDirective(body)
        if self._curtok.ttype == tt.SAVECOMM_STMT and next_is_newline:
            body = dir.SaveCommDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.PpDirective(body)
        if self._curtok.ttype == tt.VAR_STMT:
            assignment_validation:Optional[dir.AssignmentDir[None]] = self._assignment_dir()
            if assignment_validation is None:
                return None
            return stm.PpDirective[None](assignment_validation)
        if self._check_type(tt.IF_STMT):
            condition_validation:Optional[dir.ConditionDir[None]] = self._condition_dir()
            if condition_validation is None: return None
            return stm.PpDirective[None](condition_validation)
        ... # if statement

    def _condition_dir(self) -> Optional[dir.ConditionDir[None]]:
        """ Получаем директиву условия """
        self._eat_tokens(1) # пожирем IF_STMT
        if not self._check_type(tt.LEFT_PAREN):
            self._error(f'Expected LEFT_PAREN')
            return None
        self._eat_tokens(1)
        cond_expr_validation:Optional[dir.CondExprStmt[None]] = self._cond_expr_stmt()
        if cond_expr_validation is None: return None
        condition_expr:dir.CondExprStmt[None] = cond_expr_validation
        if not self._check_type(tt.RIGHT_PAREN):
            self._error(f'Expected RIGHT_PAREN')
            return None
        self._eat_tokens(1)
        if not self._check_type(tt.THEN_STMT):
            self._error(f'Expected THEN_STMT')
            return None
        self._eat_tokens(1)
        next_dirs_validation:List[dir.NextDir] = self._next_dirs()
        if not next_dirs_validation: return None
        next_dirs:List[dir.NextDir] = next_dirs_validation
        # на данном этапе у нас не поглощён только токен следующей строки
        self._eat_tokens(1)
        return dir.ConditionDir(condition_expr, next_dirs)

    def _cond_expr_stmt(self) -> Optional[dir.CondExprStmt[None]]:
        """ Получаем выражение условия """
        or_validation:Optional[expr.OrExpr[None]] = self._or()
        if or_validation is None: return None
        return dir.CondExprStmt(or_validation)

    def _or(self) -> Optional[expr.OrExpr[None]]:
        """ Получаем выражение OR """
        and_validation:Optional[expr.AndExpr[None]] = self._and()


    def _not(self) -> Optional[expr.NotType[None]]:
        """ Получаем выражение с оператором отрицания """
        # NotExpr = notOperator? EqualExpr
        if self._check_type(tt.NOT_OPERATOR):
            operator = self._curtok
            self._eat_tokens(1)
            validation_equal = self._equal()
            if validation_equal is None: return None # если есть ошибка в сравнениях, значит это невалидная директива
            right = validation_equal
            return expr.NotExpr(operator, right)

        validation_equal = self._equal()
        return validation_equal if not validation_equal is None else None
            

    def _equal(self) -> Optional[expr.EqualType[None]]:
        """ Получаем выражение сравнения """
        if not self._check_type(tt.IDENTIFIER):
            self._error('Expected IDENTIFIER (ex. var name)')
            return None
        equal_expr = expr.VarName[None](self._curtok) # TODO: добавлять идентификаторы в окружение на каждом этапе
        self._eat_tokens(1)
        while self._match(tt.EQUAL_EQUAL, tt.EQUAL_NOT_EQUAL):
            operator = self._curtok
            self._eat_tokens(1)
            if not self._check_type(tt.IDENTIFIER):
                self._error('Expected IDENTIFIER (ex. var name)')
                return None
            right = expr.VarName[None](self._curtok)
            self._eat_tokens(1)
            equal_expr = expr.EqualExpr[None](equal_expr, operator, right)
        return equal_expr

    def _assignment_dir(self) -> Optional[dir.AssignmentDir[None]]:
        """Получаем директиву присваивания"""
        self._eat_tokens(1) # пожираем токен оператора присваивания
        # далее должен идти токен скобки
        if not self._check_type(tt.LEFT_PAREN):
            self._error(f'Expected LEFT_PAREN')
            return None
        self._eat_tokens(1) # поглотили токен скобки
        # далее идёт идентификатор
        if not self._check_type(tt.IDENTIFIER):
            self._error('Expected VARIABLE NAME')
            return None
        key = self._curtok # TODO: добавить запись ключа и значения в окружение препроцессора
        self._eat_tokens(1)
        # далее могут идти три варианта
        if self._check_type(tt.RIGHT_PAREN) and self._next_peek().ttype == tt.NEWLINE:
            # правая скобка и newline означают, что объявление завершено
            assignment = dir.AssignmentDir[None](key, None)
            self._eat_tokens(2) # пожираем два токена, в т.ч. newline
            return assignment
        if self._check_type(tt.ASSIGNMENT_OPERATOR):
            self._eat_tokens(1)
            if not self._check_type(tt.IDENTIFIER):
                self._error('Expected IDENTIFIER (ex. variable name)')
                return None
            value = self._curtok
            self._eat_tokens(1)
            if not self._check_type(tt.RIGHT_PAREN):
                self._error(f'Expected RIGHT_PAREN')
                return None
            self._eat_tokens(1)
            if not self._check_type(tt.NEWLINE): # директива должна заканчиваться переносом на новую строку
                self._error('Expected end of Directive')
                return None
            # теперь, когда вся валидация пройдена, поглощаем токен новой строки, и возвращаем присвоение
            self._eat_tokens(1)
            return dir.AssignmentDir[None](key, value)
        # любой другой токен означает, что что-то сломано в комманде
        self._error('Unexpected token')
        return None

    def _open_loc(self) -> stm.PpQspLocOpen[None]:
        """ Open Loc Statement Create """
        name = self._curtok
        self._loc_is_open = True
        self._eat_tokens(1)
        return stm.PpQspLocOpen[None](name)   
    
    def _raw_line(self) -> stm.RawLineStmt[None]:
        """ Raw Line Statement Create """
        value:List[Tkn] = [self._curtok]
        self._eat_tokens(1)
        return stm.RawLineStmt[None](value)

    # aux operations
    def _is_eof(self) -> bool:
        """ Является ли токен концом файла. """
        return self._curtok.ttype == tt.EOF

    def _check_type(self, t:tt) -> bool:
        """ Сравнивает тип текущего токена с переданным. """
        return self._curtok.ttype == t

    def _match(self, *t:tt) -> bool:
        """ Проверяет, относится ли текущий токен к указанному типу """
        return self._curtok.ttype in t

    def _peek(self) -> Optional[Tkn]:
        """ Текущий токен. """
        return self._curtok

    def _next_peek(self) -> Tkn:
        """ Возващает следующий токен. """
        sk = self._curtok_num
        return self._tokens[sk + 1] 

    def _eat_tokens(self, count:int) -> None:
        """ Поглощает токен. Т.е. передвигает указатель на следующий. """
        self._curtok_num += count # токены передвигаются лишь до EOF, поэтому выход за пределы невозможен
        self._curtok = self._tokens[self._curtok_num]

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        name = self._curtok.ttype.name
        print(f"Err. {message}: {name} ({self._curtok_num}).")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")