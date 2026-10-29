"""Конвертер scope-ассертов в формат, который РЕАЛЬНО читает Sublime Text.

Почему это нужно (2026-10-29, проверено прогоном):
  * движок `Tools → Build With… → Syntax Test` считает ассертом только строку,
    которая начинается с `//` (встроенный список маркеров комментария);
  * `! ^^^ scope` (QSP-комментарий) движок НЕ видит — файл рапортует
    `Success: 0 assertions`, то есть молча ничего не проверяет;
  * «голые» строки `^^^ scope` без маркера — тоже НЕ видны;
  * колонка каретки — АБСОЛЮТНАЯ (сверено с эталонными тестами ST:
    `Python/tests/syntax_test_python.py`, `JavaScript/tests/syntax_test_js.js`);
  * `<-` проверяет ровно ОДНУ позицию — первый непробельный символ строки-цели,
    поэтому это единственный способ утверждать про колонку 0 (`^` там
    недостижим: маркер `//` занимает колонки 0–1).

Что делает:
  * `^^^ scope`      → `//` + пробелы так, чтобы каретки остались на тех же колонках;
  * колонка 0        → `// <- scope` (позиция теряет длину спана — осознанно);
  * `! ^^^ scope`    → то же (маркер `!` был в колонке 0, каретки — по абсолютным колонкам);
  * строки-прозу (`! ^^^^^ code (arm5 block body)`) НЕ трогает: payload не похож на scope.

Запуск:  python _disdocs/syntax_highlighting/convert_assert_prefixes.py [--write]
         без `--write` — только отчёт.
"""
import io
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[2] / "QSP.sublime-package"
EOL = re.compile(r"(\r\n|\n|\r)$")
BARE = re.compile(r"^(\s*)(\^+)(\s+)(\S.*)$")
BANG = re.compile(r"^(\s*)!(\s*)(\^+)(\s+)(\S.*)$")
SLASH = re.compile(r"^(\s*//)(\s*)(\^+)(\s+)(\S.*)$")
ARROW = re.compile(r"^\s*//\s*<-")
# scope = любые точечные (keyword.control.end.qsp) И одиночные (avs_wrong_no_with_out_right)
# идентификаторы; скобки, кириллица и пробельные слова в скобках отсекаются.
SCOPE = re.compile(r"^-?[A-Za-z_][\w.-]*$")


def split_eol(chunk):
    m = EOL.search(chunk)
    return (chunk[: len(chunk) - len(m.group(1))], m.group(1)) if m else (chunk, "")


def looks_like_scopes(payload):
    """`keyword.control.else.qsp -comment.qsp` — да; `code (arm5 block body)` — нет."""
    tokens = payload.split()
    return bool(tokens) and all(SCOPE.match(t) or t.startswith("|") for t in tokens)


def render(col, run, payload):
    """Собрать // -строку с каретками на тех же абсолютных колонках."""
    if col >= 2:
        return "//" + " " * (col - 2) + run + " " + payload
    return "// <- " + payload


def convert(name, write):
    path = PKG / name
    chunks = io.open(path, encoding="utf-8", newline="").read().splitlines(keepends=True)
    changed = arrowed = 0
    out = []
    for i, chunk in enumerate(chunks, 1):
        body, eol = split_eol(chunk)
        if SLASH.match(body) or ARROW.match(body) or i == 1:
            out.append(chunk)
            continue
        m = BARE.match(body)
        if m:
            indent, run, sep, payload = m.groups()
            if not looks_like_scopes(payload):
                out.append(chunk)
                continue
            col = len(indent)
        else:
            m = BANG.match(body)
            if not m:
                out.append(chunk)
                continue
            indent, gap, run, sep, payload = m.groups()
            if not looks_like_scopes(payload):
                out.append(chunk)
                continue
            col = len(indent) + 1 + len(gap)
        new = render(col, run, payload)
        if new != body:
            changed += 1
            arrowed += col < 2
            print(f"{name}:{i}: col={col} run={len(run)} -> {new[:60]}")
        out.append(new + eol)
    if write and changed:
        io.open(path, "w", encoding="utf-8", newline="").write("".join(out))
    print(f"{name}: конвертировано {changed} (из них через `<-`: {arrowed})")
    return changed


def main():
    write = "--write" in sys.argv[1:]
    names = sorted(p.name for p in PKG.glob("syntax_test_*.qsps"))
    total = sum(convert(n, write) for n in names)
    print(f"файлов: {len(names)}; строк изменено: {total}" + ("" if write else " (режим отчёта)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
