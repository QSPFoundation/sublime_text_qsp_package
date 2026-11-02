"""Таргетированный тест множественного объявления меток var(a, b, c = value, ...)
(Фаза 5, U3 — множественные метки). Golden pptest.qsps использует только одиночный
var(...), поэтому сценарии здесь закрывают новую функциональность отдельно.
Запуск: python _pp_var_multi_test.py
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


fails = []

# --- Сценарий 1: три голые метки сразу ---
src1 = [
    "# [t1]\n",
    "!@pp:var(a, b, c)\n",
    "!@pp:if(a and b and c):exclude\n",  # все три объявлены -> истина -> exclude
    "HIDDEN\n",
    "!@pp:endif\n",
    "KEPT\n",
    "--- [t1] ---\n",
]
exp1 = ["# [t1]", "KEPT", "--- [t1] ---"]
got1 = run(src1)
if got1 != exp1:
    fails.append(("scenario-1 three-bare-labels", exp1, got1))

# --- Сценарий 2: смешанный список (документированный пример) ---
# var(name, age = August, 123): name — метка; age = August — метка со значением-меткой;
# 123 — голое число объявляет метку '123'. Все три условия истинны.
src2 = [
    "# [t2]\n",
    "!@pp:var(name, age = August, 123)\n",
    "!@pp:if(age==August):exclude\n",
    "A\n",
    "!@pp:endif\n",
    "!@pp:if(123):exclude\n",
    "B\n",
    "!@pp:endif\n",
    "!@pp:if(name):exclude\n",
    "C\n",
    "!@pp:endif\n",
    "RESULT_kept\n",
    "--- [t2] ---\n",
]
exp2 = ["# [t2]", "RESULT_kept", "--- [t2] ---"]
got2 = run(src2)
if got2 != exp2:
    fails.append(("scenario-2 mixed-doc-example", exp2, got2))

# --- Сценарий 3: пример владельца — метки, присваивание и строковый литерал в списке ---
# var(a, b, c = label, 'string', 123)
src3 = [
    "# [t3]\n",
    "!@pp:var(a, b, c = label, 'string', 123)\n",
    "!@pp:if(a):exclude\n",
    "1\n",
    "!@pp:endif\n",
    "!@pp:if(c==label):exclude\n",   # c -> 'label', и 'label' объявлен как метка
    "2\n",
    "!@pp:endif\n",
    "!@pp:if(string):exclude\n",      # голый литерал 'string' объявляет метку 'string'
    "3\n",
    "!@pp:endif\n",
    "OK\n",
    "--- [t3] ---\n",
]
exp3 = ["# [t3]", "OK", "--- [t3] ---"]
got3 = run(src3)
if got3 != exp3:
    fails.append(("scenario-3 owner-example", exp3, got3))

# --- Сценарий 4: необъявленная метка среди списка -> условие ложно -> без exclude ---
src4 = [
    "# [t4]\n",
    "!@pp:var(x, y)\n",
    "!@pp:if(z):exclude\n",           # z не объявлена -> False
    "SURVIVES\n",
    "!@pp:endif\n",
    "--- [t4] ---\n",
]
exp4 = ["# [t4]", "SURVIVES", "--- [t4] ---"]
got4 = run(src4)
if got4 != exp4:
    fails.append(("scenario-4 undeclared-in-list", exp4, got4))

# --- Сценарий 5: битый var(a,,b) не должен ронять препроцессор ---
# Под pp-on неразобранная директива уходит в стадию кода как спецкомментарий '!@'
# и удаляется — то же согласованное поведение, что и для прочих неизвестных '!@pp:'
# (см. golden: строка '!@pp:если…' тоже выбрасывается). Главное — без падения,
# соседние строки целы.
src5 = [
    "# [t5]\n",
    "!@pp:var(a,,b)\n",
    "line_after\n",
    "--- [t5] ---\n",
]
try:
    pp5 = QspsPP("On")
    out5 = _norm(pp5.pp_this_lines(src5))
    exp5 = ["# [t5]", "line_after", "--- [t5] ---"]
    if out5 != exp5:
        fails.append(("scenario-5 malformed-drop", exp5, out5))
except Exception as e:  # noqa
    fails.append(("scenario-5 no-crash", "no exception", f"{type(e).__name__}: {e}"))

# --- Сценарий 6: знаковые числа в var — знак +/- допустим в identifier (как в const) ---
# var(a, b = -5, 7): a — метка; b = -5 — метка со значением '-5'; 7 — голое число-метка.
src6 = [
    "# [t6]\n",
    "!@pp:var(a, b = -5, 7)\n",
    "!@pp:if(b==-5):exclude\n",   # b -> '-5'
    "X\n",
    "!@pp:endif\n",
    "!@pp:if(7):exclude\n",        # голое число объявляет метку '7'
    "Y\n",
    "!@pp:endif\n",
    "!@pp:if(a):exclude\n",        # a объявлена
    "Z\n",
    "!@pp:endif\n",
    "KEPT\n",
    "--- [t6] ---\n",
]
exp6 = ["# [t6]", "KEPT", "--- [t6] ---"]
got6 = run(src6)
if got6 != exp6:
    fails.append(("scenario-6 signed-numbers-var", exp6, got6))

if fails:
    for name, exp, got in fails:
        print(f"FAIL {name}:\n  expected: {exp}\n  got:      {got}")
    sys.exit(1)

print("OK: var-multi tests 1..6 passed")
