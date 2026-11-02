"""Таргетированный тест вложенных блоков условия (исправление B2).
Золотой pptest.qsps вложенных if не содержит, поэтому этот сценарий закрывает
B2 отдельно. Запуск: python _pp_nesting_test.py
Контекст: _disdocs/pp/handoff.md (Фаза 3).
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

# --- Сценарий 1: вложенный if внутри выключенного pp-блока (`if(a):off`) ---
src1 = [
    "# [test]\n",
    "!@pp:var(a)\n",
    "!@pp:if(a):off\n",     # исполняется, выключает pp до своего endif
    "kept1\n",             # дословно
    "!@pp:if(a):exclude\n",# pp выключен -> блок пропускается, строка дословно
    "inner_verbatim\n",    # дословно
    "!@pp:endif\n",        # парный к ПРОПУЩЕННОМУ if -> дословно (не закрывает внешний!)
    "kept2\n",             # всё ещё внутри off-блока -> дословно
    "!@pp:endif\n",        # парный к исполненному внешнему if -> убирается
    "kept3_after_outer\n", # pp снова включён -> обычно
    "--- [test] ---\n",
]
exp1 = [
    "# [test]",
    "kept1",
    "!@pp:if(a):exclude",
    "inner_verbatim",
    "!@pp:endif",
    "kept2",
    "kept3_after_outer",
    "--- [test] ---",
]
got1 = run(src1)
if got1 != exp1:
    fails.append(("scenario-1 off-nesting", exp1, got1))

# --- Сценарий 2: вложенный exclude (обе рамки исполняются) ---
# if(a):exclude исключает блок; внутренний if(b):include при неопределённой b
# даёт exclude; ключевое — внутренний endif НЕ должен раньше времени закрыть внешний.
src2 = [
    "# [t2]\n",
    "!@pp:var(a)\n",
    "!@pp:if(a):exclude\n",
    "X_excluded\n",
    "!@pp:if(b):include\n",
    "Y_excluded\n",
    "!@pp:endif\n",        # внутренний endif -> убирается, НЕ закрывает внешний
    "Z_excluded\n",        # всё ещё исключён (внешний exclude активен)
    "!@pp:endif\n",        # внешний endif -> убирается, восстанавливает include
    "W_kept\n",            # включён
    "--- [t2] ---\n",
]
exp2 = ["# [t2]", "W_kept", "--- [t2] ---"]
got2 = run(src2)
if got2 != exp2:
    fails.append(("scenario-2 exclude-nesting", exp2, got2))

# --- Сценарий 3: сиротский endif не должен ломать последующие строки ---
src3 = [
    "# [t3]\n",
    "!@pp:endif\n",        # осиротевший endif (нет парного if) -> просто убирается
    "kept_line\n",
    "--- [t3] ---\n",
]
exp3 = ["# [t3]", "kept_line", "--- [t3] ---"]
got3 = run(src3)
if got3 != exp3:
    fails.append(("scenario-3 orphan-endif", exp3, got3))

# --- Сценарий 4: три уровня вложенности — глубина не должна «съезжать» ---
# Ключ: внутренний `if(a):include` при истинном a НАМЕРЕННО отменяет внешний
# exclude для своего блока (строка '3' выходит). Остальные строки исключены
# вплоть до своего endif — каждый endif снимает ровно свой фрейм.
src4 = [
    "# [deep]\n",
    "!@pp:var(a)\n",
    "!@pp:if(a):exclude\n",   #1
    "1\n",
    "!@pp:if(a):exclude\n",   #2
    "2\n",
    "!@pp:if(a):include\n",   #3
    "3\n",
    "!@pp:endif\n",           # close3
    "4\n",
    "!@pp:endif\n",           # close2
    "5\n",
    "!@pp:endif\n",           # close1
    "6\n",
    "--- [deep] ---\n",
]
exp4 = ["# [deep]", "3", "6", "--- [deep] ---"]
got4 = run(src4)
if got4 != exp4:
    fails.append(("scenario-4 deep-nesting-3levels", exp4, got4))

if fails:
    for name, exp, got in fails:
        print(f"FAIL {name}:\n  expected: {exp}\n  got:      {got}")
    sys.exit(1)

print("OK: nesting tests 1..4 passed")
