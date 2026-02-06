import time
import os

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))

from converter import (
    QspsLoc,
    QspsToQspBuiltinConv, QspToQspsBuiltinConv,
    FinderSplitter, QspSplitter
)

def loc_test():
    with open('converter\\base_example.qsps', 'r', encoding='utf-8') as fp:
        code = fp.readlines()
    old = time.time()
    loc = QspsLoc('start', code, (2, 2+5))
    loc.split_base()
    print(time.time()-old, ''.join(loc.get_sources()))

def qsps_to_qsp_test():
    conv = QspsToQspBuiltinConv('..\\..\\[examples]\\examples_qsps_to_qsp\\ukuzya_conv.qsp', True)
    conv.convert_file('..\\..\\[examples]\\examples_qsps_to_qsp\\ukuzya_old.qsps',
    '..\\..\\[examples]\\examples_qsps_to_qsp\\ukuzya_conv.qsp')
    conv.handle_temp_file()
        
def qsp_to_qsps_test():
    old_time = time.time()

    qsp_to_qsps = QspToQspsBuiltinConv()
    qsp_to_qsps.convert_file('..\\..\\[examples]\\examples_qsp_to_qsps\\ukuzya_old.qsp')

    new_time = time.time()
    print(new_time - old_time)
    print(QspToQspsBuiltinConv.decode_string(f',0/-\n.2\nh`ip'))

# functions for testing
def qsp_splitter():
	old_time = time.time()

	QspSplitter().split_file('..\\..\\[examples]\\examples_splitter\\driveex.qsp')

	new_time = time.time()
	print(new_time - old_time)

	QspSplitter('txt').split_file('..\\..\\[examples]\\examples_splitter\\basesex.qsps')

	old_time = time.time()
	print(old_time - new_time)

def find_n_split():
	old_time = time.time()

	FinderSplitter(('game',)).search_n_split('..\\..\\[examples]\\examples_finder')

	new_time = time.time()
	print('Find and split files in :', new_time - old_time)

if __name__ == "__main__":
    # qsps_to_qsp_test()
    # qsp_to_qsps_test()
    # find_n_split()
    qsp_splitter()