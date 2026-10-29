"""Контроль scope-ассертов в `syntax_test_*.qsps` БЕЗ Sublime (2026-10-29).

Зачем: прогон `Tools → Build With… → Syntax Test` нельзя автоматизировать
(headless в этой сборке ST не поднимается), а фикстуры создавались генератором,
который в репозиторий не попал. Этот скрипт ловит механические ошибки до прогона.

Как движок ST читает фикстуру (проверено 2026-10-29, см. HANDOFF §1o):
  1) ассертом считается ТОЛЬКО строка с префиксом `//` — `! ^^^ scope` и «голые»
     `^^ scope` движок молча игнорирует (файл рапортует `0 assertions`);
  2) `^` проверяет АБСОЛЮТНУЮ колонку: каретки должны стоять ровно под токеном;
  3) `<-` проверяет одну позицию — первый непробельный символ строки-цели
     (единственный способ утверждать про колонку 0, где `^` недостижим);
  4) блок подряд идущих ассертов относится к ПОСЛЕДНЕЙ не-ассерт-строке.

Что проверяет:
  1) «инертные» ассерты (без `//`) — молча не проверяют ничего;
  2) каретки уходят за конец строки-цели;
  3) спан `punctuation.*` длиннее одного символа (должен быть ровно сам знак);
  4) спан `meta.*` захватывает закрывающую скобку/пробел на конце;
  5) предупреждение: цель ассерта лежит ВНЕ локаций (`meta.gametext`) — законно
     только для тестов самого gametext'а (иначе scope будут чужими).

Запуск:  python _disdocs/syntax_highlighting/check_syntax_asserts.py [--write]
         без флагов — отчёт (exit 1 при найденных проблемах);
         `--write` — механически чинит найденное (CRLF/LF сохраняются).
"""
import io
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[2] / "QSP.sublime-package"
ASSERT = re.compile(r"^(\s*)//(\s*)(\^+)(\s+)(\S.*)$")
ARROW = re.compile(r"^(\s*)//(\s*)<-(?:\s+(\S.*))?$")
INERT_BARE = re.compile(r"^(\s*)(\^+)(\s+)(\S.*)$")
INERT_BANG = re.compile(r"^(\s*)!(\s*)(\^+)(\s+)(\S.*)$")
SCOPE = re.compile(r"^-?[A-Za-z_][\w.-]*$")
EOL = re.compile(r"(\r\n|\n|\r)$")
CLOSERS = ")]}"


def split_eol(chunk: str) -> tuple[str, str]:
    m = EOL.search(chunk)
    return (chunk[: len(chunk) - len(m.group(1))], m.group(1)) if m else (chunk, "")


def looks_like_scopes(payload: str) -> bool:
    """`keyword.control.else.qsp -comment.qsp` — да; `code (arm5 block body)` — нет."""
    tokens = payload.split()
    return bool(tokens) and all(SCOPE.match(t) or t.startswith("|") for t in tokens)


def audit(name: str, write: bool) -> int:
    path = PKG / name
    raw = io.open(path, encoding="utf-8", newline="").read()
    chunks = raw.splitlines(keepends=True)
    problems = 0
    code, code_no, code_in_loc, in_loc = "", 0, False, False
    out = []
    for i, chunk in enumerate(chunks):
        body, eol = split_eol(chunk)
        m = ASSERT.match(body)
        arrow = None if m else ARROW.match(body)
        if not m and not arrow:
            inert = INERT_BARE.match(body) or INERT_BANG.match(body)
            if inert and looks_like_scopes(inert.groups()[-1]):
                problems += 1
                print(f"{name}:{i + 1}: ассерт без префикса `//` — движок его НЕ видит")
            if body.startswith("#"):
                in_loc = code_in_loc = True
            elif body.startswith("--"):
                # `--` закрывает локацию, но САМА ещё принадлежит ей (её scope ставит
                # правило из location_body) — иначе ассерты про `--` вне локации.
                in_loc, code_in_loc = False, True
            else:
                code_in_loc = in_loc
            code, code_no = body, i + 1
            out.append(chunk)
            continue
        if arrow:
            if not code_in_loc:
                print(f"{name}:{i + 1}: цель `<-` вне локации (L{code_no}, meta.gametext?)")
            out.append(chunk)
            continue
        indent, gap, carets, sep, scopes = m.groups()
        # префикс ассерта = `//` + пробелы: каретки считаются от АБСОЛЮТНОЙ колонки
        start = len(indent) + 2 + len(gap)
        run = carets
        text = code[start:start + len(run)]
        new_run = None
        if not code_in_loc:
            print(f"{name}:{i + 1}: цель ассерта вне локации (L{code_no}, meta.gametext?)")
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
            body = indent + "//" + gap + new_run + sep + scopes
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
