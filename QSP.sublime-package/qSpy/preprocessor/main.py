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
            # if self._pp_int.errored(): self._error_check = True
        except er.PpInterpreterError as e:
            self._error_check = True
            print(e)
            return qsps_lines

        return output_lines

if __name__ == "__main__":
    from pp_ast_printer import AstPrinter
    from dirs_ast_printer import DirsAstPrinter
    pathes:Dict[str, str] = {
        'input': '..\\..\\..\\[examples]\\example_preprocessor\\pptest.qsps',
        'output': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\output.qsps',
        'expected': '..\\..\\..\\[examples]\\example_preprocessor\\expected.qsps',

        'dirs_tokens': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\01_dirs_tokens.json',
        'dirs_tree': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\02_dirs_tree.json',
        'dirs_lines': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\03_dirs_ml.json',
        
        'pp_tokens': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\04_pp_tokens.json',
        'pp_tree': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\05_pp_ast.json',
        'pp_lines': '..\\..\\..\\[examples]\\example_preprocessor\\_test\\06_pp_fast_out.json'
    }

    def _read_file(path:Path) -> List[str]:
        with open(path, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
        return lines

    def _write_file(path:Path, lines:List[str]) -> None:
        with open(path, 'w', encoding='utf-8') as fp:
            fp.writelines(lines)

    def _write_json(path:Path, obj:object) -> None:
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(obj, fp, ensure_ascii=False, indent=2)

    qsps_lines = _read_file(pathes['input'])
    
    import time
    old = time.time()
    preprocessor = QspsPP('On')
    new_lines = preprocessor.pp_this_lines(qsps_lines)
    new = time.time()

    _write_file(pathes['output'], new_lines)

    print(['all preprocessing', new - old])

    _write_json(pathes['dirs_tokens'], preprocessor.dirs_tokens())

    ast_printer = DirsAstPrinter(preprocessor.dirs_stmts())
    ast_printer.gen_ast()
    _write_json(pathes['dirs_tree'], ast_printer.get_ast())

    _write_json(pathes['dirs_lines'], preprocessor.dirs_marked_lines())

    _write_json(pathes['pp_tokens'], preprocessor.pp_tokens())

    ast_printer = AstPrinter(preprocessor.pp_stmts())
    ast_printer.gen_ast()
    _write_json(pathes['pp_tree'], ast_printer.get_ast())

    _write_json(pathes['pp_lines'], preprocessor.pp_fastlines())

    expected_lines = _read_file(pathes['expected'])
    
    if len(expected_lines) == len(new_lines):
        stop = False
        for i, line in enumerate(expected_lines):
            for j, char in enumerate(line):
                if new_lines[i][j] != char:
                    stop = True
                    print(f'chars not equal {i}, {j}', ['expected', line[0:j+1], 'getted', new_lines[i][0:j+1]])
                    break
            if stop: break
    else:
        print(f'Strings counts not equal. Expected {len(expected_lines)}, geted {len(new_lines)}')
    