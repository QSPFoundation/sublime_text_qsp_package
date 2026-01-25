import re
from typing import List

from .tps import (
    QspsLine, MultilineDesc, Action, LocName, LocCode, BaseFindMode)
from . import base_scanner as scn
from . import base_parser as psr
from . import base_int as bint

from .tools import parse_string

# const
_BASE_OPEN = re.compile(r'^\! BASE\s*$')
_BASE_CLOSE = re.compile(r'^\! END BASE\s*$')

class QspLoc():
    """
        qsp-locations from qsps-file
    """
    def __init__(self, name:LocName, code:LocCode) -> None:
        """ Initialise QSP-location """
        self._name:LocName = name                            # location name qsps

        self._code:LocCode = code    # all location in code qsps view

        self._base_code:List[QspsLine] = []    # base code (qsps lines of base acts and desc)
        self._base_desc:MultilineDesc = ''  # concatenate strings of base descs in text-format
        self._base_actions:List[Action] = [] # list of base actions dicts

        self._run_on_visit:List[QspsLine] = [] # code of Run-on-visit field of location

        self._extract_base()

    def name(self) -> LocName:
        return self._name

    def actions(self) -> List[Action]:
        return self._base_actions

    def desc(self) -> MultilineDesc:
        return self._base_desc

    def run_on_visit(self) -> List[QspsLine]:
        return self._run_on_visit

    def change_name(self, new_name:str) -> None:
        """ Set location name """
        self._name = new_name

    def change_code(self, new_code:List[QspsLine]) -> None:
        """ Set run on visit code. """
        self._run_on_visit = new_code

    def add_code_line(self, code_line:QspsLine) -> None:
        """ Append code line to run on visit code"""
        self._run_on_visit.append(code_line)

    def _extract_base(self) -> None:
        """ Extract qsps-lines of base from location code """
        mode:BaseFindMode = {
            'open_base': False,
            'quote': []
        }
        start:int = -1
        end:int = -1
        base_lines:List[QspsLine] = []
        for i, qsps_line in enumerate(self._code[:]):
            if mode['open_base']:
                if not mode['quote'] and _BASE_CLOSE.search(qsps_line):
                    end = i
                    mode['open_base'] = False
                    break
                base_lines.append(qsps_line)
                parse_string(qsps_line, mode)
                continue
            if not mode['quote'] and _BASE_OPEN.search(qsps_line):
                start = i
                mode['open_base'] = True
            else:
                parse_string(qsps_line, mode)

        if start != end:
            self._base_code = self._code[start+1:end]
            self._run_on_visit = self._code[0:start]+self._code[end+1:]
        else:
            self._run_on_visit = self._code[:]

        print('loc', len(self._base_code))

    def split_base(self) -> None:
        """ Split base code to description and actions """
        if not self._base_code: return # базового описания или действий нет
        scanner = scn.BaseScanner(self._base_code)
        scanner.scan_tokens()
        tokens = scanner.get_tokens()

        parser = psr.BaseParser(tokens)
        parser.parse()
        stmts = parser.get_statements()

        intr = bint.BaseInt(stmts, self._base_code)
        intr.run()

        self._base_desc = intr.desc()
        self._base_actions = intr.actions()

    def get_sources(self) -> List[QspsLine]:
        """ Return qsps-lines of location code, description and actions """
        def _open_act(action:Action) -> QspsLine:
            oa:List[str] = []
            oa.append(f"ACT '{_eqs(action['name'])}'")
            oa.append(f", '{_eqs(action['image'])}':\n" if action['image'] else ':\n')
            return ''.join(oa)
        _eqs = self.escape_qsp_string
        qsps_lines:List[QspsLine] = []
        qsps_lines.append(f"# {self._name}\n")
        if self._base_desc or self._base_actions:
            qsps_lines.append("! BASE\n")
            if self._base_desc:
                qsps_lines.append(f"*P '{_eqs(self._base_desc)}'\n")
            if self._base_actions:
                for action in self._base_actions:
                    qsps_lines.append(_open_act(action))
                    qsps_lines.extend(action['code'])
                    qsps_lines.append('END\n')
            qsps_lines.append("! END BASE\n")
        qsps_lines.extend(self._run_on_visit)
        n = '\n' if self._run_on_visit[-1][-1] != '\n' else ''
        qsps_lines.append(f"{n}-- {self._name} " + ("-" * 33))
        return qsps_lines
    
    @staticmethod
    def escape_qsp_string(qsp_string:str) -> str:
        """ Escape-sequence for qsp-string. """
        return qsp_string.replace("'", "''")
