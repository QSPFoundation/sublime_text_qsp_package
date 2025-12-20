import json
from typing import List, Optional

from pp_environment import PpEnvironment
from pp_scanner import PpScanner
from pp_parser import PpParser
from pp_ast_printer import AstPrinter
from pp_int import PpInt

from pp_tokens import PpToken
from pp_tokens import PpTokenType as tt

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
    out = "..\\..\\[examples]\\example_preprocessor\\pp_ast.json"
    with open(path, 'r', encoding='utf-8') as fp:
        qsps_lines = fp.readlines()

    preprocessor = QspsPP()
    ast_printer = AstPrinter()
    preprocessor.pp_this_lines(qsps_lines, ast_printer)
    ast_tree = ast_printer.get_ast()
    with open(out, 'w', encoding='utf-8') as fp:
        json.dump(ast_tree, fp, ensure_ascii=False, indent=2)