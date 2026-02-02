import time
import os

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))

from converter import QspsLoc, QspsToQspBuiltinConv, QspToQsps

def loc_test():
    with open('converter\\base_example.qsps', 'r', encoding='utf-8') as fp:
        code = fp.readlines()
    old = time.time()
    loc = QspsLoc('start', code)
    loc.split_base()
    print(time.time()-old, ''.join(loc.get_sources()))

def qsps_to_qsp_test():
    conv = QspsToQspBuiltinConv('..\\..\\[examples]\\ukuzya.qsp', True)
    conv.convert_file('..\\..\\[examples]\\ukuzya.qsps_',
    '..\\..\\[examples]\\ukuzya.qsp')
    conv.handle_temp_file()

        
def qsp_to_qsps_test():
    import time
    old_time = time.time()

    qsp_to_qsps = QspToQsps()
    qsp_to_qsps.convert_file('..\\..\\[examples]\\examples_qsp_to_qsps\\ukuzya_old.qsp')

    new_time = time.time()
    print(new_time - old_time)
    print(QspToQsps.decode_string(f',0/-\n.2\nh`ip'))

if __name__ == "__main__":
    # qsps_to_qsp_test()
    qsp_to_qsps_test()