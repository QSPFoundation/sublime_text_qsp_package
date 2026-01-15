import json
from typing import List, Literal, Optional

from pp_environment import PpEnvironment
from pp_tokens import TokenNode

from dirs_scanner import DirsScaner
from dirs_parser import DirsParser
from dirs_int import DirsInt

from pp_scanner import PpScanner
from pp_parser import PpParser
from pp_int import PpInt

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self, mode:Literal['Off', 'On']) -> None:
        # Препроцессор и окружение для директив общее для всех файлов:
        self._ns = PpEnvironment()
        self._pp:bool = (mode == 'On') # global switch on of preprocessor

        self._dirs_scanner:Optional[DirsScaner] = None
        self._dirs_scanner:Optional[DirsScaner] = None
        self._dirs_scanner:Optional[DirsScaner] = None
        self._dirs_scanner:Optional[DirsScaner] = None
        self._dirs_scanner:Optional[DirsScaner] = None
        self._dirs_scanner:Optional[DirsScaner] = None
        ...

    def pp_this_lines(self, qsps_lines: List[str]) -> List[str]:
        """ Preprocess the list of lines. """

        # 1. Scan by directives
        dirs_scanner = DirsScaner(qsps_lines)
        dirs_scanner.scan_tokens()
        dirs_tokens = dirs_scanner.get_tokens()

        if __name__ == "__main__":
            out = '..\\..\\..\\[examples]\\example_preprocessor\\_test\\01_dirs_tokens.json'
            out_l: List[TokenNode] = []
            for t in dirs_tokens:
                out_l.append(t.get_as_node())
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(out_l, fp, indent=4, ensure_ascii=False)

        # 2. Parse directives
        dirs_parser = DirsParser(dirs_tokens)
        dirs_parser.tokens_parse()
        dirs_stmts = dirs_parser.get_statements()

        if __name__ == "__main__":
            from dirs_ast_printer import DirsAstPrinter
            ast_printer = DirsAstPrinter(dirs_stmts)
            ast_printer.gen_ast()
            ast_tree = ast_printer.get_ast()
            out = "..\\..\\..\\[examples]\\example_preprocessor\\_test\\02_dirs_tree.json"
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(ast_tree, fp, ensure_ascii=False, indent=2)

        # 3. Interpret directives, and marked lines
        dirs_int = DirsInt(dirs_stmts, self._ns, qsps_lines)
        dirs_int.run()
        marked_lines = dirs_int.get_marked_lines()

        if __name__ == "__main__":
            out = '..\\..\\..\\[examples]\\example_preprocessor\\_test\\03_dirs_ml.json'
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(marked_lines, fp, indent=4, ensure_ascii=False)

        # 4. Scan by Stmts
        pp_scanner = PpScanner(marked_lines)
        pp_scanner.scan_tokens()
        pp_tokens = pp_scanner.get_tokens()

        if __name__ == "__main__":
            out = '..\\..\\..\\[examples]\\example_preprocessor\\_test\\04_pp_tokens.json'
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
            out = "..\\..\\..\\[examples]\\example_preprocessor\\_test\\05_pp_ast.json"
            with open(out, 'w', encoding='utf-8') as fp:
                json.dump(ast_tree, fp, ensure_ascii=False, indent=2)

        # 6. Interpret by Stmts and markers

        pp_int = PpInt(pp_stmts, marked_lines)
        pp_int.run()
        output_lines = pp_int.get_output()

        if __name__ == "__main__":
            print(pp_int.fast_output())
            out = "..\\..\\..\\[examples]\\example_preprocessor\\_test\\output.qsps"
            with open(out, 'w', encoding='utf-8') as fp:
                fp.write(''.join(output_lines))

        return output_lines

if __name__ == "__main__":
    path = "..\\..\\..\\[examples]\\example_preprocessor\\pptest.qsps"
    with open(path, 'r', encoding='utf-8') as fp:
        qsps_lines = fp.readlines()
    import time
    old = time.time()
    preprocessor = QspsPP('On')
    new_lines = preprocessor.pp_this_lines(qsps_lines)
    new = time.time()
    print(['all preprocessing', new-old])
    expected = "..\\..\\..\\[examples]\\example_preprocessor\\expected.qsps"
    with open(expected, 'r', encoding='utf-8') as fp:
        expected_lines = fp.readlines()
    if len(expected_lines) == len(new_lines):
        stop = False
        for i, line in enumerate(expected_lines):
            for j, char in enumerate(line):
                if new_lines[i][j] != char:
                    stop = True
                    print(f'chars not equal {i}, {j}', ['expected', line[0:j+1], 'getted', new_lines[i][0:j+1]])
                    break
            if stop: break
        print(new_lines)
    else:
        print(f'Strings counts not equal. Expected {len(expected_lines)}, geted {len(new_lines)}')
    