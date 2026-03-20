from typing import List, Optional

from .tokens import TokenNode
from .tce_scanner import TceScanner
from . import tce_parser as prs
from .error import TceParserRunError, TceScannerRunError

class TextConstantExtractor:
    """Извлекатель текстовых констант из проекта"""

    def __init__(self, qsps_file:prs.Path, cid_counter_start:int = 0) -> None:
        self._qsps_file:prs.Path = qsps_file
        with open(self._qsps_file, 'r', encoding='utf-8') as fp:
            self._qsps_lines:List[prs.QspsLine] = fp.readlines()

        self._constants:List[prs.TextConstant] = []
        self._const_notes:List[prs.ConstantNote] = []

        self._scanner:Optional[TceScanner] = None
        self._parser:Optional[prs.TceParser] = None

        self._cid_counter:int = cid_counter_start

        self._error_check = False

    def extract_constants(self) -> List[prs.TextConstant]:
        """Вытаскивает из файла текстовые константы и создаёт на безе этого список"""
        # 1. get tokens list
        try:
            self._scanner = scanner = TceScanner(self._qsps_lines)
            scanner.scan_tokens()
            tokens = scanner.get_tokens()
        except TceScannerRunError as e:
            self._error_check = True
            print(e)
            return []

        # 2. get list of constants
        try:
            self._parser = parser = prs.TceParser(tokens, self._qsps_file, self._cid_counter)
            parser.tokens_parse()
            self._constants = parser.get_constants()
            self._const_notes = parser.get_const_notes()
            self._cid_counter = parser.cid_counter()
        except TceParserRunError as e:
            self._error_check = True
            print(e)
            return []

        return self._constants

    def get_constants(self) -> List[prs.TextConstant]:
        return self._constants

    def get_const_container(self) -> prs.ConstFileContainer:
        return {'path': self._qsps_file, 'constants': self._const_notes}

    def get_tokens(self) -> List[TokenNode]:
        return self._scanner.get_token_nodes() if self._scanner else []

    def cid_counter(self) -> int:
        return self._cid_counter






