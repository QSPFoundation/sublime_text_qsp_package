# _pp_test_.py

if __name__ == "__main__":
    from pp_ast_printer import AstPrinter
    from dirs_ast_printer import DirsAstPrinter
    pathes:Dict[str, str] = {
        'input': '..\\..\\..\\_examples\\example_preprocessor\\pptest.qsps',
        'output': '..\\..\\..\\_examples\\example_preprocessor\\_test\\output.qsps',
        'expected': '..\\..\\..\\_examples\\example_preprocessor\\expected.qsps',

        'dirs_tokens': '..\\..\\..\\_examples\\example_preprocessor\\_test\\01_dirs_tokens.json',
        'dirs_tree': '..\\..\\..\\_examples\\example_preprocessor\\_test\\02_dirs_tree.json',
        'dirs_lines': '..\\..\\..\\_examples\\example_preprocessor\\_test\\03_dirs_ml.json',
        
        'pp_tokens': '..\\..\\..\\_examples\\example_preprocessor\\_test\\04_pp_tokens.json',
        'pp_tree': '..\\..\\..\\_examples\\example_preprocessor\\_test\\05_pp_ast.json',
        'pp_lines': '..\\..\\..\\_examples\\example_preprocessor\\_test\\06_pp_fast_out.json'
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