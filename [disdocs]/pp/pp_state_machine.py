from typing import Callable, Dict, List, Union, Optional, Any

from enum import (IntEnum, auto)
import uuid

class PpSmSignal(IntEnum):
    DEFAULT = 0

    EOF_FOUND = auto()
    EOF_NOT_FOUND = auto()

    FOUND = auto()
    NOT_FOUND = auto() # machine say that chain not found

    I_CLOSE = auto() # machine say that close

    ERROR = auto() # machine say that error

_sgn = PpSmSignal

_SCHEMES:Dict[str, Dict[str, Dict[str, str]]] = {
    '_qsps_file_parse': # function name
    {
        'loc_find': # cur state
        {   # signal: new state
            _sgn.DEFAULT: 'loc_find',
            _sgn.NOT_FOUND: 'dir_find'
        },
        'dir_find': {
            _sgn.DEFAULT: 'loc_find',
            _sgn.NOT_FOUND: 'raw_find'
        },
        'raw_find': {
            _sgn.DEFAULT: 'loc_find',
            _sgn.NOT_FOUND: 'eof_find'
        },
        'eof_find': {
            _sgn.DEFAULT: 'eof_find',
            _sgn.EOF_NOT_FOUND: 'error_eof',
            _sgn.EOF_FOUND: 'close_machine'
        },
        'error_eof': {_sgn.DEFAULT: 'error_eof'},
        'close_machine': {_sgn.DEFAULT: 'close_machine'}
    },

    '_dir_parse': # func name
    {
        'open_dir_stmt_find': # cur state
        {   # signal: new sate
            _sgn.DEFAULT: 'open_dir_stmt_find',
            'open_dir_stmt_found': 'directive_parse'
        },
        'directive_parse':
        {
            _sgn.DEFAULT: 'directive_parse',
            'directive_parsed': 'close_machine',
            'directive_not_parsed': 'error_parse'
        }
    },

    '_rawline_parse': # func name
    {
        'raw_find': # cur state
        {   # signal: new sate
            _sgn.DEFAULT: 'raw_find',
        },
    },

    '_eof_parse': # func name
    {
        'eof_find': # cur state
        {   # signal: new sate
            _sgn.DEFAULT: 'eof_find'
        }
    }
}

class PpStateMachine:

    def __init__(self,
                 handler:Callable[[str, str, uuid.UUID], str],
                 parent:uuid.UUID = None,
                 start_token:int = 0) -> None:
        self.handler:Callable[['PpStateMachine', str], str] = handler
        self.scheme:Dict[str, Dict[str, str]] = _SCHEMES[handler.__name__]
        self.state:str = list(self.scheme.keys())[0] # default state is first in dict
        self.signal:_sgn = _sgn.DEFAULT # default signal on start machine
        self.parent:uuid.UUID = parent
        self.start_token:int = start_token

        self.id:uuid.UUID = uuid.uuid4()

    def state_handler(self, signal:_sgn=_sgn.DEFAULT) -> str:
        """ Переключатель состояний. """
        s = (signal if signal in self.scheme[self.state] else _sgn.DEFAULT)
        self.state = self.scheme[self.state][s]