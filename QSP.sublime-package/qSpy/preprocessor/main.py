import json
from typing import Dict, List, Literal, Optional

Path = str

from .pp_environment import PpEnvironment
from .pp_tokens import TokenNode

from .dirs_scanner import DirsScaner
from .dirs_parser import DirStmt, DirsParser
from .dirs_int import DirsInt

from .pp_scanner import PpScanner
from .pp_parser import PpParser, PpStmt
from .pp_int import MarkedLine, PpInt, QspsLine

from . import error as er

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self, mode:Literal['Off', 'On']) -> None:
        # Препроцессор и окружение для директив общее для всех файлов:
        self._ns = PpEnvironment()
        self._pp:bool = (mode == 'On') # global switch on of preprocessor

        self._dirs_scanner:Optional[DirsScaner] = None
        self._dirs_parser:Optional[DirsParser] = None
        self._dirs_int:Optional[DirsInt] = None
        self._pp_scanner:Optional[PpScanner] = None
        self._pp_parser:Optional[PpParser] = None
        self._pp_int:Optional[PpInt] = None

        self._error_check:bool = False
        ...

    def errored(self) -> bool:
        """ Returns true if pping is broken and resets PP state. """
        return self._error_check

    def dirs_tokens(self) -> List[TokenNode]:
        return self._dirs_scanner.get_token_nodes() if self._dirs_scanner else []

    def dirs_stmts(self) -> List[DirStmt]:
        return self._dirs_parser.get_statements() if self._dirs_parser else []
    
    def dirs_marked_lines(self) -> List[MarkedLine]:
        return self._dirs_int.get_marked_lines() if self._dirs_int else []

    def pp_tokens(self) -> List[TokenNode]:
        return self._pp_scanner.get_token_nodes() if self._pp_scanner else []

    def pp_stmts(self) -> List[PpStmt]:
        return self._pp_parser.get_statements() if self._pp_parser else []

    def pp_fastlines(self) -> List[QspsLine]:
        return self._pp_int.fast_output() if self._pp_int else []

    def pp_this_lines(self, qsps_lines: List[QspsLine]) -> List[QspsLine]:
        """ Preprocess the list of lines. """
        self._error_check = False
        # 1. Scan by directives
        try:
            self._dirs_scanner = DirsScaner(qsps_lines)
            self._dirs_scanner.scan_tokens()
            dirs_tokens = self._dirs_scanner.get_tokens()
            if self._dirs_scanner.errored(): self._error_check 
        except er.DirScannerRunError as e:
            # If alg is corrupted, return source-lines
            self._error_check = True
            print(e)
            return qsps_lines

        # 2. Parse directives
        try:
            self._dirs_parser = DirsParser(dirs_tokens)
            self._dirs_parser.tokens_parse()
            dirs_stmts = self._dirs_parser.get_statements()
            if self._dirs_parser.errored(): self._error_check = True
        except er.DirsParserRunError as e:
            # If alg is corrupted, return source-lines
            self._error_check = True
            print(e)
            return qsps_lines

        # 3. Interpret directives, and marked lines
        try:
            self._dirs_int = DirsInt(dirs_stmts, self._ns, qsps_lines, self._pp)
            self._dirs_int.run()
            marked_lines = self._dirs_int.get_marked_lines()
            # if self._dirs_int.errored(): self._error_check = True
        except er.DirsInterpreterError as e:
            # If alg is corrupted, return source-lines
            self._error_check = True
            print(e)
            return qsps_lines

        # 4. Scan by Stmts
        try:
            self._pp_scanner = PpScanner(marked_lines)
            self._pp_scanner.scan_tokens()
            pp_tokens = self._pp_scanner.get_tokens()
            if self._pp_scanner.errored(): self._error_check = True
        except er.PpScannerRunError as e:
            self._error_check = True
            print(e)
            return qsps_lines

        # 5. Parse by Stmts
        try:
            self._pp_parser = PpParser(pp_tokens)
            self._pp_parser.tokens_parse()
            pp_stmts = self._pp_parser.get_statements()
            if self._pp_parser.errored(): self._error_check = True
        except er.PpParserRunError as e:
            self._error_check = True
            print(e)
            return qsps_lines

        # 6. Interpret by Stmts and markers
        try:
            self._pp_int = PpInt(pp_stmts, marked_lines)
            self._pp_int.run()
            output_lines = self._pp_int.get_output()
            if not output_lines:
                # Pp return empty list of QspsLines, if all locations exclude
                # QspsFile src need not empty list for changing, return this
                return ['\n']
            # if self._pp_int.errored(): self._error_check = True
        except er.PpInterpreterError as e:
            self._error_check = True
            print(e)
            return qsps_lines

        return output_lines
    