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

import sys, os, io, argparse, contextlib, difflib, hashlib, glob, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
EX   = os.path.dirname(HERE)                                  # _examples
ROOT = os.path.dirname(EX)                                    # JAD
PKG  = os.path.join(ROOT, 'QSP.sublime-package')
GOLD = os.path.join(HERE, '_golden')
os.makedirs(GOLD, exist_ok=True)
sys.path.insert(0, PKG)

from qSpy.converter.qsp_to_qsps import QspToQspsBuiltinConv, ValidationFormatError
from qSpy.converter.converters import QspsToQspBuiltinConv
from qSpy.converter.qsps_file import QspsFile
from qSpy.converter.qsp_location import QspsLoc
from qSpy.converter.tools import QSP_CODREMOV
from qSpy.converter.qsp_splitter import QspSplitter

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
        c.to_qsps()                 # накапливает в c._qsps_lines (наружу ничего не возвращает)
        lines = c._qsps_lines
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

    # B1/Q1: guard «подозрительного закрытия» — диагностика, разбор не меняет
    # эталонный маркер `-- name ---...` -> шумов нет
    logc = io.StringIO()
    with contextlib.redirect_stdout(logc):
        q = QspsFile(); q.set_src_lines(['# l\n', 'code\n', '-- l ' + '-' * 33 + '\n'])
        q.split_to_locations()
    if logc.getvalue().strip():
        fails.append(f'B1 ложный guard на валидном маркере: {logc.getvalue()!r}')
    if len(q.get_locations()) != 1:
        fails.append(f'B1 валидный маркер: локаций {len(q.get_locations())} != 1')
    # случайный `--`-комментарий в колонке 0 -> предупреждение + локация всё равно закрыта
    logs = io.StringIO()
    with contextlib.redirect_stdout(logs):
        q2 = QspsFile(); q2.set_src_lines(['# l\n', 'code\n', '-- просто комментарий\n'])
        q2.split_to_locations()
    if 'одозрительное' not in logs.getvalue() or '"l"' not in logs.getvalue():
        fails.append(f'B1 нет предупреждения на подозрительном закрытии: {logs.getvalue()!r}')
    if len(q2.get_locations()) != 1:
        fails.append(f'B1 разбор изменился: локаций {len(q2.get_locations())} != 1')

    # ---- пины base-подсистемы (Фаза 3: B5/B6/B7) ----
    # B5: вложенные `{...}` парсятся структурно (без поедания внешнего `}`)
    with contextlib.redirect_stdout(io.StringIO()):
        l5 = QspsLoc('L5', ['! BASE\n', '*P {a{b}c}\n', '! END BASE\n'], None)
        l5.split_base()
    j5 = ' | '.join(l5.base_errors())
    if 'EOF in braces' in j5:
        fails.append(f'B5 вложенные braces не допарсены: {j5!r}')
    if 'Use simple string' not in j5:
        fails.append(f'B5 brace не дошёл до int-проверки: {j5!r}')

    # B6: `loop ... while ... step ... then` в BASE — pop соблюдён, цикл не виснет/не падает
    with contextlib.redirect_stdout(io.StringIO()):
        l6 = QspsLoc('L6', ['! BASE\n', 'loop while (i < 5) step i += 1 then\n',
                            "    msg 'x'\n", 'END\n', '! END BASE\n'], None)
        l6.split_base()
    if not any('Do not use cycles' in e for e in l6.base_errors()):
        fails.append(f'B6 loop не распознан как Loop (pop не соблюдён): {l6.base_errors()!r}')

    # B7: единый канал — ошибка с именем локации, desc сохранён, сборка не падает
    with contextlib.redirect_stdout(io.StringIO()):
        l7 = QspsLoc('myloc', ['! BASE\n', "*P 'desc'\n", 'if x: y\n', 'END\n', '! END BASE\n'], None)
        l7.split_base()
    e7 = l7.base_errors()
    if not e7 or not all('myloc' in e for e in e7):
        fails.append(f'B7 нет имени локации в ошибках: {e7!r}')
    if l7.desc().strip() != 'desc':
        fails.append(f'B7 desc потерян при ошибке другого оператора: {l7.desc()!r}')
    # B7: ParserError из парсера ловится каналом (не роняет split_base наружу).
    # незакрытый блочный `if` (без END) — balanced по кавычкам/скобкам, поэтому BASE
    # извлекается штатно, а парсер кидает ParserError на EOF блока.
    with contextlib.redirect_stdout(io.StringIO()):
        l7b = QspsLoc('Lb', ['! BASE\n', "*P 'd'\n", 'if x:\n', '    y\n', '! END BASE\n'], None)
        l7b.split_base()   # не должно бросить исключение наружу
    if not any('EOF in multiline block' in e for e in l7b.base_errors()):
        fails.append(f'B7 ParserError не пойман каналом: {l7b.base_errors()!r}')

    # ---- пины B11 (Фаза 4, п.4.3): split_qsp — типизированная ошибка на битом входе ----
    def _enc(s):  # plain -> «±5», как хранится в .qsp (обратная к DECODE_TABLE)
        return ''.join(chr(ord(ch) - QSP_CODREMOV) for ch in s)

    # слишком короткий файл (<4 строк) -> ValidationFormatError
    c1 = QspToQspsBuiltinConv()
    c1._game_lines = ['QSPGAME\n', 'l2\n', 'pw\n']
    c1._input_file = 'short.qsp'
    try:
        c1.split_qsp()
        fails.append('B11 короткий файл: нет ValidationFormatError')
    except ValidationFormatError:
        pass

    # заголовок не QSPGAME -> ValidationFormatError
    c2 = QspToQspsBuiltinConv()
    c2._game_lines = ['OLDHDR\n', 'l2\n', 'pw\n', 'x\n']
    c2._input_file = 'old.qsp'
    try:
        c2.split_qsp()
        fails.append('B11 неверный заголовок: нет ValidationFormatError')
    except ValidationFormatError:
        pass

    # обрезанный файл (заявлено 2 локации, данных не хватает) -> ValidationFormatError
    c3 = QspToQspsBuiltinConv()
    c3._game_lines = ['QSPGAME\n', 'l2\n', _enc('pw') + '\n', _enc('2') + '\n', _enc('LocA') + '\n']
    c3._input_file = 'trunc.qsp'
    try:
        c3.split_qsp()
        fails.append('B11 обрезанный файл: нет ValidationFormatError')
    except ValidationFormatError:
        pass

    # нечисловое поле числа локаций -> ValidationFormatError
    c5 = QspToQspsBuiltinConv()
    c5._game_lines = ['QSPGAME\n', 'l2\n', _enc('pw') + '\n', _enc('abc') + '\n']
    c5._input_file = 'badint.qsp'
    try:
        c5.split_qsp()
        fails.append('B11 нечисловое число локаций: нет ValidationFormatError')
    except ValidationFormatError:
        pass

    # расхождение числа локаций (заявлено 1, распознано 0) -> только warning, без raise
    c4 = QspToQspsBuiltinConv()
    c4._game_lines = ['QSPGAME\n', 'l2\n', _enc('pw') + '\n', _enc('1') + '\n']
    c4._input_file = 'mismatch.qsp'
    logw = io.StringIO()
    with contextlib.redirect_stdout(logw):
        c4.split_qsp()  # не должно бросить
    if 'локаций' not in logw.getvalue():
        fails.append(f'B11 нет warning о расхождении числа локаций: {logw.getvalue()!r}')
    if len(c4.get_locations()) != 0:
        fails.append(f'B11 mismatch: разбор изменился {len(c4.get_locations())} != 0')

    # B11-остаток (п.4.4): неверный заголовок в первой кодировке -> continue, а не обрыв подбора.
    # UTF-8 с BOM: utf-16-le декодирует байты без исключения (чётная длина, нет суррогатов),
    # но заголовок — mojibake. Старый код кинул бы ValidationFormatError и оборвал перебор;
    # новый обязан пропустить utf-16-le и дойти до utf-8-sig.
    bom_probe = os.path.join(GOLD, '_bom_enc_probe.qsp')
    payload = 'QSPGAME\n2026-01-01 (pin)\nIj\n+\nX'  # utf8=31 (+BOM 3 = 34 → чётно для utf-16-le)
    with open(bom_probe, 'wb') as f:
        f.write(payload.encode('utf-8-sig'))
    cb = QspToQspsBuiltinConv()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cb.read_from_file(bom_probe)
        if cb._encoding != 'utf-8-sig':
            fails.append(f'B11-остаток: подбор кодировок не дошёл до utf-8-sig (enc={cb._encoding!r})')
    except ValidationFormatError as e:
        fails.append(f'B11-остаток: неверный заголовок оборвал подбор кодировок ({e})')
    finally:
        if os.path.isfile(bom_probe):
            os.remove(bom_probe)

    # ---- пин эталонного корпуса реальных .qsp (п.4.4 / Q6): читатель+сплит проходят все ----
    # 12 живых файлов QGen/txt2gam/cp1251 (utf-16le без BOM, CRLF + легаси cp1251): ни один не
    # должен бросить; кодировка — из ожидаемого набора; локаций >= 1.
    corpus = os.path.join(ROOT, '_disdocs', '_valid qgen qsp')
    qsp_files = sorted(glob.glob(os.path.join(corpus, '*.qsp')))
    if len(qsp_files) < 2:
        fails.append(f'B12-корпус: мало эталонных .qsp ({len(qsp_files)}) в {corpus}')
    for qf in qsp_files:
        cq = QspToQspsBuiltinConv()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                cq.read_from_file(qf)
                cq.split_qsp()
        except Exception as e:
            fails.append(f'B12-корпус: {os.path.basename(qf)} → {type(e).__name__}: {e}')
            continue
        if cq._encoding not in ('utf-16-le', 'cp1251'):
            fails.append(f'B12-корпус: {os.path.basename(qf)} — неожиданная кодировка {cq._encoding!r}')
        if len(cq.get_locations()) < 1:
            fails.append(f'B12-корпус: {os.path.basename(qf)} — распознано 0 локаций')

    # ---- пин B13-дедуп (Фаза 5, п.5.2): защита от перезаписи при повторном сплите ----
    # _write_location берёт ПЕРВЫЙ СВОБОДНЫЙ путь по итоговому имени; старт дедупа —
    # с высокой точки count (не с нуля). Контракт: никогда не затирать существующий файл.
    dedup_dir = tempfile.mkdtemp(prefix='_dedup_pin_')
    try:
        sp = QspSplitter('txt')
        sp._output_folder = dedup_dir
        sp._qproj_data = {}
        cnt1 = {}                                        # прогон 1: два дубля одного имени
        sp._write_location('dup', ['A\n'], cnt1)         # -> dup.qsps
        sp._write_location('dup', ['B\n'], cnt1)         # -> dup_1.qsps
        dup1_run1 = None
        p1 = os.path.join(dedup_dir, 'dup_1.qsps')
        if os.path.isfile(p1):
            with open(p1, encoding='utf-8') as fh:
                dup1_run1 = fh.read()
        cnt2 = {}                                        # прогон 2: свежий count, файлы на диске
        sp._write_location('dup', ['C\n'], cnt2)         # -> dup_2.qsps (не поверх dup_1!)
        sp._write_location('dup', ['D\n'], cnt2)         # -> dup_3.qsps
        got = sorted(os.listdir(dedup_dir))
        if got != ['dup.qsps', 'dup_1.qsps', 'dup_2.qsps', 'dup_3.qsps']:
            fails.append(f'B13-дедуп: дерево {got} != dup,dup_1,dup_2,dup_3')
        # старый баг: повторный прогон затирал dup_1.qsps -> проверяем неизменность
        if dup1_run1 is not None:
            with open(p1, encoding='utf-8') as fh:
                if fh.read() != dup1_run1:
                    fails.append('B13-дедуп: dup_1.qsps перезаписан повторным прогоном (баг!)')
        else:
            fails.append('B13-дедуп: dup_1.qsps не создан в прогоне 1')
    finally:
        shutil.rmtree(dedup_dir, ignore_errors=True)

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
        print('ok    пины B1/B2/B3/B4/B5/B6/B7/B11/B12-корпус/B13-дедуп')

    if args.info:
        info_vs_txt2gam(a_text, b_text)

    print('\nITOG:', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
