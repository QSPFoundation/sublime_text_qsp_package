# from tracemalloc import start
from typing import List, Optional, Any

from pp_tokens import PpToken as Tkn
from pp_tokens import PpTokenType as tt

import dirs_stmts as stm
import pp_dir as dir
import pp_expr as expr

DirStmt = stm.DirStmt[Any]

class DirsParser:

    def __init__(self, tokens:List[Tkn]) -> None:
        self._tokens:List[Tkn] = tokens

        # валидация цепочки токенов
        if not self._tokens:
            self._logic_error(f'Init-stage. Tokens-chain is empty')
            return None
        if self._tokens and self._tokens[-1].ttype != tt.EOF:
            self._logic_error(f'There is not EOF in tokens-chain on initial stage')
            self._tokens.append(Tkn(tt.EOF, '', (-1,-1)))        

        self._curtok_num:int = 0
        self._curtok:Tkn = self._tokens[0]

        self._tbuffer:Optional[Tkn] = None
        self._eated_count:int = 0

        self._loc_is_open:bool = False

        self._statements:List[DirStmt] = [] # qsps_file entity
        
    def get_statements(self) -> List[DirStmt]:
        return self._statements

    def qsps_file_parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # разбиваем файл на директивы и строки, валидация директив
        while not self._is_eof():
            if self._check_type(tt.PREFORMATTER):
                self._tbuffer = self._curtok
                self._eat_tokens(1)
            self._statements.append(self._declaration())
            self._tbuffer = None

    def _declaration(self) -> stm.DirStmt[None]:
        """ Распарсиваем целый файл из токенов. """
        if self._check_type(tt.OPEN_DIRECTIVE_STMT):
            start_declaration_on_loc:int = self._curtok_num
            validate_directive_on_loc:Optional[stm.DirectiveStmt[None]] = self._directive()
            if validate_directive_on_loc:
                return validate_directive_on_loc
            else:
                self._reset_curtok(start_declaration_on_loc)
                return self._qsps_line_stmt()
        elif self._check_type(tt.QSPS_LINE):
            return self._qsps_line_stmt()
        else:
            self._logic_error(f'Unexpected token: {self._curtok.ttype.name} {self._curtok.lexeme_start}')
            return self._qsps_line_stmt()

    def _qsps_line_stmt(self) -> stm.QspsLineStmt[None]:
        """Получаем строку."""
        pref, self._tbuffer = self._tbuffer, None
        value:List[Tkn] = []
        if self._check_type(tt.QSPS_LINE):
            # если текущий токен уже строка, отправляем его в value
            value.append(self._curtok)
            self._eat_tokens(1)
        else:
            # текущий токен не строка, значит надо обойти все токены до следующей строки
            start_line:int = -1
            while not self._is_eof():
                if start_line == -1:
                    start_line = self._curtok.lexeme_start[0]
                elif start_line < self._curtok.lexeme_start[0]:
                    # строка изменилась, не поглощаем токен
                    break
                value.append(self._curtok)
                self._eat_tokens(1)
        
        return stm.QspsLineStmt[None](pref, value)

    def _directive(self) -> Optional[stm.DirectiveStmt[None]]:
        """ Получаем директиву препроцессора, если возможно. """
        pref, self._tbuffer = self._tbuffer, None
        lexeme = self._curtok # !@pp: tt.OPEN_DIRECTIVE_STMT
        self._eat_tokens(1) # пожираем токен объявления директивы
        next_peek = self._next_peek()
        next_is_newline = (next_peek.ttype == tt.NEWLINE)

        if self._check_type(tt.ENDIF_STMT) and next_is_newline:
            body = dir.EndifDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.DirectiveStmt(pref, lexeme, body, next_peek)

        if self._curtok.ttype == tt.OFF_STMT and next_is_newline:
            body = dir.OffDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.DirectiveStmt(pref, lexeme, body, next_peek)
        if self._curtok.ttype == tt.ON_STMT and next_is_newline:
            body = dir.OnDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.DirectiveStmt(pref, lexeme, body, next_peek)
        if self._curtok.ttype == tt.NO_SAVECOMM_STMT and next_is_newline:
            body = dir.NoSaveCommDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.DirectiveStmt(pref, lexeme, body, next_peek)
        if self._curtok.ttype == tt.SAVECOMM_STMT and next_is_newline:
            body = dir.SaveCommDir[None](self._curtok)
            self._eat_tokens(2) # поглощаем сразу два токена, т.е ещё и newline
            return stm.DirectiveStmt(pref, lexeme, body, next_peek)

        if self._check_type(tt.VAR_STMT):
            self._eat_tokens(1) # пожираем токен объявления переменной
            assignment_validation:Optional[dir.AssignmentDir[None]] = self._assignment_dir()
            if assignment_validation is None:
                return None
            end_assignment = self._curtok # newline ещё не пожрали
            self._eat_tokens(1)
            return stm.DirectiveStmt[None](pref, lexeme, assignment_validation, end_assignment)

        if self._check_type(tt.IF_STMT):
            self._eat_tokens(1) # пожирем IF_STMT
            condition_validation:Optional[dir.ConditionDir[None]] = self._condition_dir()
            if condition_validation is None: return None
            return stm.DirectiveStmt[None](pref, lexeme, condition_validation, next_peek)
        return None # если ни одна цепочка токенов не прошла валидацию при парсинге

    def _condition_dir(self) -> Optional[dir.ConditionDir[None]]:
        """ Получаем директиву условия """
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
        cond_resolves_validation:List[dir.ConditionResolve[None]] = self._cond_resolves()
        if not cond_resolves_validation: return None
        cond_resolves = cond_resolves_validation
        # на данном этапе у нас не поглощён только токен следующей строки
        self._eat_tokens(1)
        return dir.ConditionDir(condition=condition_expr, next_dirs=cond_resolves)

    def _cond_resolves(self) -> List[dir.ConditionResolve[None]]:
        """ Получаем список операторов, выполняемых при соблюдении условия """
        resolves:List[dir.ConditionResolve[None]] = []

        while not self._check_type(tt.NEWLINE):
            
            # if self._check_type(tt.NOPP_STMT):
            #     resolves.append(dir.NoppDir[None](self._curtok))
            #     self._eat_tokens(1)
            #     continue

            if self._check_type(tt.SAVECOMM_STMT):
                resolves.append(dir.SaveCommDir[None](self._curtok))
                self._eat_tokens(1)
                continue

            if self._check_type(tt.NO_SAVECOMM_STMT):
                resolves.append(dir.NoSaveCommDir[None](self._curtok))
                self._eat_tokens(1)
                continue

            if self._check_type(tt.ON_STMT):
                resolves.append(dir.OnDir[None](self._curtok))
                self._eat_tokens(1)
                continue

            if self._check_type(tt.OFF_STMT):
                resolves.append(dir.OffDir[None](self._curtok))
                self._eat_tokens(1)
                continue

            if self._check_type(tt.INCLUDE_STMT):
                resolves.append(dir.IncludeDir[None](self._curtok))
                self._eat_tokens(1)
                continue

            if self._check_type(tt.EXCLUDE_STMT):
                resolves.append(dir.ExcludeDir[None](self._curtok))
                self._eat_tokens(1)
                continue

            self._error(f'Unexpected token. Expect Condition resolve tokens')
            return []

        return resolves

    def _cond_expr_stmt(self) -> Optional[dir.CondExprStmt[None]]:
        """ Получаем выражение условия """
        or_validation:Optional[expr.OrType[None]] = self._or()
        if or_validation is None: return None
        return dir.CondExprStmt(or_validation)

    def _or(self) -> Optional[expr.OrType[None]]:
        """ Получаем выражение OR """
        and_validation:Optional[expr.AndType[None]] = self._and()
        if and_validation is None: return None
        left = and_validation
        while self._check_type(tt.OR_OPERATOR):
            
            self._eat_tokens(1)
            
            right_validation = self._and()
            if right_validation is None: return None
            right = right_validation
            left = expr.OrExpr[None](left, right)

        return left

    def _and(self) -> Optional[expr.AndType[None]]:
        """ Выражение логического И """
        not_validation = self._not()
        if not_validation is None: return None
        left = not_validation
        while self._check_type(tt.AND_OPERATOR):
            
            self._eat_tokens(1)
            
            right_validation = self._not()
            if right_validation is None: return None
            right = right_validation
            left = expr.AndExpr[None](left, right)
        
        return left

    def _not(self) -> Optional[expr.NotType[None]]:
        """ Получаем выражение с оператором отрицания """
        # NotExpr = notOperator? EqualExpr
        if self._check_type(tt.NOT_OPERATOR):
            
            self._eat_tokens(1)
            
            validation_equal = self._equal()
            if validation_equal is None: return None # если есть ошибка в сравнениях, значит это невалидная директива
            right = validation_equal
            return expr.NotExpr(right)

        validation_equal = self._equal()
        return validation_equal if not validation_equal is None else None
            
    def _equal(self) -> Optional[expr.EqualType[None]]:
        """ Получаем выражение сравнения """
        if not self._check_type(tt.IDENTIFIER):
            self._error('Expected IDENTIFIER (ex. var name)')
            return None
        operands:List[expr.VarName[None]] = [expr.VarName[None](self._curtok)]
        operators:List[Tkn] = []
        self._eat_tokens(1)
        
        while self._match(tt.EQUAL_EQUAL, tt.EQUAL_NOT_EQUAL):
            operators.append(self._curtok)
            self._eat_tokens(1)
            
            if not self._check_type(tt.IDENTIFIER):
                self._error('Expected IDENTIFIER (ex. var name)')
                return None

            operands.append(expr.VarName[None](self._curtok))
            self._eat_tokens(1)
            
        return expr.EqualExpr[None](operands, operators)

    def _assignment_dir(self) -> Optional[dir.AssignmentDir[None]]:
        """Получаем директиву объявления переменной"""
        # далее должен идти токен скобки
        if not self._check_type(tt.LEFT_PAREN):
            self._error(f'Expected LEFT_PAREN')
            return None
        self._eat_tokens(1) # поглотили токен скобки
        # далее идёт идентификатор
        if not self._check_type(tt.IDENTIFIER):
            self._error('Expected VARIABLE NAME')
            return None
        key = self._curtok
        self._eat_tokens(1)
        # далее могут идти три варианта
        if self._check_type(tt.RIGHT_PAREN) and self._next_peek().ttype == tt.NEWLINE:
            # правая скобка и newline означают, что объявление завершено
            self._eat_tokens(1) # newline не пожираем
            return dir.AssignmentDir[None](key, None)
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
            # теперь, когда вся валидация пройдена возвращаем присвоение
            return dir.AssignmentDir[None](key, value)
        # любой другой токен означает, что что-то сломано в комманде
        self._error('Unexpected token')
        return None

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

    def _next_peek(self) -> Tkn:
        """ Возващает следующий токен. """
        sk = self._curtok_num
        return self._tokens[sk + 1] 

    def _eat_tokens(self, count:int) -> None:
        """ Поглощает токен. Т.е. передвигает указатель на следующий. """
        self._curtok_num += count # токены передвигаются лишь до EOF, поэтому выход за пределы невозможен
        self._curtok = self._tokens[self._curtok_num]

    def _reset_curtok(self, start_declaration:int) -> None:
        """ Сброс начала обработки токенов до указанного """
        self._curtok_num = start_declaration
        self._curtok = self._tokens[self._curtok_num]

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        name = self._curtok.ttype.name
        coords = self._curtok.lexeme_start
        print(f"Dirs-Parser Err. {message}: {name} ({self._curtok_num}) [{coords}].")

    def _logic_error(self, message:str) -> None:
        print(f"Dirs-parser Logic error: {message}. Please, report to the developer.")