# from tracemalloc import start
from typing import List, Optional, Any

from .pp_tokens import PpToken as Tkn
from .pp_tokens import PpTokenType as tt
from . import pp_stmts as stm

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

        self._tbuffer:Optional[Tkn] = None
        self._eated_count:int = 0

        self._loc_is_open:bool = False

        self._statements:List[PpStmt] = [] # qsps_file entity

    def tokens_parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        while not self._is_eof():
            if self._check_type(tt.PREFORMATTER):
                self._tbuffer = self._curtok
                self._eat_tokens(1)
            self._statements.append(self._declaration())
            self._tbuffer = None
        
    def get_statements(self) -> List[PpStmt]:
        return self._statements

    def _declaration(self) -> stm.PpStmt[None]:
        """ Распарсиваем целый файл из токенов. """
        if self._loc_is_open:
            if self._check_type(tt.LOC_CLOSE):
                return self._close_loc()
            # elif self._check_type(tt.LOC_OPEN):
                # TODO: теоретически может появиться вариант с подобным началом локации
            elif self._match(tt.EXCLAMATION_SIGN, tt.SIMPLE_SPEC_COMM, tt.LESS_SPEC_COMM):
                # комментарии трёх типов: обычный, спецкомментарий, спецкомментарий с удалением
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
            if self._check_type(tt.LOC_OPEN):
                return self._open_loc()
            elif self._check_type(tt.RAW_LINE):
                return self._raw_line()
            else:
                self._logic_error(f'Expected LOC_OPEN, RAW_LINE or OPEN_DIR_STMT. Get {self._curtok.ttype.name}')
                return self._raw_line_eating()

    def _statements_line(self) -> stm.StmtsLine[None]:
        """Получаем строку операторов с комментариями"""
        pref, self._tbuffer = self._tbuffer, None
        stmts:List[stm.StmtLinePart[None]] = []
        comment:Optional[stm.CommentStmt[None]] = None
        
        # Первый OtherStmt обязателен
        stmts.append(self._other_stmt())
        
        while not self._is_eof():
            if self._check_type(tt.NEWLINE):
                stmts.append(stm.PpLiteral(self._curtok))
                self._eat_tokens(1)
                break
            if self._check_type(tt.AMPERSAND):
                stmts.append(stm.PpLiteral(self._curtok))
                self._eat_tokens(1)  # поглощаем разделитель &
                # Проверяем, не комментарий ли следующий токен
                if self._match(tt.EXCLAMATION_SIGN, tt.SIMPLE_SPEC_COMM, tt.LESS_SPEC_COMM):
                    # Опциональный комментарий после разделителя
                    comment = self._comment()
                    break
                else:
                    # Следующий OtherStmt после разделителя
                    stmts.append(self._other_stmt())
            elif self._match(tt.EXCLAMATION_SIGN, tt.SIMPLE_SPEC_COMM, tt.LESS_SPEC_COMM):
                # Комментарий без разделителя (не должно быть по грамматике, но обработаем)
                comment = self._comment()
                break
            else:
                # Если не разделитель и не комментарий, значит что-то не так
                self._logic_error(f'Statements Line. Unexpected Token {self._curtok.ttype.name}')
                break
        
        return stm.StmtsLine[None](pref, stmts, comment)
       
    def _other_stmt(self) -> stm.OtherStmt[None]:
        """ Получаем QSP-оператор """
        chain:stm.OtherStmtChain[None] = []

        while not (self._is_eof() or self._match(tt.NEWLINE, tt.AMPERSAND)):
            # тело оператора продолжается до конца строки или амперсанда
            if self._match(tt.QUOTE, tt.APOSTROPHE):
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
        
        return stm.OtherStmt[None](chain)

    def _bracket_block(self) -> stm.BracketBlock[None]:
        """ блок в квадратных скобках """
        left:Tkn = self._curtok
        self._eat_tokens(1)
        
        # Собираем все OtherStmt внутри блока (может быть несколько или ни одного)
        value:Optional[stm.OtherStmt[None]] = None
        chain:stm.OtherStmtChain[None] = []
        
        while not self._is_eof():

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
        
        while not self._is_eof():
            
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
        while not self._is_eof():
            
            if self._check_type(tt.RIGHT_BRACE):
                break
            if self._check_type(tt.LEFT_BRACE):
                # Вложенный CodeBlock
                chain.append(self._code_block())
            elif self._match(tt.QUOTE, tt.APOSTROPHE):
                chain.append(self._string_literal())
            else:
                # Обычные символы (rawCodeBlockChar)
                chain.append(stm.PpLiteral[None](self._curtok))
                self._eat_tokens(1)
        
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
        value:List[stm.RawStringLine[None]] = []
        # обрабатываем токен начала строки
        ttype = self._curtok.ttype
        left = self._curtok
        self._eat_tokens(1)

        while not self._is_eof():
            # поглощаем токены

            if self._check_type(ttype): # строка окончилась
                self._eat_tokens(1)
                break
            if self._check_type(tt.PREFORMATTER):
                # токен преформатирования просто пропускаем
                self._eat_tokens(1)
                continue
            else:
                value.append(self._raw_string_line(ttype))
        else:
            self._error('Literal String. Unexpectable EOF')

        return stm.StringLiteral[None](left, value)

    def _raw_string_line(self, ttype:tt = tt.QUOTE) -> stm.RawStringLine[None]:
        """ Получение сырой строки для строковой константы """
        value:List[Tkn] = []
        # цикл выполняется, пока не достигнут конец файла или кавычка,
        # при этом токен не поглощается.
        while not (self._is_eof() or self._check_type(ttype)):
            if self._check_type(tt.NEWLINE):
                # разбиваем на отдельные строки, для этого по переводу строки прерываем цикл.
                value.append(self._curtok)
                self._eat_tokens(1)
                break

            value.append(self._curtok)
            self._eat_tokens(1)

        return stm.RawStringLine[None](value)

    def _comment(self) -> stm.CommentStmt[None]:
        """ Получение комментариев:
            - ! обычный комментарий
            - !@ спецкомментарий
            - !@< специальный с удалением """
        pref, self._tbuffer = self._tbuffer, None
        name = self._curtok
        self._eat_tokens(1) # поглощаем токен объявления комментария
        value:List[Tkn] = []      

        while not self._is_eof():
            
            if self._check_type(tt.NEWLINE):
                value.append(self._curtok)
                self._eat_tokens(1)
                break

            if self._check_type(tt.LEFT_BRACE):
                # блок фигурных скобок внутри комментария
                value.extend(self._comment_brace_block())
            elif self._match(tt.QUOTE, tt.APOSTROPHE):
                # блок строк внутри комментария
                value.extend(self._comment_string_block())
            else:
                value.append(self._curtok)
                self._eat_tokens(1)

        return stm.CommentStmt[None](pref, name, value)

    def _comment_string_block(self) -> List[Tkn]:
        """ Получаем строку в комментарии """
        ttype = self._curtok.ttype
        value:List[Tkn] = []
        value.append(self._curtok)
        self._eat_tokens(1) # поглощаем токен кавычки
        while not self._is_eof():
            if self._check_type(ttype):
                value.append(self._curtok)
                self._eat_tokens(1)
                break
            value.append(self._curtok)
            self._eat_tokens(1)
        else:
            self._error('Comments Apostrophe Block. Unexpectable EOF')        
        return value

    def _comment_brace_block(self) -> List[Tkn]:
        """Extract brace block"""
        value:List[Tkn] = []
        value.append(self._curtok)
        self._eat_tokens(1) # поглощаем токен левой скобки
        while not self._is_eof():
            if self._curtok.ttype == tt.RIGHT_BRACE:
                value.append(self._curtok)
                self._eat_tokens(1) # поглощаем токен правой скобки
                break
            elif self._check_type(tt.LEFT_BRACE):
                value.extend(self._comment_brace_block())
            elif self._match(tt.QUOTE, tt.APOSTROPHE):
                # блок строк внутри комментария
                value.extend(self._comment_string_block())
            else:
                value.append(self._curtok)
                self._eat_tokens(1)
        else:
            self._error('Comments Brace Block. Unexpectable EOF')
        return value

    def _raw_line_eating(self) -> stm.RawLineStmt[None]:
        """ Поглощение токенов для сырой строки вне локации """
        pref, self._tbuffer = self._tbuffer, None
        value:List[Tkn] = []
        while not self._is_eof():
            if self._check_type(tt.NEWLINE):
                value.append(self._curtok)
                self._eat_tokens(1)
                break
            value.append(self._curtok)
            self._eat_tokens(1)
        return stm.RawLineStmt[None](pref, value)

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
        pref, self._tbuffer = self._tbuffer, None
        value:List[Tkn] = [self._curtok]
        self._eat_tokens(1)
        return stm.RawLineStmt[None](pref, value)

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
        coords = self._curtok.lexeme_start
        print(f"Err. {message}: {name} ({self._curtok_num}) [{coords}].")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")