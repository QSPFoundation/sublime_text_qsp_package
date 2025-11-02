from typing import List, Any

from pp_scanner import PpScanner
from pp_tokens import PpToken
from pp_tokens import PpTokenType as tt

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self) -> None:
        # Здесь будут определяться различные параметры,
        # необходимые для работы одной сессии препроцессора.
        ...

    def pp_this_lines(self, qsps_lines: List[str]) -> List[str]:
        """ Preprocess the list of lines. """
        scanner = PpScanner(qsps_lines)
        scanner.scan_tokens()

        tokens = scanner.get_tokens()