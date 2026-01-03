import json
from typing import List, Optional

from pp_environment import PpEnvironment
from pp_scanner import PpScanner
from pp_parser import PpParser
from pp_ast_printer import AstPrinter
from pp_int import PpInt

from pp_tokens import PpToken
from pp_tokens import PpTokenType as tt

from dir_scanner import DirsScaner

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self) -> None:
        # Препроцессор и окружение для директив общее для всех файлов:
        self._ns = PpEnvironment()
        ...

    def pp_this_lines(self,
                      qsps_lines: List[str],
                      ast_printer:Optional[AstPrinter]=None) -> List[str]:
        """ Preprocess the list of lines. """
        # 1. Scan by directives
        dirs_scanner = DirsScaner(qsps_lines)
        dirs_scanner.scan_tokens()
        dirs_tokens = dirs_scanner.get_tokens()
        # 2. Parse directives
        dirs_parser = DirParser(dirs_tokens)
        # 3. Interpret directives, and marked lines

        # 4. Scan by Stmts
        # 5. Parse by Stmts
        # 6. Interpret by Stmts and markers

        scanner = PpScanner(qsps_lines)
        scanner.scan_tokens()
        tokens = scanner.get_tokens()

        parser = PpParser(tokens)
        parser.qsps_file_parse()
        statements = parser.get_statements()
        
        if ast_printer:
            ast_printer.gen_ast(statements)

        interpreter = PpInt(statements, self._ns, qsps_lines)
        interpreter.run()



    
        

if __name__ == "__main__":
    path = "..\\..\\[examples]\\example_preprocessor\\pptest.qsps"
    out = ".\\_test\\pp_ast.json"
    with open(path, 'r', encoding='utf-8') as fp:
        qsps_lines = fp.readlines()

    import time
    old = time.time()
    preprocessor = QspsPP()
    ast_printer = AstPrinter()
    preprocessor.pp_this_lines(qsps_lines, ast_printer)
    ast_tree = ast_printer.get_ast()
    new = time.time()
    print(['new pp all time: ', new-old])
    with open(out, 'w', encoding='utf-8') as fp:
        json.dump(ast_tree, fp, ensure_ascii=False, indent=2)