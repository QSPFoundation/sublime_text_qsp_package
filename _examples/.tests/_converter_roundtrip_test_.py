# _converter_roundtrip_test_.py
#
# Золотой roundtrip-тест конвейера qSpy/converter (Фаза 0 плана `_disdocs/converter/plan.md`).
# Работает без Sublime: `python _converter_roundtrip_test_.py`.
#
# Что покрывает (plan.md §5):
#   §5.1 Roundtrip-золото на ukuzya в обе стороны:
#        A) qsp -> qsps : `_examples/examples_qsp_to_qsps/ukuzya_old.qsp`
#        B) qsps -> qsp : `_examples/examples_qsps_to_qsp/ukuzya_old.qsps`
#      Выходы сравниваются побайтово с зафиксированными снимками в `_golden/`
#      (регрессия: любое изменение конвертации, кроме намеренного, — FAIL).
#   §5.3 Ошибка-канал и инварианты фиксов B2/B3/B4 (пин-тесты на крошечных фикстурах,
#      не зависящие от base-подсистемы, чтобы не тянуть шум B5–B8).
#   §5.1b Отчёт против золота txt2gam (`--info`): известная разница = EOL + content known-fail.
#   §5.2 (токен-дампы base) — компания Фазы 3 (B5–B8), сюда не входит.
#
# Режимы:
#   (без флагов)            — проверить снимки + пин-тесты; коды возврата 0/1.
#   --update                — перегенерировать снимки в `_golden/` (осознанное принятие baseline).
#   --info                  — дополнительно напечатать сверку с txt2gam (информативно, не влияет на код выхода).

import sys, os, io, argparse, contextlib, difflib, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
EX   = os.path.dirname(HERE)                                  # _examples
ROOT = os.path.dirname(EX)                                    # JAD
PKG  = os.path.join(ROOT, 'QSP.sublime-package')
GOLD = os.path.join(HERE, '_golden')
os.makedirs(GOLD, exist_ok=True)
sys.path.insert(0, PKG)

from qSpy.converter.qsp_to_qsps import QspToQspsBuiltinConv
from qSpy.converter.converters import QspsToQspBuiltinConv
from qSpy.converter.qsps_file import QspsFile
from qSpy.converter.qsp_location import QspsLoc

A_IN  = os.path.join(EX, 'examples_qsp_to_qsps', 'ukuzya_old.qsp')
A_REF = os.path.join(EX, 'examples_qsp_to_qsps', 'ukuzya_txt2gam.qsps')
B_IN  = os.path.join(EX, 'examples_qsps_to_qsp', 'ukuzya_old.qsps')
B_REF = os.path.join(EX, 'examples_qsps_to_qsp', 'ukuzya_txt2gam.qsp')


def _read_lines(path, enc):
    with open(path, encoding=enc, newline='') as f:
        return list(f)


def conv_A():
    """ qsp -> qsps: вернуть (текст_результата, перехваченный_вывод_консоли). """
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        c = QspToQspsBuiltinConv()
        c.read_from_file(A_IN)
        c.split_qsp()
        lines = c.to_qsps()
    return ''.join(lines), log.getvalue()


def conv_B():
    """ qsps -> qsp: вернуть (текст_результата, перехваченный_вывод_консоли). """
    lines_in = _read_lines(B_IN, 'utf-8-sig')
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        b = QspsToQspBuiltinConv(output_file=os.path.join(GOLD, '_tmp'), save_temp_files=False)
        game = b.convert_lines(lines_in)
    return ''.join(game), log.getvalue()


def _norm_console(t):
    """ Диагностика печатается из 32 потоков -> порядок недетерминирован.
    Канонизируем консоль (сортировка + дедуп строк), чтобы снимок был воспроизводим."""
    return ''.join(x + '\n' for x in sorted(set(t.splitlines())))


