import re
from typing import List, Dict, Literal, Union

from tools import BaseFindMode, parse_string

# const
BASE_OPEN = re.compile(r'^\! BASE$')
BASE_CLOSE = re.compile(r'^\! END BASE$')

class QspLoc():
    """
        qsp-locations from qsps-file
    """
    def __init__(self, name:LocName, code:List[QspsLine]) -> None:
        """ Initialise QSP-location """
        self._name:LocName = name                            # location name qsps

        self._code:List[QspsLine] = code    # all location in code qsps view

        self._base_code:List[QspsLine] = []    # base code (qsps lines of base acts and desc)
        self._base_desc:MultilineDesc = ''  # concatenate strings of base descs in text-format
        self._base_actions:List[Action] = [] # list of base actions dicts

        self._run_on_visit:List[QspsLine] = [] # code of Run-on-visit field of location

        self._extract_base()

    def change_name(self, new_name:str) -> None:
        """ Set location name """
        self.name = new_name

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
            'quote': [],
        }
        start:int = -1
        end:int = -1
        base_lines:List[QspsLine] = []
        for i, qsps_line in enumerate(self._code[:]):
            if mode['open_base']:
                if not mode['quote'] and BASE_CLOSE.search(qsps_line):
                    end = i
                    mode['open_base'] = False
                    break
                base_lines.append(qsps_line)
                parse_string(qsps_line, mode)
                continue
            if not mode['quote'] and BASE_OPEN.search(qsps_line):
                start = i
                mode['open_base'] = True
            else:
                parse_string(qsps_line, mode)

        if start != end:
            self._base_code = self._code[start+1:end]
            self._run_on_visit = self._code[0:start]+self._code[end+1:]
        else:
            self._run_on_visit = self._code[:]

    def split_base(self) -> None:
        """ Split base code to description and actions """
        
            if _all_modes_off(mode):
                if IMPLICIT_OPERATOR.match(line):
                    _string_to_desc(line, mode, 'open-implicit')
                elif PRINT_LINE.match(line):
                    # строка с командой вывода текста
                    _string_to_desc(line[3:], mode, 'open-pl')                    
                elif PRINT_STRING.match(line):
                    _string_to_desc(line[2:], mode, 'open-p')
                elif  ACTION_START.match(line):
                    _string_to_act(line[3:], mode, base_act_buffer)
                else:
                    NewQspsFile.parse_string(line, mode)
            elif mode['open-pl']:
                _string_to_desc(line, mode, 'open-pl')
            elif mode['open-p']:
                _string_to_desc(line, mode, 'open-p')
            elif mode['open-implicit']:
                _string_to_desc(line, mode, 'open-implicit')
            elif mode['action-code']:
                if mode['open-string'] == '' and ACTION_END.match(line):
                    # найдено окончание кода, закрываем
                    mode['action-code'] = False
                    self.base_actions.append(base_act_buffer.copy())
                    base_act_buffer = _empty_buffer()
                else:
                    base_act_buffer['code'].append(line)
                    NewQspsFile.parse_string(line, mode)
            elif mode['action-image'] or mode['action-name']:
                # переносы строк в названиях и изображениях базовых действий недопустимы
                mode['action-name'] = False
                mode['action-image'] = False
                base_act_buffer = _empty_buffer()
                NewQspsFile.parse_string(line, mode)
            elif mode['open-string']:
                NewQspsFile.parse_string(line, mode)

    def get_sources(self) -> list:
        """ Return qsps-lines of location code, description and actions """
        _eqs = NewQspLocation.escape_qsp_string
        qsps_lines = []
        qsps_lines.append(f"# {self.name}\n")
        if self.base_description or self.base_actions:
            qsps_lines.append("! BASE\n")
            if self.base_description:
                qsps_lines.append(f"*P '{_eqs(self.base_description)}'\n")
            if self.base_actions:
                for action in self.base_actions:
                    open_act = f"ACT '{_eqs(action['name'])}'"
                    open_act += (f", '{_eqs(action['image'])}':" if action['image'] else ':')
                    qsps_lines.append(open_act)
                    qsps_lines.extend(['\n'+line for line in action['code']] if action['code'] else [])
                    qsps_lines.append('END\n')
            qsps_lines.append("! END BASE\n")
        qsps_lines.extend(self.code)
        qsps_lines.append(f"-- {self.name} " + ("-" * 33))
        return qsps_lines
    
    @staticmethod
    def escape_qsp_string(qsp_string:str) -> str:
        """ Escape-sequence for qsp-string. """
        return qsp_string.replace("'", "''")


if __name__ == "__main__":
    code:List[QspsLine] = [
        "! BASE", 
"if $args[0] = '[м:1]_моя_комната':", 
"	if help[$args[0]]=0:", 
"		$args['result.help']=@int.din.text('<font color=#ff4444>Добро пожаловать в безграничный мир Асгар.",
"Сейчас тыользоваться заклинанием \"Перст Гемеры\", оно находится в меню инвентаря \"Изученные заклинания\".</font>')",
"! END BASE", 
"	elseif help[$args[0]]=1:", 
"		$args['result.help']=@int.din.text('<font color=#ff4444>Отличнойствию или ссылке. Добавленные предметы появляются в меню \"Инвентарь\", или во вложенных меню.</font>')", 
"	elseif help[$args[0]]=2:", 
"		$args['result.help']=@int.din.text('<font color=#ff4444>В к.</font>')", 
"	elseif help[$args[0]]=3:", 
"		$args['result.help']=@int.din.text('<font color=#ff4444></font>')", 
"	end", 
"end", 
"! BASE", 
"if $args[0] = '':	killvar '$help'", 
"! END BASE", 
"$result['[help]'] = $args['result.help'] + @b.w.s('help')", 
    ]
    loc = QspLoc('start', code)
    loc.extract_base()
    loc.print_code()