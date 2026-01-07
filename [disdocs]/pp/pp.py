import json
from typing import List, Optional, Dict, Union

from pp_environment import PpEnvironment
# from pp_scanner import PpScanner
# from pp_parser import PpParser
# from pp_ast_printer import AstPrinter
# from pp_int import PpInt

from pp_tokens import PpToken
from pp_tokens import PpTokenType as tt
from pp_tokens import TokenNode

from dirs_scanner import DirsScaner
from dirs_parser import DirsParser
from dirs_int import DirsInt

from pp_scanner import PpScanner
from pp_parser import PpParser

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self) -> None:
        # Препроцессор и окружение для директив общее для всех файлов:
        self._ns = PpEnvironment()
        ...

    def pp_this_lines(self,
                      qsps_lines: List[str]) -> List[str]:
        """ Preprocess the list of lines. """

        # 1. Scan by directives
        dirs_scanner = DirsScaner(qsps_lines)
        dirs_scanner.scan_tokens()
        dirs_tokens = dirs_scanner.get_tokens()

        # 2. Parse directives
        dirs_parser = DirsParser(dirs_tokens)
        dirs_parser.tokens_parse()
        dirs_stmts = dirs_parser.get_statements()

        if __name__ == "__main__":
            from dirs_ast_printer import DirsAstPrinter
            ast_printer = DirsAstPrinter(dirs_stmts)
            ast_printer.gen_ast()
            ast_tree = ast_printer.get_ast()
            out = ".\\_test\\dirs_ast.json"
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(ast_tree, fp, ensure_ascii=False, indent=2)

        # 3. Interpret directives, and marked lines
        dirs_int = DirsInt(dirs_stmts, self._ns, qsps_lines)
        dirs_int.run()
        marked_lines = dirs_int.get_marked_lines()

        # 4. Scan by Stmts
        pp_scanner = PpScanner(marked_lines)
        pp_scanner.scan_tokens()
        pp_tokens = pp_scanner.get_tokens()

        if __name__ == "__main__":
            out = '.\\_test\\pp_tokens.json'
            l: List[TokenNode] = []
            for t in pp_tokens:
                l.append(t.get_as_node())
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(l, fp, indent=4, ensure_ascii=False)

        # 5. Parse by Stmts

        pp_parser = PpParser(pp_tokens)
        pp_parser.tokens_parse()
        pp_stmts = pp_parser.get_statements()

        if __name__ == "__main__":
            from pp_ast_printer import AstPrinter
            ast_printer = AstPrinter(pp_stmts)
            ast_printer.gen_ast()
            ast_tree = ast_printer.get_ast()
            out = ".\\_test\\pp_ast.json"
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(ast_tree, fp, ensure_ascii=False, indent=2)

        # 6. Interpret by Stmts and markers




    
        

if __name__ == "__main__":
    path = "..\\..\\[examples]\\example_preprocessor\\pptest.qsps"
    with open(path, 'r', encoding='utf-8') as fp:
        qsps_lines = fp.readlines()
    import time
    old = time.time()
    preprocessor = QspsPP()
    preprocessor.pp_this_lines(qsps_lines)
    new = time.time()
    print(['all preprocessing', new-old])