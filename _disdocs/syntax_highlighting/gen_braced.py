# -*- coding: utf-8 -*-
"""Генератор braced-зеркал (P0, вариант A) для `qsp_base.sublime-syntax`.

Зачем: Sublime не умеет параметризовать `include`, поэтому у каждого контейнера
тела локации существуют ДВА экземпляра — plain (тело локации, `location_body`) и
braced (тело внутри открытого `{…}`, `location_body_braced`). Различие между
двойниками ЧИСТО МЕХАНИЧЕСКОЕ: имена `include`/`push` получают суффикс `_braced`,
единственное исключение — `comments → comments_in_brace` (внутри location_body).

Источник правды — plain-контекст, помеченный комментарием на строке ключа:

    multiline_actions: # @braced: auto

Двойники живут в guarded-регионе файла и руками не правятся:

    # @begin-generated
    …
    # @end-generated

Режимы:
  --check    (по умолчанию) регион совпадает с перегенерацией? иначе exit 1
  --write    перегенерация региона на месте
  --verify   файл НЕ меняется: сравнить, что сгенерировалось бы, с УЖЕ
             существующими двойниками (это доказательство нейтральности при
             переходе на генерацию — делается один раз, до снятия ручных зеркал)

См. `refactoring_review.md` (P0, вариант A) и `HANDOFF.md` §1l.
"""
import re
import sys

KEY_RE = re.compile(r'^  ([A-Za-z_][A-Za-z0-9_]*):([ \t]*#.*)?$')
MARK = '@braced: auto'
BEGIN = '  # @begin-generated'
END = '  # @end-generated'
BEGIN_RE = re.compile(r'^  # @begin-generated\b')
END_RE = re.compile(r'^  # @end-generated\b')

# Подстановки имён в теле двойника: значение `include`/`push` или элемент
# инлайнового push-списка (строка вида «- имя_контекста»).
KV_RE = re.compile(r'^(\s*(?:-\s+)?(?:include|push):\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*)$')
ITEM_RE = re.compile(r'^(\s*-\s+)([A-Za-z_][A-Za-z0-9_]*)(\s*)$')

# Особые случаи: у ЗЕРКАЛА контекста X эти имена заменяются не суффиксом.
SPECIAL = {
    'location_body': {'comments': 'comments_in_brace'},
}


