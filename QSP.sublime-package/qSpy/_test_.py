import time
import os

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))

from converter import QspLoc, QspsToQspConverter

def loc_test():
    with open('converter\\base_example.qsps', 'r', encoding='utf-8') as fp:
        code = fp.readlines()
    old = time.time()
    loc = QspLoc('start', code)
    loc.split_base()
    print(time.time()-old, ''.join(loc.get_sources()))

def qsps_to_qsp_test():
    conv = QspsToQspConverter('', '')
    conv.convert_file('..\\..\\[examples]\\ukuzya.qsps_',
    '..\\..\\[examples]\\ukuzya.qsp')
    conv.save_temp_file('..\\..\\[examples]\\ukuzya.txt')

if __name__ == "__main__":
    qsps_to_qsp_test()
    