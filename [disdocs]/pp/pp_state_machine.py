from typing import Callable, Dict, Optional # List, Union, Any

from enum import (IntEnum, auto)
import uuid

import pp_stmts as stmt

class PpSmSignal(IntEnum):
    DEFAULT = 0

    EOF_FOUND = auto()
    EOF_NOT_FOUND = auto()

    FOUND = auto()
    NOT_FOUND = auto() # machine say that chain not found

    TOGGLE = auto()

    I_CLOSE = auto() # machine say that close

    ERROR = auto() # machine say that error

_Sgn = PpSmSignal

_SCHEMES:Dict[str, Dict[str, Dict[_Sgn, str]]] = {
    '_qsps_file_parse': # function name
    {
        'loc_find': # cur state
        {   # signal: new state
            _Sgn.DEFAULT: 'loc_find',
            _Sgn.FOUND: 'loc_save',
            _Sgn.NOT_FOUND: 'dir_find',
            _Sgn.TOGGLE: 'loc_find'
        },
        'dir_find': {
            _Sgn.DEFAULT: 'loc_find',
            _Sgn.FOUND: 'dir_save',
            _Sgn.NOT_FOUND: 'raw_find',
            _Sgn.TOGGLE: 'loc_find'
        },
        'raw_find': {
            _Sgn.DEFAULT: 'loc_find',
            _Sgn.FOUND: 'raw_save',
            _Sgn.NOT_FOUND: 'eof_find',
            _Sgn.ERROR: 'error_eof',
            _Sgn.TOGGLE: 'locfind'
        },
        'eof_find': {
            _Sgn.DEFAULT: 'eof_find',
            _Sgn.EOF_NOT_FOUND: 'error_eof',
            _Sgn.EOF_FOUND: 'close_machine'
        },
        'error_eof': {_Sgn.DEFAULT: 'error_eof'},
        'close_machine': {_Sgn.DEFAULT: 'close_machine'}
    },

    '_dir_parse': # func name
    {
        'open_dir_stmt_find': # cur state
        {   # signal: new sate
            _Sgn.DEFAULT: 'open_dir_stmt_find',
            # 'open_dir_stmt_found': 'directive_parse'
        },
        'directive_parse':
        {
            _Sgn.DEFAULT: 'directive_parse',
            #'directive_parsed': 'close_machine',
            #'directive_not_parsed': 'error_parse'
        }
    },

    '_rawline_parse': # func name
    {
        'raw_find': # cur state
        {   # signal: new sate
            _Sgn.DEFAULT: 'raw_find',
        },
    },

    '_eof_parse': # func name
    {
        'eof_find': # cur state
        {   # signal: new sate
            _Sgn.DEFAULT: 'eof_find'
        }
    }
}

_NODE_TYPE:Dict[str, type] = {
    '_qsps_file_parse': stmt.QspsFileBlock,
    '_dir_parse': stmt.OpenPpDirStmt,
    '_rawline_parse': stmt.RawLineStmt

}

# prepared types
PpSmHandler = Callable[['PpStateMachine', PpSmSignal], PpSmSignal]
_Puuid = Optional[uuid.UUID]

class PpStateMachine:

    def __init__(self,
                 handler:PpSmHandler,
                 parent:_Puuid = None,
                 start_token:int = 0) -> None:
        self.handler:PpSmHandler = handler
        self.scheme:Dict[str, Dict[_Sgn, str]] = _SCHEMES[handler.__name__]
        self.state:str = list(self.scheme.keys())[0] # default state is first in dict
        self.signal:_Sgn = _Sgn.DEFAULT # default signal on start machine
        self.parent:_Puuid = parent
        self.start_token:int = start_token
        node_class = _NODE_TYPE.get(handler.__name__)
        self.node:stmt.PpStmt[None] = node_class([]) if node_class else stmt.PlaceHolder()

        self.id:uuid.UUID = uuid.uuid4()

    def state_handler(self, signal:_Sgn=_Sgn.DEFAULT) -> None:
        """ Переключатель состояний. """
        s = (signal if signal in self.scheme[self.state] else _Sgn.DEFAULT)
        self.state = self.scheme[self.state][s]