import json
from base_scanner import BaseScaner
from base_parser import BaseParser
from base_printer import BasePrinter

if __name__ == "__main__":
    with open('base_example.qsps', 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
    
    scanner = BaseScaner(lines)
    scanner.scan_tokens()
    tokens = scanner.get_tokens()
    nodes = [t.get_as_node() for t in tokens]

    with open('base_example.json', 'w', encoding='utf-8') as fp:
        json.dump(tokens, fp, indent=4, ensure_ascii=False)

    parser = BaseParser(tokens)
    parser.tokens_parse()
    statements = parser.get_statements()

    printer = BasePrinter(statements)
    printer.gen_ast()
    ast = printer.get_ast()

    with open('base_parser.json', 'w', encoding='utf-8') as fp:
        json.dump(ast, fp, indent=4, ensure_ascii=False)