def read_lines(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return fh.read().splitlines()


def write_lines(path, lines):
    # Сохраняем СТИЛЬ переводов строк исходника: рабочая копия под
    # core.autocrlf=true — CRLF, а репозиторий — LF; переписывание всего
    # файла в другой стиль даёт лишний шум в рабочем дереве.
    with open(path, encoding='utf-8', newline='') as fh:
        eol = '\r\n' if '\r\n' in fh.read() else '\n'
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(eol.join(lines) + eol)


def contexts(lines):
    """(name, start, end) для каждого ключа 2-уровня; end — исключающий."""
    keys = []
    started = False
    for i, line in enumerate(lines):
        if not started:
            started = line.startswith('contexts:')
            continue
        m = KEY_RE.match(line)
        if m:
            keys.append((m.group(1), i, bool(m.group(2) and MARK in m.group(2))))
    out = []
    for n, (name, start, marked) in enumerate(keys):
        end = keys[n + 1][1] if n + 1 < len(keys) else len(lines)
        out.append({'name': name, 'start': start, 'end': end, 'marked': marked})
    return out


def trim_tail(lines, start, end):
    """Индекс последней значимой строки чанка (без хвостовых пустых/комментариев)."""
    last = start
    for i in range(start, end):
        s = lines[i].strip()
        if s and not s.startswith('#'):
            last = i
    return last


def twin_rules(lines, start, end):
    """Правила plain-контекста для двойника: без комментариев и пустых строк."""
    out = []
    for i in range(start, end):
        s = lines[i].strip()
        if not s or s.startswith('#'):
            continue
        out.append(lines[i].rstrip())
    return out


def subst(line, plain, marked):
    special = SPECIAL.get(plain, {})

    def twin(name):
        if name in special:
            return special[name]
        return name + '_braced' if name in marked else name

    m = KV_RE.match(line)
    if m:
        return m.group(1) + twin(m.group(2)) + m.group(3)
    m = ITEM_RE.match(line)
    if m:
        return m.group(1) + twin(m.group(2)) + m.group(3)
    return line


def build_region(lines, chunk_list, marked):
    """Текст региона (без крайних переводов строк)."""
    order = [c['name'] for c in chunk_list if c['marked']]
    out = [
        BEGIN,
        '  # # # --- braced-двойники (тело внутри {…}): СГЕНЕРИРОВАНО --- # # #',
        '  # Источник правды — plain-контексты с маркером `# @braced: auto`.',
        '  # Правь plain → `python _disdocs/syntax_highlighting/gen_braced.py',
        '  # --write` → коммить. РУЧНАЯ правка региона запрещена: дрейф валит',
        '  # check_syntax_phase1.py (и побайтную сверку региона, и парность 5.1).',
        '  # Нужны потому, что Sublime не умеет «заглянуть в стек»: признак',
        '  # «открыт ли {…}» кодируется выбором location_body / location_body_braced.',
    ]
    by_name = {c['name']: c for c in chunk_list}
    for plain in order:
        c = by_name[plain]
        out.append('')
        out.append('  %s_braced:' % plain)
        out.append('    # ← сгенерировано из %s' % plain)
        for rule in twin_rules(lines, c['start'] + 1, c['end']):
            out.append(subst(rule, plain, marked))
    out.append('')
    out.append(END)
    return out


def region_bounds(lines):
    b = e = None
    for i, line in enumerate(lines):
        if b is None and BEGIN_RE.match(line):
            b = i
        elif b is not None and END_RE.match(line):
            e = i
            break
    return b, e


def marked_set(chunk_list):
    return {c['name'] for c in chunk_list if c['marked']}


def do_check(path, quiet=False):
    lines = read_lines(path)
    chunk_list = contexts(lines)
    marked = marked_set(chunk_list)
    if not marked:
        print('gen_braced: маркеров `%s` не найдено -> FAIL' % MARK)
        return False
    want = build_region(lines, chunk_list, marked)
    b, e = region_bounds(lines)
    if b is None or e is None:
        print('gen_braced: guarded-регион (@begin/@end-generated) не найден -> FAIL')
        return False
    have = lines[b:e + 1]
    if have == want:
        if not quiet:
            print('gen_braced: регион актуален (%d двойников) -> OK' % len(marked))
        return True
    print('gen_braced: регион РАСХОДИТСЯ с перегенерацией -> FAIL (запусти --write)')
    for n, (h, w) in enumerate(zip(have, want)):
        if h != w:
            print('  строка %d:\n    файл: %r\n    гене: %r' % (b + n + 1, h, w))
            break
    if len(have) != len(want):
        print('  длина региона: файл=%d гене=%d' % (len(have), len(want)))
    return False


def do_write(path):
    lines = read_lines(path)
    chunk_list = contexts(lines)
    marked = marked_set(chunk_list)
    b, e = region_bounds(lines)
    if b is None or e is None:
        print('gen_braced: guarded-регион не найден -> ничего не сделано')
        return False
    want = build_region(lines, chunk_list, marked)
    write_lines(path, lines[:b] + want + lines[e + 1:])
    print('gen_braced: регион перезаписан (%d двойников)' % len(marked))
    return True


def do_verify(path):
    """Сгенерированные двойники == существующие ручные двойники (proof)."""
    lines = read_lines(path)
    chunk_list = contexts(lines)
    by_name = {c['name']: c for c in chunk_list}
    marked = marked_set(chunk_list)
    ok = True
    checked = 0
    for plain in [c['name'] for c in chunk_list if c['marked']]:
        twin = plain + '_braced'
        if twin not in by_name:
            print('  %-32s ДВОЙНИК ОТСУТСТВУЕТ' % plain)
            ok = False
            continue
        c = by_name[plain]
        gen = [subst(r, plain, marked).strip()
               for r in twin_rules(lines, c['start'] + 1, c['end'])]
        tc = by_name[twin]
        cur = [r.strip() for r in twin_rules(lines, tc['start'] + 1, tc['end'])]
        checked += 1
        if gen == cur:
            print('  %-32s IDENTICAL (%d правил)' % (twin, len(gen)))
            continue
        ok = False
        print('  %-32s РАСХОЖДЕНИЕ (гене=%d, файл=%d)' % (twin, len(gen), len(cur)))
        for n in range(max(len(gen), len(cur))):
            g = gen[n] if n < len(gen) else '<нет>'
            f = cur[n] if n < len(cur) else '<нет>'
            if g != f:
                print('     #%d гене: %s\n         файл: %s' % (n, g, f))
                break
    print('gen_braced: проверено %d пар -> %s'
          % (checked, 'IDENTICAL' if ok else 'РАСХОЖДЕНИЯ'))
    return ok


def main(argv):
    root = None
    if '--root' in argv:
        root = argv[argv.index('--root') + 1]
    import os
    if root is None:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    path = os.path.join(root, 'QSP.sublime-package', 'qsp_base.sublime-syntax')
    mode = 'verify' if '--verify' in argv else \
        'write' if '--write' in argv else 'check'
    if mode == 'verify':
        return 0 if do_verify(path) else 1
    if mode == 'write':
        return 0 if do_write(path) else 1
    return 0 if do_check(path) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
