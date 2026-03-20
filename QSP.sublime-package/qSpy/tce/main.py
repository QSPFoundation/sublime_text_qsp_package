from typing import List
import json

from .tce_scanner import TceScanner
from . import tce_parser as prs
from .error import TceParserRunError, TceScannerRunError

class TextConstantExtractor:
    """Извлекатель текстовых констант из проекта"""

    def __init__(self, qsps_file:prs.Path) -> None:
        self._qsps_file:prs.Path = qsps_file
        with open(self._qsps_file, 'r', encoding='utf-8') as fp:
            self._qsps_lines:List[prs.QspsLine] = fp.readlines()

        self._constants:List[prs.TextConstant] = []

        self._error_check = False

    def extract_constants(self) -> List[prs.TextConstant]:
        """Вытаскивает из файла текстовые константы и создаёт на безе этого список"""
        # 1. get tokens list
        try:
            scanner = TceScanner(self._qsps_lines)
            scanner.scan_tokens()
            tokens = scanner.get_tokens()
            ts = scanner.get_token_nodes()
            with open('toks.json', 'w', encoding='utf-8') as fp:
                json.dump(ts, fp, indent=4, ensure_ascii=False)
        except TceScannerRunError as e:
            self._error_check = True
            print(e)
            return []

        # 2. get list of constants
        try:
            parser = prs.TceParser(tokens, self._qsps_file)
            parser.tokens_parse()
            self._constants = parser.get_constants()
        except TceParserRunError as e:
            self._error_check = True
            print(e)
            return []

        return self._constants






