"""Разовая правка фикстур под Фазу 10 (пунктуация однострочных скобок).

1) syntax_test_qsp_multiline_headers.qsps: ассерт `(` в `if ($a and $b):` снова
   ПОЗИТИВНЫЙ + добавлен ассерт на `)`.
2) syntax_test_qsp.qsps: новая локация `# однострочные скобки` (после локации
   `# скобки и комментарии`) — `( )` и `[ ]`, сбалансированные в строке.

Колонки не набираются руками: каретки строятся от реальных позиций символов.
Без флагов — отчёт, `--write` — запись.
"""
import io
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[2] / "QSP.sublime-package"


def load(name):
    raw = io.open(PKG / name, encoding="utf-8", newline="").read()
    return raw.splitlines(keepends=True)


def split(chunk):
    if chunk.endswith("\r\n"):
        return chunk[:-2], "\r\n"
    if chunk.endswith("\n"):
        return chunk[:-1], "\n"
    if chunk.endswith("\r"):
        return chunk[:-1], "\r"
    return chunk, ""


def assert_at(code, col, scopes):
    """`// ^^^ scopes` (без EOL), каретка над code[col]."""
    assert code[col] not in " \t", (code, col)
    return "//" + " " * (col - 2) + "^" + " " + scopes


def patch_headers(write):
    name = "syntax_test_qsp_multiline_headers.qsps"
    lines = load(name)
    target = None
    for i, ch in enumerate(lines):
        if split(ch)[0] == "if ($a and $b):":
            target = i
            break
    if target is None:
        print(f"{name}: не нашёл строку-цель")
        return 1
    code, eol = split(lines[target])
    old_i = target + 2  # третий ассерт подряд
    old, _ = split(lines[old_i])
    if not old.startswith("// ^ -invalid.illegal.qsp"):
        print(f"{name}: ожидался негативный ассерт `(` на строке {old_i + 1}, а там {old!r}")
        return 1
    new = [
        assert_at(code, code.index("("), "punctuation.section.parens.begin.qsp") + eol,
        assert_at(code, code.index(")"), "punctuation.section.parens.end.qsp") + eol,
        old + eol,
    ]
    print(f"{name}:{old_i + 1}: `{old}` -> позитивный + ассерт `)`")
    if write:
        lines[old_i:old_i + 1] = new
        io.open(PKG / name, "w", encoding="utf-8", newline="").write("".join(lines))
    return 0


def patch_inline_loc(write):
    name = "syntax_test_qsp.qsps"
    lines = load(name)
    anchor = None
    for i, ch in enumerate(lines):
        if split(ch)[0].startswith("-- скобки и комментарии"):
            anchor = i
            break
    if anchor is None:
        print(f"{name}: не нашёл якорь `-- скобки и комментарии`")
        return 1
    if any("# однострочные скобки" in split(ch)[0] for ch in lines):
        print(f"{name}: локация уже существует — пропуск")
        return 0
    eol = split(lines[anchor])[1]
    a = "set $y = ($a and $b)"
    b = "set $z = $arr[1 + 2]"
    block = [
        "# однострочные скобки",
        "! Фаза 10: сбалансированные в строке ( ) и [ ] тоже punctuation (раньше scope не было)",
        a,
        assert_at(a, a.index("("), "punctuation.section.parens.begin.qsp"),
        assert_at(a, a.index(")"), "punctuation.section.parens.end.qsp"),
        b,
        assert_at(b, b.index("["), "punctuation.section.brackets.begin.qsp"),
        assert_at(b, b.index("]"), "punctuation.section.brackets.end.qsp"),
        "-- однострочные скобки ------------------------------",
        "",
    ]
    print(f"{name}: вставка локации после строки {anchor + 1}")
    for ln in block:
        print("  +", ln)
    if write:
        lines[anchor + 1:anchor + 1] = [ln + eol for ln in block]
        io.open(PKG / name, "w", encoding="utf-8", newline="").write("".join(lines))
    return 0


if __name__ == "__main__":
    do_write = "--write" in sys.argv[1:]
    rc = patch_headers(do_write) + patch_inline_loc(do_write)
    print("записано" if do_write else "отчёт (без --write)")
    sys.exit(rc)
