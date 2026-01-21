# from tracemalloc import start
from typing import List, Optional, Any

from base_tokens import BaseToken as Tkn, BaseTokenType as tt

import base_stmt as stm

BaseStmt = stm.BaseStmt[Any]

from error import ParserError

class BaseParser:

    _EXPRESSION_START = (
        tt.APOSTROPHE_STRING, tt.QUOTE_STRING,
        tt.LEFT_BRACE, tt.LEFT_BRACKET, tt.LEFT_PAREN,
        tt.IDENTIFIER, tt.RAW_TEXT
    )

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

        self._statements:List[BaseStmt] = [] # qsps_file entity
        
    def get_statements(self) -> List[BaseStmt]:
        return self._statements

    def parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # разбиваем файл на операторы. При этом операторы могут быть блочные
        while not self._is_eof():
            if self._check_type(tt.PREFORMATTER):
                self._tbuffer = self._curtok
                self._eat_tokens(1)
            self._statements.append(self._statement())
            self._tbuffer = None

    def _statement(self) -> stm.BaseStmt[None]:
        """ Распарсиваем целый файл из токенов. """
        if self._match(tt.STAR_P_STMT, tt.STAR_NL_STMT, tt.STAR_PL_STMT):
            return self._print_text()
        if self._check_type(tt.ACT_STMT):
            return self._action()
        if self._check_type(tt.IF_STMT):
            return self._condition()
        if self._check_type(tt.LOOP_STMT):
            return self._loop()
        if self._is_unknown_stmt():
            return self._unknown_stmt()
        if self._check_type(tt.EXCLAMATION_SIGN):
            return self._comment()
        if self._curtok.ttype in self._EXPRESSION_START:
            return self._expression_stmt()
        return self._literal()

    def _is_unknown_stmt(self) -> bool:
        """ True if unknown stmt, False if expression stmt """
        # идентификатор должен быть отделён хотя бы одним пробелом от токена подходящего к началу
        return self._check_type(tt.IDENTIFIER) and self._next_peek().ttype in self._EXPRESSION_START and not self._are_adjacent()

    def _unknown_stmt(self) -> stm.Unknown[None]:
        """ Неизвестный оператор! """
        pref, self._tbuffer = self._tbuffer, None
        line = self._curtok.lexeme_start[0]
        stmt = self._curtok # фиксируем оператор
        self._eat_tokens(1)

        args:List[stm.Expression[None]] = []
        while not self._is_eof():
            if self._check_type(tt.COMMA):
                # разделитель между выражениями
                self._eat_tokens(1) # просто пожираем токен
                continue
            if self._match(tt.AMPERSAND, tt.NEWLINE):
                # если при парсинге неизвестного оператора мы встречаем конец строки или амперсанд
                self._eat_tokens(1) # пожираем токен
                break # прерываем цикл
            if self._match(tt.WHILE_STMT, tt.THEN):
                # если неизвестный оператор парсился перед WHILE или THEN,                
                break # не пожираем токен, он нам нужен
            args.append(self._expression())
        # else: # оператор может окончиться и на конце файла: не пожираем токен
        #     raise ParserError(self._curtok, 'Unexpectable EOF!')

        return stm.Unknown(pref, stmt, args, line)

    def _loop(self) -> stm.Loop[None]:
        pref, self._tbuffer = self._tbuffer, None
        line = self._curtok.lexeme_start[0]
        open_ = self._curtok
        self._eat_tokens(1)

        # defines:List[BaseStmt[R]]
        defines = self._extract_line(tt.WHILE_STMT)

        # while_stmt:BaseToken # while

        if not self._check_type(tt.WHILE_STMT):
            self._error('Expected : (WHILE_STMT). Getted ')
        while_stmt = self._curtok
        self._eat_tokens(1) # погл WHILE

        # condition:Expression[R]

        condition = self._expression(tt.THEN, tt.STEP_STMT)

        # step_stmt:Optional[BaseToken]

        if self._check_type(tt.STEP_STMT):
            step_stmt = self._curtok
            self._eat_tokens(1)

            # steps:List[BaseStmt[R]]
            steps = self._extract_line(tt.THEN)
        else:
            step_stmt = None
            steps:List[BaseStmt] = []

     
        # content:List[BaseStmt[R]]
        # close:BaseToken

        if not self._check_type(tt.THEN):
            self._error('Expected : (THEN_STMT). Getted ')
        self._eat_tokens(1) # погл THEN

        if self._check_type(tt.EXCLAMATION_SIGN):
            self._comment()
            content = self._extract_block()
            # токен END не поглощён. Поглощаем
            close = self._end()

        elif self._check_type(tt.NEWLINE):
            self._eat_tokens(1)
            content = self._extract_block()
            # токен END не поглощён. Поглощаем
            close = self._end()
        else:
            # в той же строке идут другие токены. Это однострочное действие
            content = self._extract_line()
            close = stm.End[None](None, self._prev_peek())

        return stm.Loop(pref, open_, defines,
                        while_stmt, condition, step_stmt, steps, content, close, line)

    def _condition(self) -> stm.Condition[None]:
        pref, self._tbuffer = self._tbuffer, None
        line = self._curtok.lexeme_start[0]
        open_ = self._curtok
        self._eat_tokens(1)

        condition = self._expression(tt.THEN)

        if not self._check_type(tt.THEN):
            self._error('Expected : (THEN_STMT). Getted ')
        self._eat_tokens(1) # погл THEN

        if self._check_type(tt.EXCLAMATION_SIGN):
            self._comment()
            content = self._extract_block()
            # токен END не поглощён. Поглощаем
            close = self._end()

        elif self._check_type(tt.NEWLINE):
            self._eat_tokens(1)
            content = self._extract_block()
            # токен END не поглощён. Поглощаем
            close = self._end()
        else:
            # в той же строке идут другие токены. Это однострочное действие
            content = self._extract_line()
            # токен новой строки должен быть поглощён оператором, который мы парсили
            # это значит, что это предыдущий токен
            close = stm.End[None](None, self._prev_peek())


        return stm.Condition(pref, open_, condition, content, close, line)

    def _action(self) -> stm.Action[None]:
        """ Поиск действия """
        pref, self._tbuffer = self._tbuffer, None
        line = self._curtok.lexeme_start[0]
        open_ = self._curtok
        self._eat_tokens(1)

        name = self._expression(tt.COMMA, tt.THEN)

        if self._check_type(tt.COMMA):
            self._eat_tokens(1) # eat COMMA
            image = self._expression(tt.THEN)
        else:
            image = None

        if not self._check_type(tt.THEN):
            self._error('Expected : (THEN_STMT). Getted ')
        self._eat_tokens(1) # погл THEN

        if self._check_type(tt.EXCLAMATION_SIGN):
            self._comment()
            content = self._extract_block()
            # токен END не поглощён. Поглощаем
            close = self._end()

        elif self._check_type(tt.NEWLINE):
            self._eat_tokens(1)
            content = self._extract_block()
            # токен END не поглощён. Поглощаем
            close = self._end()
        else:
            # в той же строке идут другие токены. Это однострочное действие
            content = self._extract_line()
            close = stm.End[None](None, self._prev_peek())

        return stm.Action(pref, open_, name, image, content, close, line)

    def _extract_block(self) -> List[BaseStmt]:
        """ извлекает блок операторов до end """
        chain:List[BaseStmt] = []

        while not self._is_eof():
            if self._check_type(tt.END_STMT) or (self._check_type(tt.PREFORMATTER) and self._next_is_type(tt.END_STMT)):
                # end stmt not eating
                return chain
            if self._check_type(tt.PREFORMATTER):
                self._tbuffer = self._curtok
                self._eat_tokens(1)
            chain.append(self._statement())
            self._tbuffer = None
        else:
            raise ParserError(self._curtok, 'Unexpectable EOF in multiline block')

    def _extract_line(self, *pop:tt) -> List[BaseStmt]:
        """ извлекает строку операторов через амперсанд """
        # if not pop: pop = (tt.NEWLINE, )
        start_line = self._curtok.lexeme_start[0]
        chain:List[BaseStmt] = []
        while not self._is_eof():
            if not self._is_line_num(start_line):
                # если текущий токен содержит иной номер строки, прерываем извлечение строки операторов
                return chain
            chain.append(self._statement())
        # строка может окончиться 
        return chain

    def _end(self) -> stm.End[None]:
        """ Возвращает токен END и поглощает комментарий за ним """
        if self._check_type(tt.PREFORMATTER):
            pref = self._curtok
            self._eat_tokens(1)
        else:
            pref = None

        if not self._check_type(tt.END_STMT):
            raise ParserError(self._curtok, 'Expected END_STMT.')
        line = self._curtok.lexeme_start[0]
        close = self._curtok # поглощаем токен END
        self._eat_tokens(1)

        while not self._is_eof():
            if self._match(tt.AMPERSAND, tt.NEWLINE):
                # комментарий после енда оканчивается с новой строкой или на амперсанде
                self._eat_tokens(1)
                break
            if self._check_type(tt.LEFT_BRACE):
                self._braces()
                continue
            self._eat_tokens(1)
        # else:
        #     self._error('Unexpectable EOF in comment after END')

        return stm.End(pref, close, line) 
            
    def _print_text(self) -> stm.PrintTextStmt[None]:
        """ Оператор вывода текста """
        pref, self._tbuffer = self._tbuffer, None
        line = self._curtok.lexeme_start[0]
        stmt = self._curtok # фиксируем оператор
        self._eat_tokens(1)

        expression = self._expression()

        if self._match(tt.AMPERSAND, tt.NEWLINE): self._eat_tokens(1)
        # tt.WHILE_STMT, tt.THEN означают, что оператор внутри LOOP или STEP

        return stm.PrintTextStmt(pref, stmt, expression, line)
        
    def _expression(self, *pop:tt) -> stm.Expression[None]:
        """ Выражение, передаваемое оператору. """

        if not pop: pop = (tt.NEWLINE, tt.AMPERSAND, tt.WHILE_STMT, tt.STEP_STMT)
        line_num  = self._curtok.lexeme_start[0]
        chain:List[BaseStmt] = []
        while not self._is_eof():
            if self._match(*pop):
                break # выражение закрывается, но токен не поглощаем
            if self._check_type(tt.LEFT_PAREN):
                chain.append(self._parens())
                continue
            if self._check_type(tt.LEFT_BRACKET):
                chain.append(self._brackets())
                continue
            if self._check_type(tt.LEFT_BRACE):
                chain.append(self._braces())
                continue
            chain.append(stm.Literal(self._curtok))
            self._eat_tokens(1)
        else:
            # выражение может окончиться с концом файла
            pass
            
        return stm.Expression(chain, line_num)

    def _expression_stmt(self) -> stm.ExpressionStmt[None]:
        pref, self._tbuffer = self._tbuffer, None
        line_num = self._curtok.lexeme_start[0]
        expr = self._expression()

        if self._match(tt.AMPERSAND, tt.NEWLINE): self._eat_tokens(1)
        # tt.WHILE_STMT, tt.THEN означают, что оператор внутри LOOP или STEP

        return stm.ExpressionStmt(pref, expr, line_num)

    def _parens(self) -> stm.Parens[None]:
        """ Круглые скобки и их содержимое """
        left = self._curtok # получаем и поглощаем левую скобку
        self._eat_tokens(1)
        
        content = self._expression(tt.RIGHT_PAREN, )

        if not self._check_type(tt.RIGHT_PAREN):
            raise ParserError(self._curtok, 'Expected RIGHT_PAREN.')

        right = self._curtok # поглощение правой скобки
        self._eat_tokens(1)

        return stm.Parens(left, content, right)

    def _brackets(self) -> stm.Brackets[None]:
        """ Квадратные скобки и их содержимое """
        left = self._curtok # получаем и поглощаем левую скобку
        self._eat_tokens(1)
        
        content = self._expression(tt.RIGHT_BRACKET, )

        if not self._check_type(tt.RIGHT_BRACKET):
            raise ParserError(self._curtok, 'Expected RIGHT_BRACKET.')

        right = self._curtok # поглощение правой скобки
        self._eat_tokens(1)

        return stm.Brackets(left, content, right)

    def _braces(self) -> stm.Braces[None]:
        """ Фигурные скобки и их содержимое """
        left = self._curtok # получаем и поглощаем левую скобку
        self._eat_tokens(1)
        
        chain:List[BaseStmt] = []
        while not self._is_eof():
            if self._check_type(tt.RIGHT_BRACE):
                right = self._curtok # поглощение правой скобки
                self._eat_tokens(1)
                break

            if self._check_type(tt.LEFT_BRACE):
                chain.append(self._braces())

            chain.append(stm.Literal(self._curtok))
            self._eat_tokens(1)
        else:
            # фигурная скобка не может закончиться до конца файла
            raise ParserError(self._curtok, 'Unexpectable EOF in braces!')      

        return stm.Braces(left, chain, right)

    def _comment(self) -> stm.Comment[None]:
        pref, self._tbuffer = self._tbuffer, None
        line = self._curtok.lexeme_start[0]
        open_ = self._curtok
        self._eat_tokens(1)

        chain:List[BaseStmt] = []
        while not self._is_eof():
            if self._check_type(tt.NEWLINE):
                chain.append(stm.Literal(self._curtok))
                self._eat_tokens(1)
                break
            if self._check_type(tt.LEFT_BRACE):
                chain.append(self._braces())
                continue
            chain.append(stm.Literal(self._curtok))
            self._eat_tokens(1)

        return stm.Comment(pref, open_, chain, line)

    def _literal(self) -> stm.Literal[None]:
        value = self._curtok
        self._eat_tokens(1)
        return stm.Literal(value)

    # aux operations
    def _is_eof(self) -> bool:
        """ Является ли токен концом файла. """
        return self._curtok.ttype == tt.EOF

    def _next_is_type(self, t:tt) -> bool:
        if self._curtok_num+1 < len(self._tokens):
            return self._tokens[self._curtok_num+1].ttype == t
        return False

    def _check_type(self, t:tt) -> bool:
        """ Сравнивает тип текущего токена с переданным. """
        return self._curtok.ttype == t

    def _match(self, *t:tt) -> bool:
        """ Проверяет, относится ли текущий токен к одному из указанных типов. """
        return self._curtok.ttype in t

    def _next_peek(self) -> Tkn:
        """ Возващает следующий токен. """
        sk = self._curtok_num
        return self._tokens[sk + 1]

    def _prev_peek(self) -> Tkn:
        """ Возващает предыдущий токен. """
        sk = self._curtok_num
        return self._tokens[sk - 1]

    def _are_adjacent(self) -> bool:
        """ Проверяет, являются ли текущий и следующий токен смежными. (одна строка, соседние символы)"""
        cs, ns = self._curtok.lexeme_start, self._next_peek().lexeme_start
        return cs[0] == ns[0] and self._curtok.get_end_pos()[1] == ns[1]

    def _eat_tokens(self, count:int) -> None:
        """ Поглощает токен. Т.е. передвигает указатель на следующий. """
        # # запрещаем поглощать EOF
        # if self._curtok_num + count < len(self._tokens) - 1:
        self._curtok_num += count
        self._curtok = self._tokens[self._curtok_num]

    def _reset_curtok(self, start_declaration:int) -> None:
        """ Сброс начала обработки токенов до указанного """
        self._curtok_num = start_declaration
        self._curtok = self._tokens[self._curtok_num]

    def _is_line_num(self, line_num:int) -> bool:
        """Проверяет, является ли указанный номер строки текущим"""
        return line_num == self._curtok.lexeme_start[0]

    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        name = self._curtok.ttype.name
        coords = self._curtok.lexeme_start
        print(f"Dirs-Parser Err. {message}: {name} ({self._curtok_num}) [{coords}].")

    def _logic_error(self, message:str) -> None:
        print(f"Dirs-parser Logic error: {message}. Please, report to the developer.")