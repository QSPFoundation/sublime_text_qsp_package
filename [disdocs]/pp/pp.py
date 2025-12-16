import json
from typing import List, Any

from pp_scanner import PpScanner
from pp_parser import PpParser
from pp_ast_printer import AstPrinter

from pp_tokens import PpToken
from pp_tokens import PpTokenType as tt

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self) -> None:
        # Здесь будут определяться различные параметры,
        # необходимые для работы одной сессии препроцессора.
        ...

    def pp_this_lines(self, qsps_lines: List[str]) -> List[str]:
        """ Preprocess the list of lines. """
        scanner = PpScanner(qsps_lines)
        scanner.scan_tokens()

        tokens = scanner.get_tokens()

        parser = PpParser(tokens)
        parser.qsps_file_parse()

        statements = parser.get_statements()
        return statements

    
        

if __name__ == "__main__":
    path = "..\\..\\[examples]\\example_preprocessor\\pptest.qsps"
    out = "..\\..\\[examples]\\example_preprocessor\\pp_ast.qsps"
    with open(path, 'r', encoding='utf-8') as fp:
        qsps_lines = fp.readlines()

    preprocessor = QspsPP()
    ast_tree = AstPrinter(preprocessor.pp_this_lines(qsps_lines)).get_ast()
    with open(out, 'w', encoding='utf-8') as fp:
        json.dump(ast_tree, fp)