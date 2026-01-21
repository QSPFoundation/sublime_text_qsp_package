from typing import List, Union, cast, TypedDict

from base_tokens import BaseToken, BaseTokenType as tt

import base_stmt as stm

from error import RuntimeIntError

Path = str

LocName = str
QspsLine = str

MultilineDesc = str

ActionName = str
class Action(TypedDict):
    image: Path
    name: ActionName
    code: List[QspsLine]

AstNode = Union[None, bool, str, BaseToken]

class BaseInt(stm.BaseVisitor[AstNode]):

    def __init__(self,
                 stmts:List[stm.BaseStmt[AstNode]],
                 qsps_lines:List[QspsLine]) -> None:
        self._stmts = stmts
        self._src_lines:List[QspsLine] = qsps_lines

        self._temporary:List[str] = []

        self._actions:List[Action] = []
        self._desc_lines:List[str] = []

    def run(self) -> None:
        """Обработка дерева разбора """
        for stmt in self._stmts:
            try:
                stmt.accept(self)
            except RuntimeIntError as e:
                print(e)

    def actions(self) -> List[Action]:
        return self._actions

    def desc(self) -> str:
        return ''.join(self._desc_lines)


    def visit_print_text_stmt(self, stmt:stm.PrintTextStmt[AstNode]) -> None:
        l = stmt.stmt.lexeme_start[0]
        line = (self._src_lines[l], l)
        lexeme = stmt.stmt.lexeme
        if lexeme.lower() != '*p':
            raise RuntimeIntError(line, 'Expected *P stament for Base Description.')
        if not stmt.expression:
            raise RuntimeError(line, 'Base Description print Expression not specified.')
        expression = cast(str, stmt.expression.accept(self))
        self._desc_lines.append(expression)


    def visit_expression(self, stmt:stm.Expression[AstNode]) -> str:
        l = stmt.line
        line = (self._src_lines[l], l)
        output:str = ''
        for s in stmt.chain:
            if not isinstance(s, stm.Literal):
                raise RuntimeIntError(line, 'Use simple string for Expression.')
            t = cast(stm.Literal[None], s).value
            if not t.ttype in (tt.APOSTROPHE_STRING, tt.QUOTE_STRING):
                raise RuntimeIntError(line, 'Use simple string for Expression.')
            if output:
                raise RuntimeIntError(line, 'Use simple string for Expression.')
            output = t.lexeme.replace('""', '"') if t.ttype == tt.QUOTE_STRING else t.lexeme.replace("''", "'")

        return output[1:-1]


    def visit_expression_stmt(self, stmt:stm.ExpressionStmt[AstNode]) -> AstNode:
        l = stmt.line
        raise RuntimeIntError((self._src_lines[l], l),
                'Implicit Statement not work for Base Description.')


    def visit_literal(self, stmt:stm.Literal[AstNode]) -> BaseToken:
        return stmt.value


    def visit_parens(self, stmt:stm.Parens[AstNode]) -> AstNode:
        l = stmt.left.lexeme_start[0]
        raise RuntimeIntError((self._src_lines[l], l),
                'Do not use parentheses to Expression.')

    def visit_brackets(self, stmt:stm.Brackets[AstNode]) -> AstNode:
        l = stmt.left.lexeme_start[0]
        raise RuntimeIntError((self._src_lines[l], l),
                'Do not use brackets to Expression.')


    def visit_braces(self, stmt:stm.Braces[AstNode]) -> AstNode:
        l = stmt.left.lexeme_start[0]
        raise RuntimeIntError((self._src_lines[l], l),
                'Do not use braces to Expression.')

    def visit_action(self, stmt:stm.Action[AstNode]) -> None:
        start_line = stmt.open.lexeme_start[0]
        close = stmt.close.name
        if close.ttype != tt.END_STMT:
            raise RuntimeIntError((self._src_lines[start_line], start_line),
                'Use multiline actions for Base Actions.')
        end_line = close.lexeme_start[0]
        name = cast(ActionName, stmt.name.accept(self))
        image = cast(Path, stmt.image.accept(self) if stmt.image else '')
        code = self._src_lines[start_line+1:end_line]
        self._actions.append({'image':image, 'name':name, 'code':code})    

    def visit_comment(self, stmt:stm.Comment[AstNode]) -> None:
        return None


    def visit_condition(self, stmt:stm.Condition[AstNode]) -> AstNode:
        l = stmt.line
        raise RuntimeIntError((self._src_lines[l], l),
                'Do not use condition in Base Block.')


    def visit_loop(self, stmt:stm.Loop[AstNode]) -> AstNode:
        l = stmt.line
        raise RuntimeIntError((self._src_lines[l], l),
                'Do not use cycles in Base Block.')


    def visit_unknown(self, stmt:stm.Unknown[AstNode]) -> AstNode:
        l = stmt.line
        raise RuntimeIntError((self._src_lines[l], l),
                'Unknown Statement in Base Block.')


    def visit_end(self, stmt:stm.End[AstNode]) -> str:
        return stmt.name.lexeme


    # обработчик ошибок. Пока просто выводим в консоль.
    def _error(self, message:str) -> None:
        print(f"Err. {message}.")

    def _logic_error(self, message:str) -> None:
        print(f"Logic error: {message}. Please, report to the developer.")