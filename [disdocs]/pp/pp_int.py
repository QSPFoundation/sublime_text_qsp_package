from typing import List, Dict, Union, Literal, Tuple, cast

from pp_tokens import LineNum, PpToken, PpTokenType as tt

import pp_stmts as stm

AstNode = Union[None, bool, str]
Modes = Dict[
    Literal[
        'pp',
        'no_save_comm',
        'open_if',
        'include',
        'loc'
    ],
    bool]
QspsLine = str
NoSaveComm = Literal[True, False]
IncludeLine = Literal[True, False]
MarkedLine = Tuple[
    QspsLine,
    NoSaveComm,
    IncludeLine
]
CommentSignal = Literal[
    '', # комментарий исключён, удаляется
    'less_spec_comm', # Удаляется комментарий и вся цепочка операторов до него
    'simple_spec_comm', # удаляется только комментарий
    'base_comment' # обычный комментарий, сохраняется
]
LineMode = Tuple[NoSaveComm, IncludeLine, LineNum]

Context = Dict[
    Literal[
        'in_literal_string',
        'loc_open'
    ]
    
    , bool]

class PpInt(stm.PpVisitor[AstNode]):

    _QUOTES:Dict[tt, str] = {
        tt.APOSTROPHE: "'",
        tt.QUOTE: '"',
        tt.LEFT_BRACE: '{',
        tt.RIGHT_BRACE: '}',
        tt.LEFT_BRACKET: '[',
        tt.RIGHT_BRACKET: ']',
        tt.LEFT_PAREN: '(',
        tt.RIGHT_PAREN: ')'
    }

    def __init__(self,
                 stmts:List[stm.PpStmt[AstNode]],
                 marked_lines:List[MarkedLine]) -> None:
        self._stmts = stmts
        self._output_lines:List[QspsLine] = []
        self._marked_lines:List[MarkedLine] = marked_lines

        self._temporary:List[str] = []

        self._contexts:List[Context] = [{
            'in_literal_string': False,

        }]

    def run(self) -> None:
        """Обработка дерева разбора """
        for stmt in self._stmts:
            stmt.accept(self)

    def get_output(self) -> List[QspsLine]:
        return self._output_lines

    # Statements

    def visit_raw_line_dclrt(self, stmt: stm.RawLineStmt[AstNode]) -> AstNode:
        # Сырую строку между локациями не возвращаем,
        # обрабатывать её не нужно в любом режиме.
        pass

    def visit_loc_open_dclrt(self, stmt: stm.PpQspLocOpen[AstNode]) -> AstNode:
        include_line = stmt.name.include_line
        if include_line:
            line_num = stmt.name.lexeme_start[0]
            self._add_qsps_line(line_num)
            self._loc('open')

    def visit_loc_close_dclrt(self, stmt: stm.PpQspLocClose[AstNode]) -> AstNode:
        # аналогично ^
        if stmt.name.include_line:
            self._add_qsps_line(stmt.name.lexeme_start[0])
            self._loc('close')

    def visit_stmts_line(self, stmt: stm.StmtsLine[AstNode]) -> AstNode:
        # StmtsLine требует определить, сохраняем мы её, или нет.
        comment_validate = self._outer_comments_handler(stmt.comment) if stmt.comment else ''
        if comment_validate == 'less_spec_comm':
            # это означает, что вся цепочка StmtsLine исключается из конечного файла
            return
        # Остались три случая. Обычный комментарий, отсутствующий, или простой спецкомментарий
        # в случае обычного, мы его обрабатываем, как набор токенов
        comment_line:List[str] = []
        if comment_validate == 'base_comment':
            comm = cast(stm.CommentStmt[AstNode], stmt.comment)
            comment_line.append(comm.name.lexeme)
            comment_line.extend(t.lexeme for t in comm.value)
        
        
        self._temporary = []
        for other_stmt in stmt.stmts:
            other_stmt.accept(self)
        if comment_line:
            self._temporary.extend(comment_line)
        elif comment_validate == 'simple_spec_comm':
            # специальный комментарий не попадёт в выходной файл, но перенос строки надо сохранить
            self._temporary.append('\n')
        if len(self._temporary) >= 2 and self._temporary[-2].strip() == '&': self._temporary.pop(-2)
        self._output_lines.extend(self._temporary)
        self._temporary = []

    def visit_comment_stmt(self, stmt: stm.CommentStmt[AstNode]) -> AstNode:
        # CommentStmt является либо частью OtherStmt, либо самостоятельным оператором
        comment_validate:CommentSignal = self._outer_comments_handler(stmt)
        # только при получении сигнала 'base_comment' комментарий сохраняется
        if comment_validate == 'base_comment':
            sl  = (stmt.pref.lexeme_start[0] if stmt.pref else stmt.name.lexeme_start[0])
            el = (stmt.value[-1].get_end_pos()[0] if stmt.value else sl)
            self._extend_qsps_lines(sl, el)

    def visit_other_stmt(self, stmt: stm.OtherStmt[AstNode]) -> AstNode:
        for s in stmt.chain:
            # обрабатываем цепочку
            s.accept(self)
 
    def visit_string_literal(self, stmt: stm.StringLiteral[AstNode]) -> AstNode:
        self._new_context()
        self._contexts[-1]['in_literal_string'] = True
        if stmt.left.include_line:
            self._temporary.append(self._QUOTES[stmt.left.ttype])
        for s in stmt.value:
            s.accept(self)
        if stmt.left.include_line:
            self._temporary.append(self._QUOTES[stmt.left.ttype])
        self._contexts.pop()

    def visit_raw_string_line(self, stmt: stm.RawStringLine[AstNode]) -> AstNode:
        for tkn in stmt.value:
            if tkn.include_line: self._temporary.append(tkn.lexeme)

    def visit_pp_literal(self, stmt: stm.PpLiteral[AstNode]) -> AstNode:
        if not stmt.value.include_line: return
        self._temporary.append(stmt.value.lexeme)
        

    def visit_bracket_block(self, stmt: stm.BracketBlock[AstNode]) -> AstNode:
        if stmt.left.include_line:
            self._temporary.append(self._QUOTES[stmt.left.ttype])
        if stmt.value: stmt.value.accept(self)
        if stmt.right.include_line:
            self._temporary.append(self._QUOTES[stmt.right.ttype])

    # outer handlers
    def _outer_comments_handler(self,
        stmt:stm.CommentStmt[AstNode]) -> CommentSignal:
        # nosavecomm, include, line_num
        sc, si, sl  = (self._get_include_start(stmt.pref) if stmt.pref
            else self._get_include_start(stmt.name))
        ec, ei, _ = (self._get_include_end(stmt.value[-1]) if stmt.value
            else (sc, si, sl))
        comment_signal = cast(CommentSignal, {
            tt.EXCLAMATION_SIGN: 'base_comment',
            tt.LESS_SPEC_COMM: 'less_spec_comm',
            tt.SIMPLE_SPEC_COMM: 'simple_spec_comm'
        }[stmt.name.ttype])
        if not (si and ei):
            # если хотя бы одна из строк комментария исключена, исключаем весь комментарий
            return ''
        elif stmt.name.ttype in (tt.LESS_SPEC_COMM, tt.SIMPLE_SPEC_COMM) and sc and ec:
            # если это спецкомментарий, и не запрещено их обрабатывать
            # тоже они исключаются, но посылают сигнал, чтобы обработать операторы
            return comment_signal
        else:
            # это не спецкомментарии, либо запрещено их обрабатывать
            return 'base_comment'

    # aux funcs

    def _loc_is_open(self) -> bool:
        return self._contexts[-1]['loc_open']

    def _loc(self, sets:Literal['open', 'close']) -> None:
        self._contexts[-1]['loc_open'] = (sets == 'open')

    def _new_context(self) -> None:
        cur = self._contexts[-1]
        self._contexts.append({})
        self._contexts[-1].update(cur)

    def _add_qsps_line(self, line_num:LineNum) -> None:
        self._output_lines.append(self._marked_lines[line_num][0])

    def _extend_qsps_lines(self, start_line:LineNum, end_line:LineNum) -> None:
        self._output_lines.extend([
            ml[0] for ml in self._marked_lines[start_line:end_line+1]
        ])

    def _get_include_start(self, tkn:PpToken) -> LineMode:
        start_nosavecomm = tkn.no_save_comment
        start_include = tkn.include_line
        start_line = tkn.lexeme_start[1]
        return start_nosavecomm, start_include, start_line

    def _get_include_end(self, tkn:PpToken) -> LineMode:
        end_nosavecomm = tkn.no_save_comment
        end_include = tkn.include_line
        end_line = tkn.get_end_pos()[0]
        return end_nosavecomm, end_include, end_line


    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        print(f"Err. {message}.")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")