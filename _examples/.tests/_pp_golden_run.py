"""Золотой контур препроцессора (Фаза 0 рефакторинга).
Прогоняет QspsPP('On') на pptest.qsps и сверяет с expected.qsps.
Перед каждой фазой рефакторинга: запускать, сверять golden_sha / matches_expected,
чтобы отличать намеренное изменение поведения от случайной регрессии.

Запуск (из любого места):  python _pp_golden_run.py
Подробности рефакторинга: _disdocs/pp/handoff.md
"""
import sys, hashlib, difflib
from pathlib import Path

HERE = Path(__file__).resolve().parent          # _examples/.tests
ROOT = HERE.parents[1]                            # project root
PKG = ROOT / "QSP.sublime-package"
sys.path.insert(0, str(PKG))

from qSpy.preprocessor import QspsPP  # noqa

INP = ROOT / "_examples/example_preprocessor/pptest.qsps"
EXP = ROOT / "_examples/example_preprocessor/expected.qsps"
GOLDEN = ROOT / "_disdocs/pp/_baseline_output.qsps"

src = INP.read_text(encoding="utf-8-sig").splitlines(keepends=True)
pp = QspsPP("On")
out = pp.pp_this_lines(src)
err = pp.errored()

GOLDEN.write_text("".join(out), encoding="utf-8")
digest = hashlib.sha256("".join(out).encode("utf-8")).hexdigest()[:16]

exp = EXP.read_text(encoding="utf-8-sig").splitlines(keepends=True)
norm = lambda ls: [l.rstrip("\r\n") for l in ls]
matched = norm(exp) == norm(out)

print(f"errored={err}")
print(f"out_lines={len(out)}  golden_sha={digest}")
print(f"matches_expected={matched}")
if not matched:
    diff = list(difflib.unified_diff(norm(exp), norm(out), "expected", "actual", lineterm=""))
    print("\n".join(diff[:60]))
