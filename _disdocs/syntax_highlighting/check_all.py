# -*- coding: utf-8 -*-
"""Единый гейт перед коммитом в подсветку (аудит п.29).

Зачем: контроля три, команд тоже три — одну из них легко забыть. Здесь они
идут подряд, а вердикт общий: «зелёный» только если зелёные все.

  1) check_syntax_phase1.py  — YAML (с запретом дубликатов ключей), резолв
                               include/push, баланс скобок regex, переменные,
                               парность plain/braced, дрейф braced-региона;
  2) gen_braced.py --check   — регион `# @braced: auto` == перегенерация
                               (шаг есть и в 1), но даёт отдельный вердикт);
  3) check_syntax_asserts.py — геометрия scope-ассертов в `syntax_test_*.qsps`
                               (инертные ассерты, вылет кареток за строку,
                               спаны punctuation.*/meta.*).

Чего НЕ делает (осознанно):
  * `gen_braced.py --write` — регенерация braced-слоя, а не проверка;
  * живой `Tools → Build With… → Syntax Test` — headless не стартует в этой
    сборке Sublime (см. HANDOFF §1o), поэтому ассерты проверяются на диске
    (шаг 3) и глазами в редакторе.

Запуск: python _disdocs/syntax_highlighting/check_all.py
Выход:  0 — все проверки PASS; 1 — хотя бы одна FAIL (лог — выше вердикта).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

CHECKS = (
    ('check_syntax_phase1.py', []),
    ('gen_braced.py', ['--check']),
    ('check_syntax_asserts.py', []),
)


def _run(script, args):
    """Один прогон; вывод дочернего скрипта идёт в тот же stdout (без перехвата,
    чтобы при FAIL был виден полный лог проверки, а не только вердикт)."""
    print('=' * 72)
    print('>>> %s %s' % (script, ' '.join(args)))
    sys.stdout.flush()
    proc = subprocess.run([sys.executable, os.path.join(HERE, script)] + args,
                          cwd=ROOT)
    return proc.returncode == 0


def main():
    # Кириллица в выводе не должна ронять гейт на консоли без UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass
    results = [(script, _run(script, args)) for script, args in CHECKS]
    print('=' * 72)
    for script, ok in results:
        print('%-26s %s' % (script, 'PASS' if ok else 'FAIL'))
    failed = [script for script, ok in results if not ok]
    print('RESULT: %s' % ('PASS' if not failed else 'FAIL (%s)' % ', '.join(failed)))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
