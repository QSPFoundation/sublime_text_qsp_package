# -*- coding: utf-8 -*-
"""Контроль Фаз рефакторинга: YAML-load (с запретом ДУБЛИКАТОВ ключей),
резолв include/push, баланс скобок regex, переменные; с Фазы 5 — парность
plain/braced-контейнеров (п.5.1); с шага 4 — дрейф сгенерированного региона
braced-двойников (gen_braced.py)."""
import yaml, re, sys, os


class StrictLoader(yaml.SafeLoader):
    """SafeLoader, падающий на дубликатах ключей.

    PyYAML молча оставляет ПОСЛЕДНИЙ ключ, а Sublime — первый: дубль в
    `contexts:` молча меняет подсветку в зависимости от парсера. Ловить такое
    надо здесь, а не глазами.
    """


def _strict_mapping(loader, node, deep=False):
    seen = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, 'дубликат ключа %r' % (key,), key_node.start_mark)
        seen[key] = loader.construct_object(value_node, deep=deep)
    return seen


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)

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
    data[k] = yaml.load(txt.replace('%YAML 1.2', ''), Loader=StrictLoader)
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

# # # ------- Фаза 5, п.5.1: синхрон-контракт plain/braced ------- # # #
# С ШАГА 4 (P0, вариант A) braced-двойники НЕ пишутся руками: они генерируются
# скриптом gen_braced.py в guarded-регион qsp_base и проверяются ниже отдельным
# drift-check (регион == перегенерация из plain). Проверка парности оставлена
# как вторая линия защиты: она сверяет уже СГЕНЕРИРОВАННЫЕ двойники с plain
# посериализованно (ловит порчу региона руками и ошибки самого генератора).
PAIRS = ['multiline_actions', 'multiline_loop', 'multiline_conditions',
         'multiline_actions_else', 'multiline_actions_elseif',
         # Фаза 8: расширено на тела и pending-состояния, вынесенные в Фазе 7
         # (раньше их парность не проверялась вовсе) — тот же критерий:
         # отличие только суффикс '_braced' у include/push.
         'multiline_actions_body', 'multiline_conditions_body',
         'multiline_loop_body', 'multiline_elseif_body',
         'multiline_act_pending', 'multiline_if_pending',
         'multiline_loop_pending', 'multiline_loop_pending_prewhile',
         'multiline_elseif_pending',
         # фикс `else !коммент` (1g): тело многострочного else вынесено в
         # именованные контексты (нужны для push двух контекстов в arm'е).
         'else_body_block',
         # 1j: мёртвый регион однострочных else/elseif = многострочный
         # комментарий (хвост строки else/elseif выделяется
         # location_body[_braced]).
         'else_dead_line', 'elseif_dead_line']

def strip_braced_suffix(rules):
    """Копия правил, у include/push срезан хвост '_braced' (рекурсивно)."""
    cut = lambda x: x[:-len('_braced')] if isinstance(x, str) \
        and x.endswith('_braced') else x
    out = []
    for r in rules:
        if not isinstance(r, dict):
            out.append(r)
            continue
        r2 = dict(r)
        for key in ('include', 'push'):
            if key not in r2:
                continue
            v = r2[key]
            if isinstance(v, str):
                r2[key] = cut(v)
            elif isinstance(v, list):
                # элементы списка: строки (имена контекстов) режем напрямую,
                # словари (вложенные правила) — рекурсивно тем же проходом
                r2[key] = [cut(x) if isinstance(x, str) else
                           strip_braced_suffix([x])[0] if isinstance(x, dict) else x
                           for x in v]
        out.append(r2)
    return out

pair_errs = []
base_ctx = data['base']['contexts']
for name in PAIRS:
    plain, braced = base_ctx.get(name), base_ctx.get(name + '_braced')
    if plain is None or braced is None:
        pair_errs.append('%s: пара отсутствует' % name)
        continue
    if len(plain) != len(braced):
        pair_errs.append('%s: разное число правил (%d vs %d)'
                         % (name, len(plain), len(braced)))
        continue
    n_braced = strip_braced_suffix(braced)
    if yaml.safe_dump(plain, sort_keys=True) != yaml.safe_dump(n_braced, sort_keys=True):
        for i, (p, b) in enumerate(zip(plain, n_braced)):
            if yaml.safe_dump(p, sort_keys=True) != yaml.safe_dump(b, sort_keys=True):
                pair_errs.append('%s: правило #%d расходится' % (name, i))
print('braced pairing (5.1): %s'
      % (pair_errs if pair_errs
         else 'OK (%d пар), отличия — только суффикс _braced у include/push'
              % len(PAIRS)))
if pair_errs:
    ok = False

# # # ------- шаг 4: braced-слой ГЕНЕРИРУЕТСЯ (gen_braced.py) ------- # # #
# Двойники живут в guarded-регионе qsp_base (@begin/@end-generated) и обязаны
# побайтно совпадать с перегенерацией из plain-контекстов (маркер
# `# @braced: auto`). Дрейф = правка plain без `--write` или правка региона
# руками. Комментарии в регион не копируются, поэтому сверка — по правилам.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_braced
if not gen_braced.do_check(BASE_DIR + FILES['base']):
    ok = False

print('RESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
