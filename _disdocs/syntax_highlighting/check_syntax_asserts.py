"""Контроль геометрии scope-ассертов в `syntax_test_*.qsps` (P4.4, 2026-10-29).

Зачем: прогон `Tools → Build With… → Syntax Test` нельзя автоматизировать
(headless в этой сборке ST не поднимается), а фикстуры создавались генератором,
который в репозиторий не попал. Генератор писал КОЛОНКИ 1-BASED — в результате
все кареты стояли на 1 символ правее токена (` ^^` под `if` покрывало `f `),
и файлы не могли пройти ни разу. Этот скрипт ловит такую геометрию без Sublime.

Что проверяет (ST относит блок подряд идущих ассертов к ПОСЛЕДНЕЙ строке-коду,
поэтому идём назад до первой не-ассерт-строки):
  1) кареты уходят за конец строки-кода;
  2) спан `punctuation.*` длиннее одного символа (должен быть ровно сам знак);
  3) спан `meta.*` захватывает закрывающую скобку/пробел на конце.

Запуск:  python _disdocs/syntax_highlighting/check_syntax_asserts.py [--write]
         без флагов — только отчёт (exit 1 при найденных проблемах);
         `--write` — механически чинит найденное (CRLF/LF сохраняются).
"""
import io
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[2] / "QSP.sublime-package"
ASSERT = re.compile(r"^(\s*)(\^+)(\s+)(\S.*)$")
EOL = re.compile(r"(\r\n|\n|\r)$")
CLOSERS = ")]}"


def split_eol(chunk: str) -> tuple[str, str]:
    m = EOL.search(chunk)
    return (chunk[: len(chunk) - len(m.group(1))], m.group(1)) if m else (chunk, "")


def audit(name: str, write: bool) -> int:
    path = PKG / name
    raw = io.open(path, encoding="utf-8", newline="").read()
    chunks = raw.splitlines(keepends=True)
    problems = 0
    code, code_no = "", 0
    out = []
    for i, chunk in enumerate(chunks):
        body, eol = split_eol(chunk)
        m = ASSERT.match(body)
        if not m:
            code, code_no = body, i + 1
            out.append(chunk)
            continue
        indent, carets, sep, scopes = m.groups()
        start = len(indent)
        run = carets
        text = code[start:start + len(run)]
        new_run = None
        if not text:
            problems += 1
            print(f"{name}:{i + 1}: кареты за концом строки-кода (L{code_no})")
        elif "punctuation." in scopes and len(run) > 1:
            # пунктуация — ровно один знак: оставляем последний символ блока
            if text[-1] in "()[]{}" or text[-1] in CLOSERS:
                new_run = " " * (len(run) - 1) + carets[-1]
                problems += 1
                print(f"{name}:{i + 1}: спан punctuation [{text}] (L{code_no})")
        elif "meta." in scopes:
            cut = len(text)
            for j, ch in enumerate(text):
                if ch in CLOSERS:
                    cut = j
                    break
            cut = len(text[:cut].rstrip())
            if 0 < cut < len(text):
                new_run = carets[:cut]
                problems += 1
                print(f"{name}:{i + 1}: спан meta [{text}] -> [{text[:cut]}] (L{code_no})")
        if new_run and write:
            n = len(new_run)
            body = indent + new_run + sep + scopes
            print(f"  -> исправлено: [{code[start:start + n]}]")
        out.append(body + eol)
    if write and problems:
        io.open(path, "w", encoding="utf-8", newline="").write("".join(out))
    return problems


def main() -> int:
    write = "--write" in sys.argv[1:]
    files = sorted(p.name for p in PKG.glob("syntax_test_*.qsps"))
    total = sum(audit(f, write) for f in files)
    print(f"проверено файлов: {len(files)}; проблем: {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