def snapshot(name, text):
    p = os.path.join(GOLD, name)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def load_snapshot(name):
    p = os.path.join(GOLD, name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def _diff_report(actual, expected):
    a = actual.splitlines()
    e = expected.splitlines()
    return list(difflib.unified_diff(e, a, 'golden', 'actual', lineterm='', n=1))[:40]


# ---------------- пин-тесты инвариантов фиксов B2/B3/B4 ----------------
def pins():
    fails = []
    # B2: хвостовые пробельные символы срезаются из имени локации
    for raw, want in [('# loc \n', 'loc'), ('# loc\r\n', 'loc'),
                      ('# loc\x0c\n', 'loc'), ('# loc\x0b\n', 'loc'), ('#  loc  \n', 'loc')]:
        q = QspsFile(); q.set_src_lines([raw, '-- x ' + '-' * 33 + '\n']); q.split_to_locations()
        got = q.get_locations()[0].name()
        if got != want:
            fails.append(f'B2 {raw!r}: name={got!r} != {want!r}')

    # B3: незакрытый `! BASE` -> весь код в run_on_visit (без дублей) + сообщение в консоль
    code = ['open\n', '! BASE\n', "* p 'd'\n", "'a'\n"]
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        loc = QspsLoc('myloc', list(code), None)
    if loc.run_on_visit() != code:
        fails.append(f'B3 run_on_visit={loc.run_on_visit()!r} != весь код {code!r}')
    if 'BASE' not in log.getvalue() or 'myloc' not in log.getvalue():
        fails.append(f'B3 нет сообщения с именем локации: {log.getvalue()!r}')
    # B3: закрытый BASE — без сообщения, base извлечён, дублей нет
    log2 = io.StringIO()
    with contextlib.redirect_stdout(log2):
        QspsLoc('m', ['pre\n', '! BASE\n', "* p 'd'\n", '! END BASE\n', 'post\n'], None)
    if log2.getvalue().strip():
        fails.append(f'B3 ложное сообщение на валидном BASE: {log2.getvalue()!r}')

    # B4: пустой run_on_visit — без падения, маркер terminated
    src = ['! BASE\n', "* p 'x'\n", '! END BASE\n']  # base закрыт, run_on_visit пуст
    out = QspsLoc('L', src, None).get_sources()
    if not (out[-1].startswith('-- L ') and out[-1].endswith('\n')):
        fails.append(f'B4 пустой run_on_visit: хвост={out[-1]!r}')
    # B4: последняя строка кода без \n -> добавлен терминатор, нет склейки 'код-- '
    out2 = QspsLoc('L', ['a\n', 'b'], None).get_sources()
    j2 = ''.join(out2)
    if j2.count('-- L ') != 1 or '\nb\n-- L ' not in j2:
        fails.append(f'B4 без-\\n: склейка нарушена: {j2!r}')

    return fails


# ---------------- отчёт против золота txt2gam (информативно) ----------------
def split_locs_text(lines):
    locs, name, body = {}, None, []
    for ln in lines:
        s = ln.rstrip('\r\n')
        if s.startswith('# '):
            if name is not None:
                locs.setdefault(name, body)
            name, body = s[2:].rstrip(), []
        elif s.startswith('-- ') and name is not None:
            locs.setdefault(name, body); name, body = None, []
        elif name is not None:
            body.append(ln.replace('\r\n', '\n'))
    if name is not None:
        locs.setdefault(name, body)
    return locs


def info_vs_txt2gam(a_text, b_text):
    print('--- INFO: сверка с золотом txt2gam (known-fail, не влияет на код выхода) ---')
    # B: сверка мультисетом нормализованных строк (порядок/выравнивание строк не важны:
    # реальные различия продукта B12/Q7 ломают позиционную сверку, но не содержимое)
    from collections import Counter
    ob = [l.rstrip('\r\n') for l in io.StringIO(b_text, newline='')]
    rb = [l.rstrip('\r\n') for l in _read_lines(B_REF, 'utf-16le')]
    co, cr = Counter(ob), Counter(rb)
    only_o = sum((co - cr).values()); only_r = sum((cr - co).values()); common = sum((co & cr).values())
    print(f'  B (qsps->qsp): строк ours={len(ob)} ref={len(rb)} | совпало {common} | только ours {only_o} | только ref {only_r} (known-fail: EOL/отступы B12/Q7)')
    # A: содержимое локаций (текстовый сплит, без base-подсистемы)
    la = split_locs_text(a_text.splitlines(keepends=True))
    with open(A_REF, encoding='utf-8', newline='') as f:
        lr = split_locs_text(list(_iter_lines(f)))
    extra, missing = set(la) - set(lr), set(lr) - set(la)
    diff = [k for k in la if k in lr and la[k] != lr[k]]
    print(f'  A (qsp->qsps): локаций ours={len(la)} ref={len(lr)} | extra={sorted(extra)} missing={sorted(missing)} | content-diff(после-EOL)={diff} (known-fail: crutch Q7)')


def _iter_lines(f):
    for ln in f:
        yield ln


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('--update', action='store_true', help='перегенерировать снимки baseline')
    ap.add_argument('--info', action='store_true', help='сверка с золотом txt2gam')
    args = ap.parse_args()

    a_text, a_log = conv_A()
    b_text, b_log = conv_B()

    ok = True
    snaps = {'A_ukuzya.qsps.txt': a_text, 'A_console.txt': _norm_console(a_log),
             'B_ukuzya.qsp.txt': b_text, 'B_console.txt': _norm_console(b_log)}
    if args.update:
        for n, t in snaps.items():
            snapshot(n, t)
        print(f'[update] зафиксировано снимков: {len(snaps)} в {GOLD}')
    else:
        for n, t in snaps.items():
            exp = load_snapshot(n)
            if exp is None:
                print(f'FAIL  снимок {n} отсутствует — запусти --update'); ok = False; continue
            if exp != t:
                print(f'FAIL  регрессия конвертации в {n}:'); ok = False
                for d in _diff_report(t, exp):
                    print('   ', d)
            else:
                print(f'ok    {n}  sha={hashlib.sha256(t.encode()).hexdigest()[:12]}')

    pf = pins()
    for m in pf:
        print('FAIL  pin:', m)
    ok = ok and not pf
    if not pf:
        print('ok    пины B2/B3/B4')

    if args.info:
        info_vs_txt2gam(a_text, b_text)

    print('\nITOG:', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
