import os
import concurrent.futures

from typing import List, Dict, Optional

from .tps import (
    QspsLine, Path
)
from .qsps_file import QspsFile
from .qsp_location import QspLoc

AppPath = Path
AppParam = str

QspsChar = str
GameChar = str
CharCache = Dict[QspsChar, GameChar]

GameLine = str # QSP-line string

# constants:
QSP_CODREMOV = 5 # const of cyphering

class QspsToQspConverter:
    """ Converting QspsLine-s to QSP-format. """
    _char_cache:CharCache = {}

    def __init__(self, converter:AppPath, conv_args:AppParam) -> None:
        self._converter = converter
        self._conv_args = conv_args

        self._qsps_file:Optional[QspsFile] = None
        self._game_lines:List[GameLine] = []

    def _qsps_entity_to_game_lines(self, qsps_file:QspsFile) -> List[GameLine]:
        """ Convert QspsFile to QSP-format """
        self._qsps_file = qsps_file
        locs = qsps_file.get_locations()
        # header of qsp-file
        self._game_lines.append('QSPGAME\n')
        self._game_lines.append('SublimeText QSP-Package\n')
        self._game_lines.append(self.encode_qsps_line('No')+'\n')
        self._game_lines.append(self.encode_qsps_line(str(len(locs)))+'\n')
        # decode locations
        def _encode_location(loc:QspLoc) -> List[GameLine]:
            loc.split_base()
            name = loc.name()
            desc = loc.desc()
            actions = loc.actions()
            code_lines = ''.join(loc.run_on_visit()).replace('\n', '\r\n')
            out_lines:List[GameLine] = []
            out_lines.append(QspsToQspConverter.encode_qsps_line(name))
            out_lines.append('\n')
            out_lines.append(QspsToQspConverter.encode_qsps_line(desc))
            out_lines.append('\n')
            out_lines.append(QspsToQspConverter.encode_qsps_line(code_lines))
            out_lines.append('\n')
            out_lines.append(QspsToQspConverter.encode_qsps_line(str(len(actions))))
            out_lines.append('\n')
            for act in actions:
                out_lines.append(QspsToQspConverter.encode_qsps_line(act['image']))
                out_lines.append('\n')
                out_lines.append(QspsToQspConverter.encode_qsps_line(act['name']))
                out_lines.append('\n')
                out_lines.append(QspsToQspConverter.encode_qsps_line(''.join(act['code']).replace('\n', '\r\n')))
                out_lines.append('\n')
            return out_lines
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            # Используем executor.map для получения результатов в порядке отправки задач
            # Если _encode_location возвращает список строк для каждой локации
            results = executor.map(_encode_location, locs)
            for encoded_lines in results:
                self._game_lines.extend(encoded_lines)
        # for location in locs:
        #     _encode_location(location)
        return self._game_lines

    def covert_lines(self, qsps_lines:List[QspsLine]) -> List[GameLine]:
        qsps_file = self._qsps_file = QspsFile(qsps_lines)
        qsps_file.split_to_locations()
        return self._qsps_entity_to_game_lines(qsps_file)

    def convert_file(self, input_file:str, output_file:str) -> None:
        """ Convert qsps-file to qsp-file """
        if not os.path.isfile(input_file): return
        qsps_file = QspsFile()
        qsps_file.read_from_file(input_file)
        qsps_file.split_to_locations()
        self._qsps_entity_to_game_lines(qsps_file)
        self.save_to_file(output_file)

    def save_to_file(self, output_file:Path) -> None:
        with open(output_file, 'w', encoding='utf-16le') as file:
            file.writelines(self._game_lines)

    def save_temp_file(self, output_file:Path) -> None:
        if not self._qsps_file: return
        with open(output_file, 'w', encoding='utf-8-sig') as file:
            file.writelines(self._qsps_file.get_src())

    @staticmethod
    def encode_char(point:QspsChar) -> GameChar:
        """ Encode char. """
        return chr(-QSP_CODREMOV) if ord(point) == QSP_CODREMOV else chr(ord(point) - QSP_CODREMOV)

    @staticmethod
    def encode_qsps_line(qsps_line:QspsLine) -> GameLine:
        """ Decode qsps_line to qsp_coded_line """
        cache = QspsToQspConverter._char_cache
        encode_char = QspsToQspConverter.encode_char

        exit_line:List[GameChar] = []
        for point in qsps_line:
            if point not in cache:
                cache[point] = encode_char(point)
            exit_line.append(cache[point])
        return ''.join(exit_line)