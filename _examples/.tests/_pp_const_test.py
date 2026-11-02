"""Таргетированный тест директивы const и подстановки @name (Фаза 5, U3 — константы).
Semantics (по решению владельца) — позиционный стиль, как у var:
  - const(a, b, c = 'literal', 123, -1) — ровно один "=" внутри скобок: слева список
    имён через запятую, справа список литералов-значений через запятую; пары сопоставляются
    ПОЗИЦИОННО (число имён обязано равняться числу значений).
  - Одиночная форма const(name = литерал) — частный случай (1 имя, 1 значение).
  - Значение — целое (в т.ч. знаковое) число или строковый литерал. const(a = b) (голый
    идентификатор-значение), const(label) (без "="), несовпадение числа имён/значений —
    невалидны: директива не исполняется (recoverable-error), НИЧЕГО не заводится (атомарно).
  - const НЕ объявляет метку var (отдельная таблица) -> if(k) по имени константы ложен.
  - Подстановка @name выполняется строго ПОСЛЕ объявления (позиционно в тексте вывода).
  - СТРОКОВАЯ константа обрамляется апострофами: вне '...'-литерала -> 'literal';
    ВНУТРИ '...'-литерала -> ''literal'' (спаренные апострофы = экранированный апостроф).
    ЧИСЛОВАЯ константа подставляется как есть, без кавычек, независимо от контекста.
    Комментарий/код не различаются; апостроф внутри "...-литерала — не разделитель.
  - Необъявленные @foo остаются как есть; совпадение по полному идентификатору [A-Za-z0-9_].
Запуск: python _pp_const_test.py
Контекст: _disdocs/pp/handoff.md (Фаза 5).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "QSP.sublime-package"))
from qSpy.preprocessor import QspsPP  # noqa


def _norm(lines):
    return [l.rstrip("\r\n") for l in lines if l.strip("\r\n") != ""]


def run(src):
    pp = QspsPP("On")
    out = pp.pp_this_lines(src)
    assert not pp.errored(), "препроцессор не должен падать на корректном коде"
    return _norm(out)


def run_tolerant(src):
    """Возвращает (нормализованный вывод, errored) без утверждений — для невалидных директив."""
    pp = QspsPP("On")
    out = _norm(pp.pp_this_lines(src))
    return out, pp.errored()


fails = []

# --- 1: строковая константа ВНЕ литерала -> одиночные апострофы ---
src1 = ["# [t1]\n", '!@pp:const(br = "<br>")\n', "say @br now\n", "--- [t1] ---\n"]
exp1 = ["# [t1]", "say '<br>' now", "--- [t1] ---"]
g = run(src1)
if g != exp1:
    fails.append(("1-string-outside-quote", exp1, g))

# --- 2: числовая константа -> как есть, без кавычек ---
src2 = ["# [t2]\n", "!@pp:const(n, m = 42, -7)\n", "val @n and @m\n", "--- [t2] ---\n"]
exp2 = ["# [t2]", "val 42 and -7", "--- [t2] ---"]
g = run(src2)
if g != exp2:
    fails.append(("2-positional-numbers", exp2, g))

# --- 3: позиционный смешанный список: a->'literal' (строка), b->123, c->-1 (числа) ---
src3 = [
    "# [t3]\n",
    "!@pp:const(a, b, c = 'literal', 123, -1)\n",
    "A=[@a] B=[@b] C=[@c]\n",
    "--- [t3] ---\n",
]
exp3 = ["# [t3]", "A=['literal'] B=[123] C=[-1]", "--- [t3] ---"]
g = run(src3)
if g != exp3:
    fails.append(("3-owner-positional-example", exp3, g))

# --- 4: строго после объявления (до — остаётся как есть) ---
src4 = [
    "# [t4]\n",
    "before @x\n",
    '!@pp:const(x = "X!")\n',
    "after @x\n",
    "--- [t4] ---\n",
]
exp4 = ["# [t4]", "before @x", "after 'X!'", "--- [t4] ---"]
g = run(src4)
if g != exp4:
    fails.append(("4-order-after-decl", exp4, g))

# --- 5: const НЕ объявляет метку var -> if(k) ложен, блок сохраняется ---
src5 = [
    "# [t5]\n",
    '!@pp:const(k = "v")\n',
    "!@pp:if(k):exclude\n",
    "SURVIVES\n",
    "!@pp:endif\n",
    "--- [t5] ---\n",
]
exp5 = ["# [t5]", "SURVIVES", "--- [t5] ---"]
g = run(src5)
if g != exp5:
    fails.append(("5-const-not-var-label", exp5, g))

# --- 6: граница идентификатора — @bb/@b_done не подменяются, @b да (в одиночные апострофы) ---
src6 = ["# [t6]\n", '!@pp:const(b = "B")\n', "@b and @bb and @b_done\n", "--- [t6] ---\n"]
exp6 = ["# [t6]", "'B' and @bb and @b_done", "--- [t6] ---"]
g = run(src6)
if g != exp6:
    fails.append(("6-word-boundary", exp6, g))

# --- 7: невалидно const(a = b) — голый идентификатор-значение -> errored ---
src7 = ["# [t7]\n", "!@pp:const(a = b)\n", "text @a here\n", "--- [t7] ---\n"]
exp7 = ["# [t7]", "text @a here", "--- [t7] ---"]
g, err = run_tolerant(src7)
if g != exp7 or not err:
    fails.append(("7-invalid-const-ab", (exp7, True), (g, err)))

# --- 8: невалидно const(label) — нет "=" -> errored ---
src8 = ["# [t8]\n", "!@pp:const(label)\n", "@label stays\n", "--- [t8] ---\n"]
exp8 = ["# [t8]", "@label stays", "--- [t8] ---"]
g, err = run_tolerant(src8)
if g != exp8 or not err:
    fails.append(("8-invalid-const-noval", (exp8, True), (g, err)))

# --- 9: несовпадение числа имён/значений -> атомарно ничего не заводится, errored ---
src9 = ["# [t9]\n", "!@pp:const(good, extra = 1)\n", "@good @extra\n", "--- [t9] ---\n"]
exp9 = ["# [t9]", "@good @extra", "--- [t9] ---"]
g, err = run_tolerant(src9)
if g != exp9 or not err:
    fails.append(("9-count-mismatch-atomic", (exp9, True), (g, err)))

# --- 10: невалидное значение в списке роняет всю директиву (атомарность) ---
src10 = ["# [t10]\n", "!@pp:const(good, other = 1, x)\n", "@good @other\n", "--- [t10] ---\n"]
exp10 = ["# [t10]", "@good @other", "--- [t10] ---"]
g, err = run_tolerant(src10)
if g != exp10 or not err:
    fails.append(("10-invalid-value-in-list-atomic", (exp10, True), (g, err)))

# --- 11: строковая константа ВНУТРИ '...'-литерала -> спаренные апострофы ''literal'' ---
src11 = [
    "# [t11]\n",
    "!@pp:const(nm = 'Aleks')\n",
    "greet 'I say @nm!'\n",
    "--- [t11] ---\n",
]
exp11 = ["# [t11]", "greet 'I say ''Aleks''!'", "--- [t11] ---"]
g = run(src11)
if g != exp11:
    fails.append(("11-string-inside-single-quote-doubled", exp11, g))

# --- 12: апостроф внутри "...-литерала — НЕ разделитель; подстановка в одиночные апострофы ---
src12 = [
    "# [t12]\n",
    "!@pp:const(name='Aleks')\n",
    '*pl "Hello, I\'m <<@name>>"\n',
    "--- [t12] ---\n",
]
exp12 = ["# [t12]", '*pl "Hello, I\'m <<\'Aleks\'>>"', "--- [t12] ---"]
g = run(src12)
if g != exp12:
    fails.append(("12-apostrophe-in-double-quote", exp12, g))

# --- 13: подстановка в комментарии — без различия контекста (одиночные апострофы) ---
src13 = [
    "# [t13]\n",
    "!@pp:const(name='Aleks')\n",
    "! hero name @name\n",
    "--- [t13] ---\n",
]
exp13 = ["# [t13]", "! hero name 'Aleks'", "--- [t13] ---"]
g = run(src13)
if g != exp13:
    fails.append(("13-string-in-comment", exp13, g))

# --- 14: ЧИСЛОВАЯ константа внутри '...'-литерала -> как есть, без кавычек ---
src14 = [
    "# [t14]\n",
    "!@pp:const(n = 42)\n",
    "x '@n here'\n",
    "--- [t14] ---\n",
]
exp14 = ["# [t14]", "x '42 here'", "--- [t14] ---"]
g = run(src14)
if g != exp14:
    fails.append(("14-number-inside-single-quote-raw", exp14, g))

if fails:
    for name, exp, got in fails:
        print(f"FAIL {name}:\n  expected: {exp}\n  got:      {got}")
    sys.exit(1)

print("OK: const tests 1..14 passed")
