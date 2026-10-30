# -*- coding: utf-8 -*-
r"""P1.7 — нормализация `\s*?` → `\s*` в `qsp_base.sublime-syntax`.

Зачем вообще: `\s*?` и `\s*` дают ОДИН И ТОТ ЖЕ матч только там, где сразу за
квантором стоит ОБЯЗАТЕЛЬНЫЙ атом, не совпадающий с пробелом: тогда позиция
остановки единственна и greedy/lazy сходятся к ней. Во всех остальных местах
замена МЕНЯЕТ подсветку:

  * квантор в КОНЦЕ regex (`arm_anchor`) — ленивый матчит НОЛЬ символов, greedy
    съест отступ и утащит в scope начало строки;
  * квантор ПЕРЕД `\K` (`left_ctx_anchor`, inline-якорь в `operacion`) — greedy
    сдвинет НАЧАЛО матча на первый непробельный символ;
  * квантор ПЕРЕД `.*`/`.*?`/опциональной группой/`$`/`{{nr…}}` — `\s` включает
    перевод строки, поэтому greedy дотянется до следующей строки и матч СТАНЕТ
    успешным там, где ленивый его не находил (это ровно класс бага `kw_elseif`,
    HANDOFF §1i).

Скрипт сам классифицирует каждое вхождение (см. `verdict`) и печатает отчёт.
`--write` меняет ТОЛЬКО безопасные вхождения; guarded-регион `@begin-generated`
не трогается никогда — его перегенерирует `gen_braced.py --write` из plain.

Режимы:
  (без ключей)  отчёт: вхождения + вердикты + доказательство эквивалентности
  --write       применить правку безопасных вхождений + доказательство
  --prove       только доказательство (файл не меняется)
  --against-head  доказательство против версии из `git show HEAD:` (себя включает
                  регенерированные braced-двойники) + проверка, что диф = ТОЛЬКО
                  `\s*?` → `\s*` — запускать ПОСЛЕ gen_braced

Доказательство 1:1: обе версии файла раскручиваются по `{{var}}`, затем каждый
ИЗМЕНЁННЫЙ `match` прогоняется по корпусу (`_examples/**/*.qsps|qsrc|qsp` +
фикстуры пакета) — сравниваются позиции ВСЕХ совпадений. Regex, которые
Python `re` не компилирует (`\K`, `\p{L}`), пропускаются с пометкой.

См. `refactoring_review.md` (P1.7) и `HANDOFF.md` §3.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if '--root' in sys.argv:
    ROOT = sys.argv[sys.argv.index('--root') + 1]
BASE_DIR = os.path.join(ROOT, 'QSP.sublime-package') + '/'
PATH = BASE_DIR + 'qsp_base.sublime-syntax'

LAZY = '\\s*?'
BEGIN_RE = re.compile(r'^\s*#\s*@begin-generated\b')
END_RE = re.compile(r'^\s*#\s*@end-generated\b')
LABEL_RE = re.compile(r'^  ([A-Za-z_]\w*):')
MATCH_RE = re.compile(r'^(\s*(?:-\s+)?(?:match|replace):\s*)(.*?)(\s*)$')
VAR_RE = re.compile(r'^(\s{2}[A-Za-z_]\w*:\s*)(.*?)(\s*)$')
TPL_RE = re.compile(r'\{\{(\w+)\}\}')

# ---------------------------------------------------------------- вердикты ---
# Каждое безопасное вхождение получает один вердикт; причина — в KEEP/SAFE.
SAFE = ('SAFE', 'обязательный атом, не совпадающий с пробелом')
KEEP_K = ('KEEP', 'перед \\K — greedy сдвинет НАЧАЛО матча')
KEEP_END = ('KEEP', 'конец regex — ленивый матчит НОЛЬ символов')
KEEP_DOT = ('KEEP', 'перед . / .* — \\s съест перевод строки')
KEEP_EOL = ('KEEP', 'перед $ / {{nr…}} — \\s съест перевод строки')
KEEP_WS = ('KEEP', 'перед \\s — кванторы сольются')
KEEP_OPT = ('KEEP', 'дальше опциональный атом — greedy съест пробел')
KEEP_UNC = ('KEEP', 'не разобрано структурно — решать вручную')


def strip_comment(val):
    """Срезать YAML-комментарий ` # …` (вне кавычек) и пробелы по краям."""
    quote = None
    for i, c in enumerate(val):
        if quote:
            if c == quote:
                quote = None
        elif c in '\'"':
            quote = c
        elif c == '#' and i and val[i - 1] in ' \t':
            return val[:i].rstrip()
    return val.rstrip()


def strip_quotes(val):
    if len(val) >= 2 and val[0] in '\'"' and val[-1] == val[0]:
        return val[1:-1]
    return val


def expand(s, variables, depth=0):
    """Раскрутка {{var}} (рекурсивно, до 6 уровней)."""
    if depth > 6 or '{{' not in s:
        return s

    def sub(m):
        val = variables.get(m.group(1))
        return m.group(0) if val is None else expand(val, variables, depth + 1)

    return TPL_RE.sub(sub, s)


def match_paren(s, i):
    """Индекс ')' парного к '(' в позиции i (учитывает классы и экранирование)."""
    depth, in_class = 0, False
    j = i
    while j < len(s):
        c = s[j]
        if c == '\\':
            j += 2
            continue
        if in_class:
            if c == ']':
                in_class = False
        elif c == '[':
            in_class = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def atom_verdict(s, i, variables):
    """Вердикт для атома, начинающегося в позиции i (общая логика рекурсии)."""
    if i >= len(s):
        return KEEP_END
    c = s[i]
    if c in ')}|':
        return KEEP_UNC
    if c == '.':
        return KEEP_DOT
    if c == '$':
        return KEEP_EOL
    if s.startswith('\\s', i):
        return KEEP_WS
    if s.startswith('{{', i):
        exp = expand(s[i:], variables)
        if exp == s[i:]:
            return KEEP_UNC
        return atom_verdict(exp, 0, variables)
    if c == '(':
        j = match_paren(s, i)
        if j < 0:
            return KEEP_UNC
        nxt = s[j + 1:j + 2]
        if nxt in ('?', '*'):
            return KEEP_OPT
        if nxt == '+':
            # (…)+ — атом обязателен, но повторы не влияют на остановку
            return atom_verdict(s, i + 1, variables)
        body = s[i + 1:j]
        # групповые префиксы: ?, ?i:, ?<name>, ?=, ?! …
        if body.startswith('?'):
            m = re.match(r'\?[imsx\-\w]*:', body)
            if not m:
                return KEEP_UNC
            body = body[m.end():]
        if body[:1] in ('|', ')', '') or body.startswith('?'):
            return KEEP_UNC
        return atom_verdict(body, 0, variables)
    return SAFE


def verdict(rest, variables):
    """Вердикт для квантора: rest — текст ПОСЛЕ `\\s*?` до конца regex."""
    if '\\K' in rest:
        return KEEP_K
    i = 0
    while i < len(rest):
        c = rest[i]
        if c == ')':
            i += 1  # закрылась СВОЯ группа — смотрим дальше по внешней части
            continue
        if c == '|':
            # наша ветка кончилась: пропускаем остальные ветки внешней группы
            depth, i = 0, i + 1
            while i < len(rest):
                ch = rest[i]
                if ch == '\\':
                    i += 2
                    continue
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth == 0:
                        i += 1
                        break
                    depth -= 1
                i += 1
            continue
        return atom_verdict(rest, i, variables)
    return KEEP_END


# --------------------------------------------------------------- инвентарь ---
def read_text(path):
    with io.open(path, encoding='utf-8', newline='') as fh:
        return fh.read()


def read_corpus(path):
    """Корпус бывает в старой кодировке — читаем терпимо (важна геометрия)."""
    with io.open(path, encoding='utf-8', newline='', errors='replace') as fh:
        return fh.read()


def collect(text, variables):
    """Список вхождений: (line_no, col, label, yaml_span, verdict)."""
    lines = text.splitlines()
    out = []
    label = '?'
    in_gen = False
    for n, line in enumerate(lines, 1):
        if BEGIN_RE.match(line):
            in_gen = True
            continue
        if END_RE.match(line):
            in_gen = False
            continue
        m = LABEL_RE.match(line)
        if m and not line.lstrip().startswith('-'):
            label = m.group(1)
        if line.lstrip().startswith('#'):
            continue  # комментарии/доки не правим (в них \s*? — проза)
        m = MATCH_RE.match(line) or VAR_RE.match(line)
        if not m:
            continue
        raw = strip_comment(m.group(2))
        if not raw:
            continue
        val = strip_quotes(raw)
        start = len(m.group(1)) + m.group(2).find(raw)
        if val is not raw:  # YAML-кавычки сняты — сдвиг на один символ
            start += 1
        for occ in re.finditer(re.escape(LAZY), val):
            v = verdict(val[occ.end():], variables)
            out.append({'line': n, 'col': start + occ.start(), 'label': label,
                        'gen': in_gen, 'verdict': v,
                        'ctx': val[max(0, occ.start() - 24):occ.end() + 24]})
    return lines, out


def new_text(text, sites):
    """Текст с заменой безопасных вхождений (от конца к началу)."""
    lines = text.splitlines(True)
    hit = {}
    for s in sites:
        if s['verdict'][0] == 'SAFE' and not s['gen']:
            hit.setdefault(s['line'], []).append(s['col'])
    for n, cols in hit.items():
        line = lines[n - 1]
        for col in sorted(cols, reverse=True):
            assert line[col:col + len(LAZY)] == LAZY, (n, col)
            line = line[:col] + '\\s*' + line[col + len(LAZY):]
        lines[n - 1] = line
    return ''.join(lines)


# ------------------------------------------------ доказательство 1:1 (P1.7) ---
def yaml_doc(text):
    import yaml
    return yaml.safe_load(text.replace('%YAML 1.2', ''))


def rules_of(doc):
    """{id: (label, regex)} для всех match/replace всех контекстов."""
    res = {}
    for ctx, body in (doc.get('contexts') or {}).items():
        if not isinstance(body, list):
            continue
        for i, rule in enumerate(body):
            if not isinstance(rule, dict):
                continue
            for key in ('match', 'replace'):
                if key in rule:
                    res['%s#%d:%s' % (ctx, i, key)] = (ctx, rule[key])
    return res


def corpus():
    files = sorted(glob.glob(os.path.join(ROOT, '_examples', '**', '*.qsps'),
                             recursive=True))
    files += sorted(glob.glob(os.path.join(ROOT, '_examples', '**', '*.qsrc'),
                              recursive=True))
    files += sorted(glob.glob(os.path.join(ROOT, '_examples', '**', '*.qsp'),
                              recursive=True))
    files += [BASE_DIR + f for f in os.listdir(BASE_DIR) if f.endswith('.qsps')]
    texts = []
    for path in files:
        try:
            texts.append(read_corpus(path))
        except (IOError, OSError):
            pass
    return texts


def prove(old_text, new_text_, old_vars, new_vars, verbose=True):
    """Сравнить поведение ИЗМЕНЁННЫХ regex на корпусе. True = 1:1."""
    old_doc, new_doc = yaml_doc(old_text), yaml_doc(new_text_)
    old_rules, new_rules = rules_of(old_doc), rules_of(new_doc)
    samples = corpus()
    changed, proven, skipped, failed = 0, 0, [], []
    for rid in sorted(set(old_rules) & set(new_rules)):
        o = expand(old_rules[rid][1], old_vars)
        n = expand(new_rules[rid][1], new_vars)
        if o == n:
            continue
        changed += 1
        try:
            po, pn = re.compile(o, re.M), re.compile(n, re.M)
        except re.error as exc:
            skipped.append((rid, str(exc)))
            continue
        bad = None
        for txt in samples:
            a = [(m.start(), m.end(), m.group(0)) for m in po.finditer(txt)]
            b = [(m.start(), m.end(), m.group(0)) for m in pn.finditer(txt)]
            if a != b:
                bad = (a[:1], b[:1], len(a), len(b))
                break
        if bad:
            failed.append((rid, bad))
        else:
            proven += 1
    print('proof: изменённых regex %d | эквивалентны на корпусе %d | '
          'пропущено (re не компилирует) %d | расхождений %d'
          % (changed, proven, len(skipped), len(failed)))
    print('       корпус: %d файлов' % len(samples))
    if verbose:
        for rid, why in skipped:
            print('       skip %s: %s' % (rid, why))
    for rid, (a, b, la, lb) in failed:
        print('       DIFF %s: old=%s (%d) new=%s (%d)' % (rid, a, la, b, lb))
    return not failed


def assert_only_quantifiers(old_text, new_text_):
    r"""Доказать, что правка = ТОЛЬКО `\s*?` → `\s*` (комментарии не в счёт).

    Обе версии приводятся к одной шкале (строка-комментарий выброшена,
    `\s*?` → `\s*` в обеих) — любое иное изменение даст расхождение.
    """
    def norm(text):
        out = []
        for line in text.splitlines():
            if line.lstrip().startswith('#'):
                continue
            out.append(line.replace(LAZY, '\\s*'))
        return out
    a, b = norm(old_text), norm(new_text_)
    if a == b:
        print('diff-scope: изменены ТОЛЬКО кванторы (комментарии не в счёт) -> OK')
        return True
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            print('diff-scope: расхождение в некомментарной строке #%d:\n  HEAD: %s\n  NOW : %s'
                  % (i + 1, x.strip(), y.strip()))
            break
    else:
        print('diff-scope: разное число некомментарных строк (%d vs %d)'
              % (len(a), len(b)))
    return False


# ------------------------------------------------------------------- main ---
def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    text = read_text(PATH)
    variables = (yaml_doc(text).get('variables') or {})
    if '--against-head' in sys.argv:
        # доказательство против версии из HEAD: захватывает и РЕГЕНЕРИРОВАННЫЕ
        # braced-двойники (их после gen_braced.py --write на диске уже не lazy)
        import subprocess
        rel = os.path.relpath(PATH, ROOT).replace('\\', '/')
        old = subprocess.check_output(['git', 'show', 'HEAD:' + rel], cwd=ROOT)
        text = old.decode('utf-8')
        variables = (yaml_doc(text).get('variables') or {})
        fixed = read_text(PATH)
        print('proof: базовая версия — HEAD:%s, текущая — рабочая копия' % rel)
        scope_ok = assert_only_quantifiers(text, fixed)
        return 0 if prove(text, fixed, variables,
                          (yaml_doc(fixed).get('variables') or {})) and scope_ok else 1
    lines, sites = collect(text, variables)

    keep = [s for s in sites if s['verdict'][0] == 'KEEP']
    safe = [s for s in sites if s['verdict'][0] == 'SAFE'
            and not s['gen']]
    gen = [s for s in sites if s['gen']]
    print('%s: вхождений `%s` всего %d (в @begin-generated — %d)'
          % (os.path.basename(PATH), LAZY, len(sites), len(gen)))
    print('  SAFE к правке: %d | KEEP: %d | генерированный регион: %d'
          % (len(safe), len(keep), len(gen)))
    print('\n-- KEEP (не трогаем) --')
    for s in keep:
        print('  %5d %-22s %-10s %s' % (s['line'], s['label'],
                                        s['verdict'][1].split(' — ')[0],
                                        s['ctx']))
    print('\n-- SAFE (меняем `\\s*?` на `\\s*`) --')
    for s in safe:
        print('  %5d %-22s %s' % (s['line'], s['label'], s['ctx']))

    fixed = new_text(text, sites)
    if '--write' in sys.argv and fixed != text:
        with io.open(PATH, 'w', encoding='utf-8', newline='') as fh:
            fh.write(fixed)
        print('\n--write: правка применена (%d замен)' % len(safe))
    if '--write' in sys.argv:
        print('NB: регион @begin-generated не тронут — запустите '
              '`python _disdocs/syntax_highlighting/gen_braced.py --write`')

    print()
    ok = prove(text, fixed, variables, (yaml_doc(fixed).get('variables') or {}))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
