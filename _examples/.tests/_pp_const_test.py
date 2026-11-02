"""Таргетированный тест директивы const и подстановки @name (Фаза 5, U3 — константы).
Semantics (по решению владельца):
  - const(a = литерал, ...) — список через запятую; у каждого элемента ОБЯЗАТЕЛЬНО
    `имя = значение`, значение — целое (в т.ч. знаковое) число или строковый литерал.
  - const(a = b) и const(label) — невалидны, директива не исполняется (recoverable-error).
  - const НЕ объявляет метку var (отдельная таблица) -> if(k) по имени константы ложен.
  - Подстановка @name выполняется строго ПОСЛЕ объявления (позиционно в тексте вывода).
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

# --- 1: строковая константа подставляется в тело локации ---
src1 = ["# [t1]\n", '!@pp:const(br = "<br>")\n', "say @br now\n", "--- [t1] ---\n"]
exp1 = ["# [t1]", "say <br> now", "--- [t1] ---"]
g = run(src1)
if g != exp1:
    fails.append(("1-string-subst", exp1, g))

# --- 2: числовые константы (положительная и отрицательная) ---
src2 = ["# [t2]\n", "!@pp:const(n = 42, m = -7)\n", "val @n and @m\n", "--- [t2] ---\n"]
exp2 = ["# [t2]", "val 42 and -7", "--- [t2] ---"]
g = run(src2)
if g != exp2:
    fails.append(("2-number-subst", exp2, g))

# --- 3: строго после объявления (до — остаётся как есть) ---
src3 = [
    "# [t3]\n",
    "before @x\n",
    '!@pp:const(x = "X!")\n',
    "after @x\n",
    "--- [t3] ---\n",
]
exp3 = ["# [t3]", "before @x", "after X!", "--- [t3] ---"]
g = run(src3)
if g != exp3:
    fails.append(("3-order-after-decl", exp3, g))

# --- 4: const НЕ объявляет метку var -> if(k) ложен, блок сохраняется ---
src4 = [
    "# [t4]\n",
    '!@pp:const(k = "v")\n',
    "!@pp:if(k):exclude\n",
    "SURVIVES\n",
    "!@pp:endif\n",
    "--- [t4] ---\n",
]
exp4 = ["# [t4]", "SURVIVES", "--- [t4] ---"]
g = run(src4)
if g != exp4:
    fails.append(("4-const-not-var-label", exp4, g))

# --- 5: граница идентификатора — @bb/@b_done не подменяются, @b да ---
src5 = ["# [t5]\n", '!@pp:const(b = "B")\n', "@b and @bb and @b_done\n", "--- [t5] ---\n"]
exp5 = ["# [t5]", "B and @bb and @b_done", "--- [t5] ---"]
g = run(src5)
if g != exp5:
    fails.append(("5-word-boundary", exp5, g))

# --- 6: невалидно const(a = b) — идентификатор-значение -> не исполняется, errored ---
src6 = ["# [t6]\n", "!@pp:const(a = b)\n", "text @a here\n", "--- [t6] ---\n"]
exp6 = ["# [t6]", "text @a here", "--- [t6] ---"]
g, err = run_tolerant(src6)
if g != exp6 or not err:
    fails.append(("6-invalid-const-ab", (exp6, True), (g, err)))

# --- 7: невалидно const(label) — нет значения -> не исполняется, errored ---
src7 = ["# [t7]\n", "!@pp:const(label)\n", "@label stays\n", "--- [t7] ---\n"]
exp7 = ["# [t7]", "@label stays", "--- [t7] ---"]
g, err = run_tolerant(src7)
if g != exp7 or not err:
    fails.append(("7-invalid-const-noval", (exp7, True), (g, err)))

# --- 8: атомарность — один невалидный элемент роняет всю директиву (ничего не заводятся) ---
src8 = ["# [t8]\n", "!@pp:const(good = 1, bad = x)\n", "@good @bad\n", "--- [t8] ---\n"]
exp8 = ["# [t8]", "@good @bad", "--- [t8] ---"]
g, err = run_tolerant(src8)
if g != exp8 or not err:
    fails.append(("8-invalid-item-atomic", (exp8, True), (g, err)))

if fails:
    for name, exp, got in fails:
        print(f"FAIL {name}:\n  expected: {exp}\n  got:      {got}")
    sys.exit(1)

print("OK: const tests 1..8 passed")
