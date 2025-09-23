import sys, os
from typing import List, Dict

class GenerateAst:

    def __init__(self, args:List[str]) -> None:
        if len(args) != 1:
            print("Usage: generate_ast <output directory>")
            sys.exit(64)
        self.output_folder:str = args[0]

        arr_expr = {
            "QspAssign"   : "name:QspToken, value:QspExpr",
            "QspBinary"   : "left:QspExpr, operator:QspToken, right:QspExpr",
            "QspGrouping" : "expression:QspExpr",
            "QspLiteral"  : "value:Any",
            "QspUnary"    : "operator:QspToken, right:QspExpr",
            "QspVariable" : "name:QspToken"
        }

        arr_stmt = {
            "QspExpression" : "expression:QspExpr",
            "QspPrint"      : "expression:QspExpr",
            "QspVar"        : "name:QspToken, initializer:QspExpr"
        }

        self.define_ast("QspExpr", arr_expr)
        self.define_ast("QspStmt", arr_stmt)

    def define_ast(self, base_name:str, types:Dict[str, str]) -> None:
        path = os.path.join(self.output_folder, f'{base_name.lower()}.py')
        with open(path, 'w', encoding='utf-8') as fp:
            lines:List[str] = [
                'from abc import ABC, abstractmethod',
                'from dataclasses import dataclass',
                'from typing import Generic, TypeVar, Any',
                '',
                'from token_ import QspToken',
                ''
            ]
            if base_name == 'QspStmt':
                lines.extend([
                    'from qspexpr import QspExpr',''])
            lines.extend([
                'R = TypeVar("R")',
                '',
                
                f'class {base_name}(ABC, Generic[R]):',
                f'    """Класс поддержки выражений. Используется в т.ч. для указания типов."""',
                f'    @abstractmethod',
                f'    def accept(self, visitor: "Visitor[R]") -> R:',
                f'        ...',
                f''
            ])

            self.define_visitor(lines, base_name, types)

            for class_name, fields in types.items():
                self.define_type(lines, base_name, class_name, fields)
            
            fp.write('\n'.join(lines))

    def define_visitor(self, lines:List[str], base_name:str, types:Dict[str, str]) -> None:
        b = base_name[3:].lower()
        lines.extend(['class Visitor(ABC, Generic[R]):',
            '    """interface of visitor for Expression"""'
        ])
        for type_name in types.keys():
            t = type_name[3:].lower()
            lines.extend([
                f'    @abstractmethod',
                f'    def visit_{t}_{b}(self, expr:R) -> R:',
                f'        ...',
                f''
            ])

    def define_type(self, lines:List[str], base_name:str, class_name:str, fields:str) -> None:
        c = class_name[3:].lower()
        b = base_name[3:].lower()
        lines.extend([
            '@dataclass',
            f'class {class_name}({base_name}[R]):',
           
        ])
        # constructor and 
        # store parameters in fields
        field_list:List[str] = fields.split(', ')
        for field in field_list:
            name, ext = field.split(":")
            lines.append(f'    {name}: {ext}')
        # fields initialisation in py not needs
        # ...
        # visitor pattern
        lines.extend([
            f'    def accept(self, visitor: Visitor[R]) -> R:',
            f'        return visitor.visit_{c}_{b}(self)',
            f''
        ])


def main():
    gen = GenerateAst(['..\\analyser\\'])

if __name__ == "__main__":
    main()