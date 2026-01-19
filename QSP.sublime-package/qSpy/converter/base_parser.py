# from tracemalloc import start
from typing import List, Optional, Any

from base_tokens import BaseToken as Tkn, BaseTokenType as tt

import base_stmt as stm

BaseStmt = stm.BaseStmt[Any]

class BaseParser:

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

    def tokens_parse(self) -> None:
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
        if self._check_type(tt.IDENTIFIER):
            return self._unknown_stmt()
        return self._expression()

    def _unknown_stmt(self) -> stm.Unknown[None]:
        """ Неизвестный оператор! """
        pref, self._tbuffer = self._tbuffer, None
        
        stmt = self._curtok # фиксируем оператор
        self._eat_tokens(1)

        expression = self._expression()

        return stm.Unknown(pref, stmt, expression)

    def _loop(self) -> stm.Loop[None]:
        pref, self._tbuffer = self._tbuffer, None

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
            # токен новой строки не поглощён. Поглощаем
            close = self._curtok
            self._eat_tokens(1)

        return stm.Loop(pref, open_, defines,
                        while_stmt, condition, step_stmt, steps, content, close)

    def _condition(self) -> stm.Condition[None]:
        pref, self._tbuffer = self._tbuffer, None

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
            # токен новой строки не поглощён. Поглощаем
            close = self._curtok
            self._eat_tokens(1)

        return stm.Condition(pref, open_, condition, content, close)

    def _action(self) -> stm.Action[None]:
        """ Поиск действия """
        pref, self._tbuffer = self._tbuffer, None

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
            # токен новой строки не поглощён. Поглощаем
            close = self._curtok
            self._eat_tokens(1)

        return stm.Action(pref, open_, name, image, content, close)

    def _extract_block(self) -> List[BaseStmt]:
        """ извлекает блок операторов до end """
        chain:List[BaseStmt] = []

        while not self._is_eof():
            if self._check_type(tt.END_STMT):
                # end stmt not eating
                return chain
            if self._check_type(tt.PREFORMATTER):
                self._tbuffer = self._curtok
                self._eat_tokens(1)
            chain.append(self._statement())
            self._tbuffer = None
        else:
            self._error('Unexpectable EOF in multiline block')
            return chain

    def _extract_line(self, *pop:tt) -> List[BaseStmt]:
        """ извлекает строку операторов через амперсанд """
        if not pop: pop = (tt.NEWLINE, )
        chain:List[BaseStmt] = []
        while not self._is_eof():
            if self._match(*pop):
                return chain
            chain.append(self._statement())
        else:
            self._error('Unexpectable EOF in single line block')
            return chain

    def _end(self) -> Tkn:
        """ Возвращает токен END и поглощает комментарий за ним """
        close = self._curtok # поглощаем токен END
        self._eat_tokens(1)
        while not self._check_type(tt.EOF):
            if self._match(tt.AMPERSAND, tt.NEWLINE):
                # комментарий после енда оканчивается с новой строкой или на амперсанде
                self._eat_tokens(1)
                break
            if self._check_type(tt.LEFT_BRACE):
                self._braces()
                continue
            self._eat_tokens(1)
        else:
            self._error('Unexpectable EOF in comment after END')
        return close  
            
    def _print_text(self) -> stm.PrintTextStmt[None]:
        """ Оператор вывода текста """
        pref, self._tbuffer = self._tbuffer, None
        
        stmt = self._curtok # фиксируем оператор
        self._eat_tokens(1)

        expression = self._expression()

        return stm.PrintTextStmt(pref, stmt, expression)
        
    def _expression(self, *pop:tt) -> stm.Expression[None]:
        """ Выражение, передаваемое оператору. """
        pref, self._tbuffer = self._tbuffer, None
        if not pop: pop = (tt.EOF, tt.NEWLINE, tt.AMPERSAND, tt.WHILE_STMT, tt.STEP_STMT)
        
        chain:List[BaseStmt] = []
        while not self._match(*pop):
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
            
        return stm.Expression(pref, chain)

    def _parens(self) -> stm.Parens[None]:
        """ Круглые скобки и их содержимое """
        left = self._curtok # получаем и поглощаем левую скобку
        self._eat_tokens(1)
        
        content = self._expression(tt.RIGHT_PAREN)

        if not self._check_type(tt.RIGHT_PAREN):
            self._error('Expected RIGHT PAREN. Getted')
        right = self._curtok # поглощение правой скобки
        self._eat_tokens(1)

        return stm.Parens(left, content, right)

    def _brackets(self) -> stm.Brackets[None]:
        """ Квадратные скобки и их содержимое """
        left = self._curtok # получаем и поглощаем левую скобку
        self._eat_tokens(1)
        
        content = self._expression(tt.RIGHT_BRACKET)

        if not self._check_type(tt.RIGHT_BRACKET):
            self._error('Expected RIGHT BRACKET. Getted')
        right = self._curtok # поглощение правой скобки
        self._eat_tokens(1)

        return stm.Brackets(left, content, right)

    def _braces(self) -> stm.Braces[None]:
        """ Фигурные скобки и их содержимое """
        left = self._curtok # получаем и поглощаем левую скобку
        self._eat_tokens(1)
        
        chain:List[BaseStmt] = []
        while not self._check_type(tt.RIGHT_BRACE):
            if self._check_type(tt.LEFT_BRACE):
                chain.append(self._braces())
            chain.append(stm.Literal(self._curtok))
            self._eat_tokens(1)

        if not self._check_type(tt.RIGHT_BRACE):
            self._error('Expected RIGHT BRACE. Getted')
        right = self._curtok # поглощение правой скобки
        self._eat_tokens(1)

        return stm.Braces(left, chain, right)

    def _comment(self) -> stm.Comment[None]:
        pref, self._tbuffer = self._tbuffer, None

        open_ = self._curtok
        self._eat_tokens(1)

        chain:List[BaseStmt] = []
        while not self._check_type(tt.EOF):
            if self._check_type(tt.NEWLINE):
                chain.append(stm.Literal(self._curtok))
                self._eat_tokens(1)
                break
            if self._check_type(tt.LEFT_BRACE):
                chain.append(self._braces())
                continue
            chain.append(stm.Literal(self._curtok))
            self._eat_tokens(1)

        return stm.Comment(pref, open_, chain)

    # aux operations
    def _is_eof(self) -> bool:
        """ Является ли токен концом файла. """
        return self._curtok.ttype == tt.EOF

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