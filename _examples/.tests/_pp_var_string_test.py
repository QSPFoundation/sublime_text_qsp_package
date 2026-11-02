"""Таргетированный тест строковых литералов-значений в директиве var (Фаза 5, U3).
Золотой pptest.qsps строковых значений в var не содержит, поэтому сценарии здесь
закрывают новую функциональность отдельно. Запуск: python _pp_var_string_test.py
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

# --- Сценарий 1: строковое значение var участвует в сравнении (двойные кавычки) ---
src1 = [
    "# [t1]\n",
    '!@pp:var(sep = ", ")\n',        # литерал-значение ', '
    '!@pp:if(sep==", "):exclude\n',  # сравнение с таким же литералом -> истина -> exclude
    "X_hidden\n",
    "!@pp:endif\n",
    "Y_kept\n",
    "--- [t1] ---\n",
]
exp1 = ["# [t1]", "Y_kept", "--- [t1] ---"]
got1 = run(src1)
if got1 != exp1:
    fails.append(("scenario-1 string-value-equality", exp1, got1))

# --- Сценарий 2: литерал НЕ объявляет своё содержимое как метку ---
# var(msg="private") задаёт msg='private', но 'private' НЕ становится меткой,
# поэтому if(private) ложен и строка сохраняется.
src2 = [
    "# [t2]\n",
    '!@pp:var(msg = "private")\n',
    "!@pp:if(private):exclude\n",
    "KEEP_ME\n",
    "!@pp:endif\n",
    "--- [t2] ---\n",
]
exp2 = ["# [t2]", "KEEP_ME", "--- [t2] ---"]
got2 = run(src2)
if got2 != exp2:
    fails.append(("scenario-2 literal-not-a-label", exp2, got2))

# --- Сценарий 3: апострофы и спецсимволы внутри строки (двоеточие, обратный слэш) ---
src3 = [
    "# [t3]\n",
    "!@pp:var(path = 'C:\\dir')\n",
    "!@pp:if(path=='C:\\dir'):exclude\n",
    "HIDDEN\n",
    "!@pp:endif\n",
    "TAKEN\n",
    "--- [t3] ---\n",
]
exp3 = ["# [t3]", "TAKEN", "--- [t3] ---"]
got3 = run(src3)
if got3 != exp3:
    fails.append(("scenario-3 apostrophe-specials", exp3, got3))

# --- Сценарий 4: несовпадение литералов -> условие ложно -> ничего не исключается ---
src4 = [
    "# [t4]\n",
    '!@pp:var(flag = "yes")\n',
    '!@pp:if(flag=="no"):exclude\n',
    "SURVIVES\n",
    "!@pp:endif\n",
    "--- [t4] ---\n",
]
exp4 = ["# [t4]", "SURVIVES", "--- [t4] ---"]
got4 = run(src4)
if got4 != exp4:
    fails.append(("scenario-4 mismatch-no-exclude", exp4, got4))

if fails:
    for name, exp, got in fails:
        print(f"FAIL {name}:\n  expected: {exp}\n  got:      {got}")
    sys.exit(1)

print("OK: var-string tests 1..4 passed")
