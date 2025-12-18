# from tracemalloc import start
from typing import List, Callable, Optional, Any # Dict, Tuple, cast

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
            self._tokens.append(Tkn(tt.EOF, '', (-1,-1)))        

        self._curtok_num:int = 0
        self._curtok:Tkn = self._tokens[0]

        self._loc_is_open:bool = False

        self._statements:List[PpStmt] = [] # qsps_file entity

    def qsps_file_parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        iteration_count = 0
        max_iterations = len(self._tokens) * 2  # Защита от бесконечного цикла
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop detected in qsps_file_parse at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            # если попадается токен пробелов с преформатированием, просто поглощаем его
            if self._check_type(tt.PREFORMATTER): self._eat_tokens(1)
            self._statements.append(self._declaration())
            # ТОЧКА ОСТАНОВА: Проверка, что указатель продвинулся
            if self._curtok_num == prev_token_num and not self._is_eof():
                self._logic_error(f'Parser stuck at token {self._curtok_num}. Token: {self._curtok.ttype.name}')
                self._eat_tokens(1)  # Принудительно продвигаем указатель
        
    def get_statements(self) -> List[PpStmt]:
        return self._statements

    def _declaration(self) -> stm.PpStmt[None]:
        """ Распарсиваем целый файл из токенов. """
        # запоминаем стартовый токен
        if self._loc_is_open:
            if self._check_type(tt.LOC_CLOSE):
                return self._close_loc()
            # elif self._check_type(tt.LOC_OPEN):
                # TODO: теоретически может появиться вариант с подобным началом локации
            elif self._match(tt.EXCLAMATION_SIGN, tt.SIMPLE_SPEC_COMM, tt.LESS_SPEC_COMM):
                # комментарии трёх типов: обычный, спецкомментарий, спецкомментарий с удалением
                return self._comment()
            elif self._check_type(tt.OPEN_DIRECTIVE_STMT):
                start_declaration_on_loc:int = self._curtok_num
                print(f'OPEN_DIRECTIVE_STMT: {self._curtok_num}')
                validate_directive_on_loc:Optional[stm.PpDirective[None]] = self._directive()
                if validate_directive_on_loc:
                    return validate_directive_on_loc
                else:
                    self._reset_curtok(start_declaration_on_loc)
                    return self._comment()
            elif self._match(tt.APOSTROPHE, tt.QUOTE, tt.RAW_LOC_LINE,
                             tt.LEFT_BRACKET, tt.LEFT_BRACE, tt.LEFT_PAREN,
                             tt.RIGHT_BRACKET, tt.RIGHT_BRACE, tt.RIGHT_PAREN,
                             tt.AMPERSAND):
                return self._statements_line()
            else:
                self._logic_error(f'Unexpected token in location body: {self._curtok.ttype.name}')
                return self._raw_line_eating()
        else:
            # _open_loc
            if self._check_type(tt.LOC_OPEN):
                return self._open_loc()
            elif self._check_type(tt.RAW_LINE):
                return self._raw_line()
            elif self._check_type(tt.OPEN_DIRECTIVE_STMT):
                start_declaration:int = self._curtok_num
                validate_directive_out_loc:Optional[stm.PpDirective[None]] = self._directive()
                if validate_directive_out_loc:
                    return validate_directive_out_loc
                else:
                    self._reset_curtok(start_declaration)
                    return self._raw_line_eating()
            else:
                self._logic_error(f'Expected LOC_OPEN, RAW_LINE or OPEN_DIR_STMT. Get {self._curtok.ttype.name}')
                return self._raw_line_eating()

    def _statements_line(self) -> stm.StmtsLine[None]:
        """Получаем строку операторов с комментариями"""
        stmts:List[stm.OtherStmt[None]] = []
        comment:Optional[stm.CommentStmt[None]] = None
        
        # Первый OtherStmt обязателен
        print(f'first otherStatement 108: {self._curtok_num}', self._curtok.get_as_node())
        stmts.append(self._other_stmt())
        print(f'first otherStatement 110: {self._curtok_num}', self._curtok.get_as_node())
        
        # Обрабатываем разделители & и следующие OtherStmt
        iteration_count = 0
        max_iterations = 1000  # Защита от бесконечного цикла
        # Прерываем цикл, если: переход на новую строку И токен в начале этой новой строки
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _statements_line at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            if self._check_type(tt.NEWLINE):
                self._eat_tokens(1)
                break
            if self._check_type(tt.AMPERSAND):
                self._eat_tokens(1)  # поглощаем разделитель &
                # Проверяем, не комментарий ли следующий токен
                if self._match(tt.EXCLAMATION_SIGN, tt.SIMPLE_SPEC_COMM, tt.LESS_SPEC_COMM, tt.OPEN_DIRECTIVE_STMT):
                    # Опциональный комментарий после разделителя
                    comment = self._comment()
                    break
                else:
                    # Следующий OtherStmt после разделителя
                    stmts.append(self._other_stmt())
            elif self._match(tt.EXCLAMATION_SIGN, tt.SIMPLE_SPEC_COMM, tt.LESS_SPEC_COMM, tt.OPEN_DIRECTIVE_STMT):
                # Комментарий без разделителя (не должно быть по грамматике, но обработаем)
                comment = self._comment()
                break
            else:
                # Если не разделитель и не комментарий, значит что-то не так
                self._logic_error(f'Statements Line. Unexpected Token {self._curtok.ttype.name}')
                # ТОЧКА ОСТАНОВА: Проверка зацикливания
                if self._curtok_num == prev_token_num:
                    self._eat_tokens(1)  # Принудительно продвигаем указатель
                break
        
        return stm.StmtsLine[None](stmts, comment)
       
    def _other_stmt(self) -> stm.OtherStmt[None]:
        """ Получаем QSP-оператор """
        chain:stm.OtherStmtChain[None] = []
        # Запоминаем номер строки начала оператора, чтобы не завершить цикл преждевременно
        iteration_count = 0
        max_iterations = 10000  # Защита от бесконечного цикла
        # Прерываем цикл, если: переход на новую строку И токен в начале этой новой строки
        while not (self._is_eof() or self._match(tt.NEWLINE, tt.AMPERSAND)):
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _other_stmt at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            
            # тело оператора продолжается до конца строки или амперсанда
            if self._match(tt.QUOTE, tt.APOSTROPHE):
                print(f'otherStatement find quote 161: {self._curtok_num}', self._curtok.get_as_node())
                chain.append(self._string_literal())
                print(f'otherStatement find quote 163: {self._curtok_num}', self._curtok.get_as_node())
            elif self._check_type(tt.LEFT_BRACKET):
                chain.append(self._bracket_block())
            elif self._check_type(tt.LEFT_PAREN):
                chain.append(self._paren_block())
            elif self._check_type(tt.LEFT_BRACE):
                chain.append(self._code_block())
            else:
                # Обычные символы (rawOtherStmtChar)
                chain.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
            
            # ТОЧКА ОСТАНОВА: Проверка зацикливания
            if self._curtok_num == prev_token_num:
                self._logic_error(f'Parser stuck in _other_stmt at token {self._curtok_num}. Token: {self._curtok.ttype.name}')
                self._eat_tokens(1)  # Принудительно продвигаем указатель
        
        return stm.OtherStmt[None](chain)

    def _bracket_block(self) -> stm.BracketBlock[None]:
        """ блок в квадратных скобках """
        left:Tkn = self._curtok
        self._eat_tokens(1)
        
        # Собираем все OtherStmt внутри блока (может быть несколько или ни одного)
        value:Optional[stm.OtherStmt[None]] = None
        chain:stm.OtherStmtChain[None] = []
        
        iteration_count = 0
        max_iterations = 10000  # Защита от бесконечного цикла
        # Цикл продолжается до правой квадратной скобки или конца файла
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _bracket_block at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            
            if self._check_type(tt.RIGHT_BRACKET):
                break
            elif self._match(tt.QUOTE, tt.APOSTROPHE):
                chain.append(self._string_literal())
            elif self._check_type(tt.LEFT_BRACKET):
                chain.append(self._bracket_block())
            elif self._check_type(tt.LEFT_PAREN):
                chain.append(self._paren_block())
            elif self._check_type(tt.LEFT_BRACE):
                chain.append(self._code_block())
            else:
                # Обычные символы (rawOtherStmtChar)
                chain.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
            
            # ТОЧКА ОСТАНОВА: Проверка зацикливания
            if self._curtok_num == prev_token_num:
                self._logic_error(f'Parser stuck in _bracket_block at token {self._curtok_num}. Token: {self._curtok.ttype.name}')
                self._eat_tokens(1)  # Принудительно продвигаем указатель
        
        if chain:
            value = stm.OtherStmt[None](chain)
        
        if not self._check_type(tt.RIGHT_BRACKET):
            self._error('BracketBlock. Expected RIGHT_BRACKET')
            return stm.BracketBlock[None](left, value, Tkn(tt.RIGHT_BRACKET, '', (-1,-1)))
        
        right:Tkn = self._curtok
        self._eat_tokens(1)
        return stm.BracketBlock[None](left, value, right)

    def _paren_block(self) -> stm.BracketBlock[None]:
        """ блок в круглых скобках """
        # Временно используем BracketBlock, так как структура ParenBlock отсутствует
        left:Tkn = self._curtok
        self._eat_tokens(1)
        
        value:Optional[stm.OtherStmt[None]] = None
        chain:stm.OtherStmtChain[None] = []
        
        iteration_count = 0
        max_iterations = 10000  # Защита от бесконечного цикла
        # Прерываем цикл, если: переход на новую строку И токен в начале этой новой строки
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _paren_block at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            
            if self._check_type(tt.RIGHT_PAREN):
                break
            elif self._match(tt.QUOTE, tt.APOSTROPHE):
                chain.append(self._string_literal())
            elif self._check_type(tt.LEFT_BRACKET):
                chain.append(self._bracket_block())
            elif self._check_type(tt.LEFT_PAREN):
                chain.append(self._paren_block())
            elif self._check_type(tt.LEFT_BRACE):
                chain.append(self._code_block())
            else:
                chain.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
            
            # ТОЧКА ОСТАНОВА: Проверка зацикливания
            if self._curtok_num == prev_token_num:
                self._logic_error(f'Parser stuck in _paren_block at token {self._curtok_num}. Token: {self._curtok.ttype.name}')
                self._eat_tokens(1)  # Принудительно продвигаем указатель
        
        if chain:
            value = stm.OtherStmt[None](chain)
        
        if not self._check_type(tt.RIGHT_PAREN):
            self._error('ParenBlock. Expected RIGHT_PAREN')
            return stm.BracketBlock[None](left, value, Tkn(tt.RIGHT_PAREN, '', (-1,-1)))
        
        right:Tkn = self._curtok
        self._eat_tokens(1)
        # Временно используем BracketBlock вместо ParenBlock
        return stm.BracketBlock[None](left, value, right)

    def _code_block(self) -> stm.BracketBlock[None]:
        """ блок в фигурных скобках """
        # Временно используем BracketBlock, так как структура CodeBlock отсутствует
        left:Tkn = self._curtok
        self._eat_tokens(1)
        
        value:Optional[stm.OtherStmt[None]] = None
        chain:stm.OtherStmtChain[None] = []
        
        # CodeBlockContent = ( CodeBlock | PpDirectiveFullLine | rawCodeBlockChar)+
        # Парсим до RIGHT_BRACE, независимо от позиции в строке
        iteration_count = 0
        max_iterations = 10000  # Защита от бесконечного цикла
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _code_block at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            
            if self._check_type(tt.RIGHT_BRACE):
                break
            if self._check_type(tt.LEFT_BRACE):
                # Вложенный CodeBlock
                chain.append(self._code_block())
            elif self._check_type(tt.OPEN_DIRECTIVE_STMT) and self._is_line_start():
                # PpDirectiveFullLine - директива препроцессора на отдельной строке
                # Проверяем, что директива начинается с начала строки
                start_declaration:int = self._curtok_num
                directive = self._directive()
                if directive:
                    chain.append(directive)
                else:
                    # Если директива невалидна, обрабатываем как комментарий
                    self._reset_curtok(start_declaration)
                    chain.append(stm.PpLiteral[None](self._curtok))
                    self._eat_tokens(1)
            elif self._match(tt.QUOTE, tt.APOSTROPHE):
                chain.append(self._string_literal())
            else:
                # Обычные символы (rawCodeBlockChar)
                chain.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
            
            # ТОЧКА ОСТАНОВА: Проверка зацикливания
            if self._curtok_num == prev_token_num:
                self._logic_error(f'Parser stuck in _code_block at token {self._curtok_num}. Token: {self._curtok.ttype.name}')
                self._eat_tokens(1)  # Принудительно продвигаем указатель
        
        if chain:
            value = stm.OtherStmt[None](chain)
        
        if not self._check_type(tt.RIGHT_BRACE):
            self._error('CodeBlock. Expected RIGHT_BRACE')
            return stm.BracketBlock[None](left, value, Tkn(tt.RIGHT_BRACE, '', (-1,-1)))
        
        right:Tkn = self._curtok
        self._eat_tokens(1)
        # Временно используем BracketBlock вместо CodeBlock
        return stm.BracketBlock[None](left, value, right)

    def _string_literal(self) -> stm.StringLiteral[None]:
        """ Получаем строку """
        value:List[Tkn] = []
        ttype = self._curtok.ttype
        value.append(self._curtok)
        print(f'_string_literal open 346: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1) # поглощаем токен начала строки
        print(f'_string_literal open 348: {self._curtok_num}', self._curtok.get_as_node())
        iteration_count = 0
        max_iterations = 100000  # Защита от бесконечного цикла (строки могут быть длинными)
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _string_literal at token {self._curtok_num}')
                break
            iteration_count += 1
            # поглощаем токены

            if self._check_type(ttype):
                value.append(self._curtok)
                print(f'_string_literal close 363: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_string_literal close 365: {self._curtok_num}', self._curtok.get_as_node())
                break
                
            value.append(self._curtok)
            print(f'_string_literal 358: {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1)
            print(f'_string_literal 360: {self._curtok_num}', self._curtok.get_as_node())
        else:
            self._error('Literal String. Unexpectable EOF')

        return stm.StringLiteral[None](value)

    def _comment(self) -> stm.CommentStmt[None]:
        """ Получение комментариев:
            - ! обычный комментарий
            - !@ спецкомментарий
            - !@< специальный с удалением """
        name = self._curtok
        value:stm.CommentValue[None] = []
        self._eat_tokens(1) # поглощаем токен объявления комментария

        iteration_count = 0
        max_iterations = 10000  # Защита от бесконечного цикла
        # Прерываем цикл, если: переход на новую строку И токен в начале этой новой строки
        while not self._is_eof():
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _comment at token {self._curtok_num}')
                break
            iteration_count += 1
            prev_token_num = self._curtok_num
            
            if self._check_type(tt.NEWLINE):
                self._eat_tokens(1)
                break

            if self._check_type(tt.LEFT_BRACE):
                # блок фигурных скобок внутри комментария
                value.extend(self._comment_brace_block())
            elif self._check_type(tt.QUOTE):
                # блок строк внутри комментария
                value.extend(self._comment_quote_block())
            elif self._check_type(tt.APOSTROPHE):
                value.extend(self._comment_apostrophe_block())
            else:
                value.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
            
            # ТОЧКА ОСТАНОВА: Проверка зацикливания
            if self._curtok_num == prev_token_num:
                self._logic_error(f'Parser stuck in _comment at token {self._curtok_num}. Token: {self._curtok.ttype.name}')
                self._eat_tokens(1)  # Принудительно продвигаем указатель

        return stm.CommentStmt[None](name, value)

    def _comment_apostrophe_block(self) -> stm.CommentValue[None]:
        """ Получаем строку в комментарии """
        value:stm.CommentValue[None] = []
        value.append(stm.PpLiteral[None](self._curtok))
        self._eat_tokens(1) # поглощаем токен кавычки
        while not (self._is_eof() or self._curtok.ttype == tt.APOSTROPHE):
            # выполняем, пока не достигнем правой кавычки или конца файла
            value.append(stm.PpLiteral[None](self._curtok))
            self._eat_tokens(1)
        if self._check_type(tt.APOSTROPHE):
            value.append(stm.PpLiteral[None](self._curtok))
            self._eat_tokens(1) # поглощаем токен кавычки
        else:
            self._error('Comments Apostrophe Block. Unexpectable EOF')
        return value

    def _comment_quote_block(self) -> stm.CommentValue[None]:
        """ Получаем строку в комментарии """
        value:stm.CommentValue[None] = []
        value.append(stm.PpLiteral[None](self._curtok))
        self._eat_tokens(1) # поглощаем токен кавычки
        while not (self._is_eof() or self._check_type(tt.QUOTE)):
            # выполняем, пока не достигнем правой кавычки или конца файла
            value.append(stm.PpLiteral[None](self._curtok))
            self._eat_tokens(1)
        if self._check_type(tt.QUOTE):
            value.append(stm.PpLiteral[None](self._curtok))
            self._eat_tokens(1) # поглощаем токен кавычки
        else:
            self._error('Comments Quote Block. Unexpectable EOF')
        return value

    def _comment_brace_block(self) -> stm.CommentValue[None]:
        """Extract brace block"""
        value:stm.CommentValue[None] = []
        value.append(stm.PpLiteral[None](self._curtok))
        self._eat_tokens(1) # поглощаем токен левой скобки
        while not (self._is_eof() or self._curtok.ttype == tt.RIGHT_BRACE):
            # выполняем, пока не достигнем правой скобки или конца файла
            if self._check_type(tt.LEFT_BRACE):
                value.extend(self._comment_brace_block())
            elif self._check_type(tt.QUOTE):
                # блок строк внутри комментария
                value.extend(self._comment_quote_block())
            elif self._check_type(tt.APOSTROPHE):
                value.extend(self._comment_apostrophe_block())
            else:
                value.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
        if self._check_type(tt.RIGHT_BRACE):
            value.append(stm.PpLiteral[None](self._curtok))
            self._eat_tokens(1) # поглощаем токен правой скобки
        else:
            self._error('Comments Brace Block. Unexpectable EOF')
        return value

    def _raw_line_eating(self) -> stm.RawLineStmt[None]:
        """ Поглощение токенов для сырой строки вне локации """
        value:List[stm.PpLiteral[None]] = []
        iteration_count = 0
        max_iterations = 10000  # Защита от бесконечного цикла
        while not self._check_type(tt.NEWLINE):
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _raw_line_eating at token {self._curtok_num}')
                break
            iteration_count += 1
            value.append(stm.PpLiteral[None](self._curtok))
            self._eat_tokens(1)
        return stm.RawLineStmt[None](value)

    def _directive(self) -> Optional[stm.PpDirective[None]]:
        """ Получаем директиву препроцессора, если возможно. """
        print(f'_directive 466: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1) # пожираем токен объявления директивы
        print(f'_directive 468: {self._curtok_num}', self._curtok.get_as_node())
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
            self._eat_tokens(1) # пожираем токен объявления переменной
            assignment_validation:Optional[dir.AssignmentDir[None]] = self._assignment_dir()
            if assignment_validation is None:
                return None
            return stm.PpDirective[None](assignment_validation)
        if self._check_type(tt.IF_STMT):
            print(f'_directive 501: {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1) # пожирем IF_STMT
            print(f'_directive 503: {self._curtok_num}', self._curtok.get_as_node())
            condition_validation:Optional[dir.ConditionDir[None]] = self._condition_dir()
            if condition_validation is None: return None
            return stm.PpDirective[None](condition_validation)
        return None # если ни одна цепочка токенов не прошла валидацию при парсинге

    def _condition_dir(self) -> Optional[dir.ConditionDir[None]]:
        """ Получаем директиву условия """
        if not self._check_type(tt.LEFT_PAREN):
            self._error(f'Expected LEFT_PAREN')
            return None
        print(f'_condition_dir 514: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1)
        print(f'_condition_dir 516: {self._curtok_num}', self._curtok.get_as_node())
        cond_expr_validation:Optional[dir.CondExprStmt[None]] = self._cond_expr_stmt()
        if cond_expr_validation is None: return None
        condition_expr:dir.CondExprStmt[None] = cond_expr_validation
        if not self._check_type(tt.RIGHT_PAREN):
            self._error(f'Expected RIGHT_PAREN')
            return None
        print(f'_condition_dir 523: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1)
        print(f'_condition_dir 525: {self._curtok_num}', self._curtok.get_as_node())
        if not self._check_type(tt.THEN_STMT):
            self._error(f'Expected THEN_STMT')
            return None
        print(f'_condition_dir 529: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1)
        print(f'_condition_dir 531: {self._curtok_num}', self._curtok.get_as_node())
        cond_resolves_validation:List[dir.ConditionResolve[None]] = self._cond_resolves()
        if not cond_resolves_validation: return None
        cond_resolves = cond_resolves_validation
        # на данном этапе у нас не поглощён только токен следующей строки
        print(f'_condition_dir 536: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1)
        print(f'_condition_dir 538: {self._curtok_num}', self._curtok.get_as_node())
        return dir.ConditionDir(condition_expr, cond_resolves)

    def _cond_resolves(self) -> List[dir.ConditionResolve[None]]:
        """ Получаем список операторов, выполняемых при соблюдении условия """
        resolves:List[dir.ConditionResolve[None]] = []
        iteration_count = 0
        max_iterations = 1000  # Защита от бесконечного цикла
        while not self._check_type(tt.NEWLINE):
            if iteration_count >= max_iterations:
                self._logic_error(f'Infinite loop in _cond_resolves at token {self._curtok_num}')
                break
            iteration_count += 1
            
            if self._check_type(tt.NOPP_STMT):
                resolves.append(dir.NoppDir[None](self._curtok))
                print(f'_cond_resolves 555: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 557: {self._curtok_num}', self._curtok.get_as_node())
                continue
            if self._check_type(tt.SAVECOMM_STMT):
                resolves.append(dir.SaveCommDir[None](self._curtok))
                print(f'_cond_resolves 561: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 563: {self._curtok_num}', self._curtok.get_as_node())
                continue
            if self._check_type(tt.NO_SAVECOMM_STMT):
                resolves.append(dir.NoSaveCommDir[None](self._curtok))
                print(f'_cond_resolves 567: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 569: {self._curtok_num}', self._curtok.get_as_node())
                continue
            if self._check_type(tt.ON_STMT):
                resolves.append(dir.OnDir[None](self._curtok))
                print(f'_cond_resolves 573: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 575: {self._curtok_num}', self._curtok.get_as_node())
                continue
            if self._check_type(tt.OFF_STMT):
                resolves.append(dir.OffDir[None](self._curtok))
                print(f'_cond_resolves 579: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 581: {self._curtok_num}', self._curtok.get_as_node())
                continue
            if self._check_type(tt.INCLUDE_STMT):
                resolves.append(dir.IncludeDir[None](self._curtok))
                print(f'_cond_resolves 585: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 587: {self._curtok_num}', self._curtok.get_as_node())
                continue
            if self._check_type(tt.EXCLUDE_STMT):
                resolves.append(dir.ExcludeDir[None](self._curtok))
                print(f'_cond_resolves 591: {self._curtok_num}', self._curtok.get_as_node())
                self._eat_tokens(1)
                print(f'_cond_resolves 593: {self._curtok_num}', self._curtok.get_as_node())
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
            print(f'_or 602: {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1)
            print(f'_or 604: {self._curtok_num}', self._curtok.get_as_node())
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
            print(f'_and 618: {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1)
            print(f'_and 620: {self._curtok_num}', self._curtok.get_as_node())
            right_validation = self._not()
            if right_validation is None: return None
            right = right_validation
            left = expr.AndExpr[None](left, right)
        
        return left

    def _not(self) -> Optional[expr.NotType[None]]:
        """ Получаем выражение с оператором отрицания """
        # NotExpr = notOperator? EqualExpr
        if self._check_type(tt.NOT_OPERATOR):
            print(f'_not 632: {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1)
            print(f'_not 634: {self._curtok_num}', self._curtok.get_as_node())
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
        equal_expr = expr.VarName[None](self._curtok) # TODO: добавлять идентификаторы в окружение на каждом этапе
        print(f'_equal 649: {self._curtok_num}', self._curtok.get_as_node())
        self._eat_tokens(1)
        print(f'_equal 651: {self._curtok_num}', self._curtok.get_as_node())
        while self._match(tt.EQUAL_EQUAL, tt.EQUAL_NOT_EQUAL):
            operator = self._curtok
            print(f'_equal 654: {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1)
            print(f'_equal 656: {self._curtok_num}', self._curtok.get_as_node())
            if not self._check_type(tt.IDENTIFIER):
                self._error('Expected IDENTIFIER (ex. var name)')
                return None
            right = expr.VarName[None](self._curtok)
            print(f'_equal 661 {self._curtok_num}', self._curtok.get_as_node())
            self._eat_tokens(1)
            print(f'_equal 663: {self._curtok_num}', self._curtok.get_as_node())
            equal_expr = expr.EqualExpr[None](equal_expr, operator, right)
        return equal_expr

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
    
    def _close_loc(self) -> stm.PpQspLocClose[None]:
        """ Close Loc Statement Create """
        name = self._curtok
        self._loc_is_open = False
        self._eat_tokens(1)
        return stm.PpQspLocClose[None](name) 
    
    def _raw_line(self) -> stm.RawLineStmt[None]:
        """ Raw Line Statement Create """
        value:List[stm.PpLiteral[None]] = [stm.PpLiteral[None](self._curtok)]
        self._eat_tokens(1)
        return stm.RawLineStmt[None](value)

    # aux operations
    def _is_eof(self) -> bool:
        """ Является ли токен концом файла. """
        return self._curtok.ttype == tt.EOF

    def _is_line_start(self) -> bool:
        """ Текущий токен - начало строки? """
        return self._curtok.lexeme_start[1] == 0

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

    def _reset_curtok(self, start_declaration:int) -> None:
        """ Сброс начала обработки токенов до указанного """
        self._curtok_num = start_declaration
        self._curtok = self._tokens[self._curtok_num]

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        name = self._curtok.ttype.name
        print(f"Err. {message}: {name} ({self._curtok_num}).")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")