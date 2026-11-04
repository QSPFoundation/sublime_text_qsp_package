from abc import ABC, abstractmethod
import os, subprocess
import concurrent.futures

from typing import List, Optional

from .tps import (
    QspsLine, Path
)
from .qsps_file import QspsFile
from .qsp_location import QspsLoc

from .tools import del_first_pref, QSP_CODREMOV

AppPath = Path
AppParam = str

GameLine = str # QSP-line string

# Таблица кодирования «qsp ±5» (B9): единый НЕизменяемый dict ordinal→ordinal, строится
# один раз при импорте — вместо прежнего разделяемого ИЗМЕНЯЕМОГО _char_cache. Кодирование
# qsps→qsp — чистый посимвольный сдвиг кодовой точки на -QSP_CODREMOV: символ cp уходит в
# cp-QSP_CODREMOV. str.translate только ЧИТАЕТ таблицу, поэтому при вызове encode_qsps_line
# из ThreadPoolExecutor гонки нет. Диапазон: BMP начиная с QSP_CODREMOV+1 (точки ниже неё не
# сдвигаются — на них chr() от отрицательного падал и раньше); астральные (> U+FFFF)
# translate оставляет без изменения — QSP-движок фактически BMP-only.
ENCODE_TABLE = {cp: cp - QSP_CODREMOV for cp in range(QSP_CODREMOV + 1, 0x10000)}

class QspsToQspConverter(ABC):

    def __init__(self, output_file:Path, save_temp_files:bool,
                 conv_path:Path = '', conv_args:AppParam = '') -> None:
        # conv_path/conv_args — конфигурация ВНЕШНЕго конвертера (нужна только QspsToQspOuterConv).
        # Объявлены в базовом контракте, чтобы builder единообразно строил любой конвертер; сам
        # базовый класс их не сохраняет (были `*args` — теряли имена и арность; решение B9).
        self._save_temp_files:bool = save_temp_files

        self._module_path:Path = output_file
        self._temp_file_path:Path = os.path.splitext(output_file)[0]+'.txt'

    @abstractmethod
    def convert_lines(self, qsps_lines:List[QspsLine]) -> List[GameLine]:
        ...

    @abstractmethod
    def convert_file(self, input_file:str, output_file:str) -> None:
        ...

    @abstractmethod
    def handle_temp_file(self) -> None:
        ...

    @abstractmethod
    def save_to_file(self, output_file:Path = '') -> None:
        ...

