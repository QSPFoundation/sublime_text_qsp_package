# -*- coding: utf-8 -*-
"""Контроль Фазы 1 (п.1.4): YAML-load, резолв include/push, баланс скобок regex."""
import yaml, re, sys, os

# репозиторий = на 2 уровня выше этого файла; при копировании скрипта в другое
# место — скорректируйте путь относительно файла (или запустите с --root <путь>)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if '--root' in sys.argv:
    ROOT = sys.argv[sys.argv.index('--root') + 1]
BASE_DIR = os.path.join(ROOT, 'QSP.sublime-package') + '/'
FILES = {'base': 'qsp_base.sublime-syntax',
         'qsps': 'qsp.sublime-syntax',
         'qsrc': 'qsp.qsrc.sublime-syntax'}

data = {}
for k, f in FILES.items():
    with open(BASE_DIR + f, encoding='utf-8') as fh:
        txt = fh.read()
    data[k] = yaml.safe_load(txt.replace('%YAML 1.2', ''))
    data[k]['_txt'] = txt
    print(f + ': YAML load OK')

def collect_refs(node, used):
    if isinstance(node, dict):
        for key, val in node.items():
            if key in ('include', 'push'):
                vals = val if isinstance(val, list) else [val]
                for item in vals:
                    if isinstance(item, str) and 'Packages/' not in item:
                        used.add(item)
            elif key == 'embed' and isinstance(val, str) and 'Packages/' not in val:
                used.add(val)
            collect_refs(val, used)
    elif isinstance(node, list):
        for it in node:
            collect_refs(it, used)

ok = True
for k, f in FILES.items():
    d = data[k]
    ctx = dict(data['base']['contexts']) if d.get('extends') else {}
    ctx.update(d.get('contexts', {}))
    defined = set(ctx)
    used = set()
    collect_refs(d.get('contexts', []), used)
    # прототип тоже ссылается
    local_missing = set()
    for u in used:
        base_only = data['base'].get('contexts', {})
        target = ctx.get(u) or base_only.get(u)
        if isinstance(target, list):
            sub = set()
            collect_refs(target, sub)
            local_missing |= {s for s in sub if s not in defined}
    missing = {u for u in used if u not in defined} | local_missing
    print('%s: local=%d pool=%d refs=%d MISSING=%s'
          % (f, len(d.get('contexts', {})), len(defined), len(used),
             sorted(missing) if missing else 'none'))
    if missing:
        ok = False

def brace_balance(pattern, name):
    """Проверка баланса ( ) внутри regex с учётом экранирования и классов."""
    depth, i, in_class = 0, 0, False
    s = pattern
    while i < len(s):
        c = s[i]
        if c == '\\':
            i += 2
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
            if depth < 0:
                return 'extra ) at %d in %s' % (i, name)
        i += 1
    if depth != 0:
        return 'unbalanced ( depth=%d in %s' % (depth, name)
    if in_class:
        return 'unclosed [ in %s' % name
    return None

def check_regexes(txt, fname):
    errs = []
    for m in re.finditer(r'^\s*(match|replace|include):\s*(.+)$', txt, re.M):
        val = m.group(2).strip()
        if m.group(1) == 'include':
            continue
        # снять YAML-кавычки
        if len(val) >= 2 and val[0] in '\'"' and val[-1] == val[0]:
            val = val[1:-1]
        elif val.startswith("'") or val.startswith('"'):
            errs.append('open quote line: %s' % val[:40])
            continue
        if val.startswith('- '):
            continue
        e = brace_balance(val, '%s: %s' % (fname, val[:50]))
        if e:
            errs.append(e)
    return errs

for k, f in FILES.items():
    errs = check_regexes(data[k]['_txt'], f)
    # переменные тоже проверим
    for vm in re.finditer(r'^  (\w+): [\'"](.*)[\'"]\s*(?:#.*)?$', data[k]['_txt'], re.M):
        vname, vval = vm.groups()
        if '{{' in vval:
            continue  # шаблоны с подстановками — проверим после раскрутки
        e = brace_balance(vval, '%s@var:%s' % (f, vname))
        if e:
            errs.append(e)
    print('%s: regex brace balance -> %s' % (f, errs if errs else 'OK'))
    if errs:
        ok = False

# переменные: нет ли висящих {{...}} на несуществующие имена
all_vars = set(data['base'].get('variables', {}))
for k in ('qsps', 'qsrc'):
    all_vars |= set(data[k].get('variables', {}))
used_tpl = set()
for k, f in FILES.items():
    used_tpl |= set(re.findall(r'\{\{(\w+)\}\}', data[k]['_txt']))
undef = sorted(used_tpl - all_vars)
unused = sorted(all_vars - used_tpl)
print('declared vars:', len(all_vars), '| undefined {{refs}}:', undef or 'none',
      '| declared-but-unused:', unused or 'none')
if undef or unused:
    ok = False

print('RESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
