# from tracemalloc import start
from typing import List, Optional, TypedDict, Tuple

from .tokens import TextToken as Tkn, TextTokenType as tt, Point
from . import error as er

ConstantValue = str
Path = str
LocName = str
Region = Tuple[Point, Point]
QspsLine = str

class TextConstant(TypedDict):
    cid: int
    value: ConstantValue
    path: Path
    location: LocName
    place: Region

class TceParser:

    def __init__(self, tokens:List[Tkn], file_path:Path) -> None:
        self._tokens:List[Tkn] = tokens
        self._file:Path = file_path

        # валидация цепочки токенов
        if not self._tokens:
            raise er.TceParserRunError(f'Init-stage. Tokens-chain is empty')
        if self._tokens and self._tokens[-1].ttype != tt.EOF:
            raise er.TceParserRunError(f'Init-stage. There is not EOF in tokens-chain')

        self._curtok_num:int = 0
        self._curtok:Tkn = self._tokens[0]

        self._tbuffer:Optional[Tkn] = None
        self._eated_count:int = 0

        self._loc_is_open:bool = False
        self._loc_name:LocName = ''
        self._cid_counter: int = 0

        self._constants:List[TextConstant] = []

        self._error_check: bool = False

    def errored(self) -> bool:
        return self._error_check

    def tokens_parse(self) -> None:
        """ Публичная функция вызова парсера. """
        # прежде всего разбиваем файл на директивы и блоки
        while not self._is_eof():
            try:
                self._declaration()
            except er.TceParserError as e:
                self._error_check = True
                print(e)
            self._tbuffer = None

    def get_constants(self) -> List[TextConstant]:
        return self._constants

    def _declaration(self) -> None:
        """ Распарсиваем целый файл из токенов. """
        if self._loc_is_open:
            if self._check_type(tt.LOC_CLOSE):
                self._close_loc()
            # elif self._check_type(tt.LOC_OPEN):
                # TODO: теоретически может появиться вариант с подобным началом локации
            elif self._check_type(tt.RAW_LINE):
                # обычную строку пропускаем
                self._eat_tokens(1)
            elif self._match(tt.TEXT_APOSTROPHE_CONST, tt.TEXT_QUOTE_CONST):
                self._constant_line()
            else:
                raise er.TceParserRunError(''.join([
                    f'Unexpected token in location body: ',
                    str(self._curtok.ttype.name), str(self._curtok.lexeme_start)
                    ]))
        else:
            if self._check_type(tt.LOC_OPEN):
                self._open_loc()
            elif self._check_type(tt.RAW_LINE):
                self._eat_tokens(1)
            else:
                raise er.TceParserRunError(f'Expect LOC_OPEN, RAW_LINE. Get {self._curtok.ttype.name}')

    def _constant_line(self) -> None:
        """ Получаем строку """
        cid:int = self._cid_counter
        self._cid_counter += 1
        value:ConstantValue = self._curtok.lexeme
        path:Path = self._file
        location:LocName = self._loc_name
        place:Region = (self._curtok.lexeme_start, self._curtok.get_end_pos())
        self._eat_tokens(1)

        self._constants.append({
            'cid': cid, 'value': value, 'path':path,
            'location': location, 'place': place
        })

    def _open_loc(self) -> None:
        """ Open Loc Statement Create """
        self._loc_is_open = True
        self._loc_name = self._curtok.lexeme[1:].strip()
        self._eat_tokens(1)

    def _close_loc(self) -> None:
        """ Close Loc Statement Create """
        self._loc_is_open = False
        self._loc_name = ''
        self._eat_tokens(1)

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

    def _eat_tokens(self, count:int) -> None:
        """ Поглощает токен. Т.е. передвигает указатель на следующий. """
        self._curtok_num += count # токены передвигаются лишь до EOF, поэтому выход за пределы невозможен
        self._curtok = self._tokens[self._curtok_num]