class QspsToQspBuiltinConv(QspsToQspConverter):
    """ Converting QspsLine-s to QSP-format. """
    # По сути нам нужны три режима работы:
    #   - Получить строки, сконвертировать, вернуть сконвертированные: .convert_lines()
    #   - Получить файл, сконвертировать сохранить: .convert_file()
    #   - Получить строки, сконвертировать, сохранить: .convert_lines() + .save_to_file()

    def __init__(self, output_file:Path, save_temp_files:bool,
                 conv_path:Path = '', conv_args:AppParam = '') -> None:
        # conv_path/conv_args приняты ради единой сигнатуры построения, но builtin-конвертеру не
        # нужны: он кодирует в памяти и не запускает внешний процесс → намеренно игнорируются (B9).
        super().__init__(output_file, save_temp_files)

        self._qsps_file:Optional[QspsFile] = None
        self._game_lines:List[GameLine] = []

    def _qsps_entity_to_game_lines(self, qsps_file:QspsFile) -> List[GameLine]:
        """ Convert QspsFile to QSP-format.

        Канон `.qsp` — CRLF (эталонные QGen/txt2gam, см. Q6): game_lines строятся уже с
        `'\r\n'`, а `save_to_file` пишет с `newline=''` (без платформенной трансляции) →
        идентичный побайтовый вывод на Windows/Linux и нет сдвоенного `'\r\r\n'`.
        """
        self._qsps_file = qsps_file
        locs = qsps_file.get_locations()
        NL = '\r\n'  # единый терминатор строки `.qsp` (CRLF)
        # header of qsp-file
        self._game_lines.append(f'QSPGAME{NL}')
        self._game_lines.append(f'SublimeText QSP-Package{NL}')
        # РЕШЕНИЕ Q11(A): qsps-формат (как в txt2gam) несёт только локации, без метаданных →
        # пароль/line-2 на build неоткуда восстановить, пишем дефолт намеренно.
        self._game_lines.append(self.encode_qsps_line('No') + NL)
        self._game_lines.append(self.encode_qsps_line(str(len(locs))) + NL)

        def _encode_location(loc:QspsLoc) -> List[GameLine]:
            loc.split_base()
            name = loc.name()
            desc = loc.desc()
            actions = loc.actions()
            run_on_visit = loc.run_on_visit()
            if run_on_visit:
                run_on_visit[-1] = run_on_visit[-1][:-1] # crunch for extra \n-char in end lines
                code_lines:str = ''.join(run_on_visit).replace('\n', NL)
            else:
                code_lines = ''
            out_lines:List[GameLine] = []
            out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(name))
            out_lines.append(NL)
            out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(desc))
            out_lines.append(NL)
            out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(code_lines))
            out_lines.append(NL)
            out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(str(len(actions))))
            out_lines.append(NL)
            for act in actions:
                out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(act['image']))
                out_lines.append(NL)
                out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(act['name']))
                out_lines.append(NL)
                act_code = del_first_pref(act['code'])
                act_code[-1] = act_code[-1][:-1]
                out_lines.append(QspsToQspBuiltinConv.encode_qsps_line(''.join(act_code).replace('\n', NL)))
                out_lines.append(NL)
            return out_lines
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
            # Используем executor.map для получения результатов в порядке отправки задач
            # Если _encode_location возвращает список строк для каждой локации
            results = executor.map(_encode_location, locs)
            for encoded_lines in results:
                self._game_lines.extend(encoded_lines)
        return self._game_lines

    def convert_lines(self, qsps_lines:List[QspsLine]) -> List[GameLine]:
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

    def save_to_file(self, output_file:Path = '') -> None:
        if not output_file: output_file = self._module_path
        output_folder:Path = os.path.dirname(output_file)
        os.makedirs(output_folder, exist_ok=True)
        # РЕШЕНИЕ Q6 (подтверждено реальными .qsp QGen 4.3.0-b1 / txt2gam 0.4.0): канон —
        # UTF-16LE **без BOM** (плеер/QGen так и выдают). `'utf-16le'` в Python BOM не пишет →
        # это намеренно корректный выбор, а не упущение (не 'utf-16', который добавил бы BOM).
        # `newline=''` отключает платформенную подстановку конца строки: game_lines уже несут
        # канонный CRLF (см. _qsps_entity_to_game_lines) → пишем побайтово, без двойного CR.
        with open(output_file, 'w', encoding='utf-16le', newline='') as file:
            file.writelines(self._game_lines)

    def handle_temp_file(self) -> None:
        if not (self._qsps_file and self._save_temp_files): return
        with open(self._temp_file_path, 'w', encoding='utf-8') as file:
            file.writelines(self._qsps_file.get_src())

    @staticmethod
    def encode_qsps_line(qsps_line:QspsLine) -> GameLine:
        """ Encode qsps_line to qsp_coded_line: посимвольный сдвиг на -QSP_CODREMOV
        через неизменяемую ENCODE_TABLE (B9: нет разделяемого состояния → нет гонки). """
        return qsps_line.translate(ENCODE_TABLE)

class QspsToQspOuterConv(QspsToQspConverter):
    """ Обёртка для запуска внешнего конвертера, с ориентированием на txt2gam """
    def __init__(self, output_file:Path, save_temp_files:bool,
                 conv_path:Path = '', conv_args:AppParam = '') -> None:
         super().__init__(output_file, save_temp_files)

         self._conv_path:Path = conv_path
         self._conv_args:AppParam = conv_args

    def convert_lines(self, qsps_lines:List[QspsLine]) -> List[GameLine]:
        """ Convert lines to game file by outer converter """
        os.makedirs(os.path.split(self._temp_file_path)[0], exist_ok=True)
        with open(self._temp_file_path, 'w', encoding='utf-8') as file:
            file.writelines(qsps_lines)
        _run = [self._conv_path, self._temp_file_path, self._module_path]
        if self._conv_args: _run.append(self._conv_args)
        subprocess.run(_run, stdout=subprocess.PIPE)
        # Возврат [] — ОСОЗНАННО (решение B10): внешний конвертер пишет .qsp сам,
        # in-memory game-строк не производит (product — файл на диске); builder возврат игнорирует.
        return []

    def convert_file(self, input_file:str, output_file:str) -> None:
        # НЕ живой путь: builder для outer использует convert_lines; convert_file внешнего
        # конвертера нигде не вызывается, реализован только ради @abstractmethod-контракта.
        # Пустой conv_args в argv не уходит (консистентно с convert_lines).
        _run = [self._conv_path, input_file, output_file]
        if self._conv_args: _run.append(self._conv_args)
        subprocess.run(_run, stdout=subprocess.PIPE)

    def handle_temp_file(self) -> None:
        # temp-файл здесь — рабочий ВХОД txt2gam (в отличие от builtin, где handle_temp_file пишет
        # debug-дамп). `save_temp_files` = «сохранять ли промежуточные файлы»: удаляем temp, только
        # если не просили хранить и он реально создавался (guard от FileNotFoundError).
        if not self._save_temp_files and os.path.isfile(self._temp_file_path):
            os.remove(self._temp_file_path)

    def save_to_file(self, output_file:Path = '') -> None:
        """ File was been created by  """
        pass
