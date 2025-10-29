from typing import List, Any

class QspsPP:
    """ Препроцессор для файлов  """
    def __init__(self) -> None:
        # Здесь будут определяться различные параметры,
        # необходимые для работы одной сессии препроцессора.
        ...

    def pp_this_lines(self, qsps_lines: List[str]) -> List[str]:
        """ Preprocess the list of lines. """
        ...