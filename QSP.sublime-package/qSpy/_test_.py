import time

from converter import QspLoc

if __name__ == "__main__":

    with open('converter\\base_example.qsps', 'r', encoding='utf-8') as fp:
        code = fp.readlines()
    old = time.time()
    loc = QspLoc('start', code)
    loc.split_base()
    print(time.time()-old, ''.join(loc.get_sources()))