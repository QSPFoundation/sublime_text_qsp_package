import json, os
from typing import Dict, List, Union, cast

from base_scanner import BaseScanner
from base_parser import BaseParser
from base_printer import BasePrinter
from base_int import Action, BaseInt

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))

    with open('.\\base_example.qsps', 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
    
    scanner = BaseScanner(lines)
    scanner.scan_tokens()
    tokens = scanner.get_tokens()
    nodes = scanner.get_token_nodes()

    print('scanner is over')

    with open('base_example.json', 'w', encoding='utf-8') as fp:
        json.dump(nodes, fp, indent=4, ensure_ascii=False)

    parser = BaseParser(tokens)
    parser.parse()
    statements = parser.get_statements()

    print('parser is over')

    printer = BasePrinter(statements)
    printer.gen_ast()
    ast = printer.get_ast()

    print('ast is over')

    with open('base_parser.json', 'w', encoding='utf-8') as fp:
        json.dump(ast, fp, indent=4, ensure_ascii=False)

    interpreter = BaseInt(statements, lines)
    interpreter.run()

    elements:Dict[str, Union[str, List[Action]]] = {'base-description': interpreter.desc(), 'actions':[]}

    for a in interpreter.actions():
        cast(List[Action], elements['actions']).append({'image': a['image'],
        'name': a['name'], 'code': a['code']})

    print('interpreter is over')

    with open('base_output.json', 'w', encoding='utf-8') as fp:
        json.dump(elements, fp, indent=4, ensure_ascii=False)