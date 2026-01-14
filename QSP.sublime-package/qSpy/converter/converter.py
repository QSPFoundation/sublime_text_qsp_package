import os
import re
import concurrent.futures

from typing import List, Dict, cast

AppPath = str
AppParam = str

QspsChar = str
GameChar = str
CharCache = Dict[QspsChar, GameChar]

QspsLine = str
GameLine = str # QSP-line string

# constants:
QSP_CODREMOV = 5 # const of cyphering

class QspsToQspConverter:
    """ Converting QspsLine-s to QSP-format. """
    _char_cache:CharCache = {}

    def __init__(self, converter:AppPath, conv_args:AppParam) -> None:
        self._converter = converter
        self._conv_args = conv_args

        self._game_lines:List[GameLine] = []


    def to_qsp(self) -> None:
        """ Convert NewQspsFile to QSP-format """
        if self._game_lines:
            print('[301] Already converted.')
            raise Exception('[301] Already converted.')
        # header of qsp-file
        self._game_lines.append('QSPGAME\n')
        self._game_lines.append('qsps_to_qsp SublimeText QSP Package\n')
        self._game_lines.append(self.encode_qsps_line('No')+'\n')
        self._game_lines.append(self.encode_qsps_line(str(len(self.locations)))+'\n')
        # decode locations
        _decode_location = lambda l: l.encode()
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            for location in self.locations:
                executor.submit(_decode_location, location)
        for location in self.locations:
            self._game_lines.extend(location.get_qsp())

    def convert_file(self, input_file:str) -> None:
        """ Convert qsps-file to qsp-file """
        if not os.path.isfile(input_file): return
        
        self.read_from_file(input_file)
        self.split_to_locations()
        self.to_qsp()
        self.save_to_file()
        


    def save_to_file(self, output_file:str=None) -> None:
        """ Save qsps-text to file. """
        if not output_file:
            output_file = self.output_file
        with open(output_file, 'w', encoding='utf-16le') as file:
            file.writelines(self._game_strings)

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