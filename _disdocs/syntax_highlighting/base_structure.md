# План рефакторинга подсветки синтаксиса QSP (Sublime Text)

> Файл-дорожная карта. Детальный переносимый контекст (понимание задачи,
> решения, инварианты, статус шагов) — в [`CONTEXT.md`](./CONTEXT.md).

## Цель

Развести две группы форматов и устранить дублирование через **третий общий
базовый синтаксис**:

| Формат | Расширения | Семантика подсветки |
|--------|-----------|---------------------|
| **qsps** | `.qsps`, `.qsp-text`, `.text-qsp` | Весь файл. Локации как блоки `# … --`. Между локациями — игнорируемый текст (комментарий), кроме первой строки `QSP-Game`. |
| **qsrc** | `.qsrc` | Каждый файл = одна локация. Подсвечивается всё. Начало/конец локации — самостоятельные statements, БЕЗ объявления блока. Текста между локациями нет. |

Общее для обоих — **подсветка кода тела локации**. Разное — **границы локации**
и (для qsps) **текст между локациями**.

## Архитектура (Option B — общая база)

```
qsp_base.sublime-syntax        (hidden, scope: source.qsp.base)
  ├── общие variables
  └── общие contexts: location_body + ВСЁ, что он включает
        (strings, subexpression, comments, functions, operacion, figure_brace,
         multiline_actions/conditions/loop, kw_declarations, system_variables,
         users_variables, labels, operators, htmlsupport, preprocessor, ...)
        ▲ extends                         ▲ extends
        │                                 │
qsp.sublime-syntax              qsp.qsrc.sublime-syntax
  (qsps, scope: source.qsp)       (qsrc, scope: source.qsrc.qsp)
  - main: header → diff           - main: границы-statements + всё тело как код
  - location_def (# ... --)       - начало/конец локации НЕ открывают блок
  - qspgame_header
  - между-локационный комментарий
```

Почему база-наследование (`extends`), а не «qsps extends qsrc»: `main` qsrc
(«весь файл = одна локация») конфликтует с `main` qsps («файл с блоками и
текстом между ними»). Общая часть — это лист (`location_body`), поэтому её и
выносим в нейтральную базу, а каждый формат навешивает сверху свой `main`.

## Где что живёт: формат-специфичные контексты (уточнено 2026-10-29, P4.2)

| Контекст | Где определён / инклюднут | Зачем |
|---|---|---|
| `qspgame_header` | только `qsp.sublime-syntax#main` | заголовок `QSP-Game` первой строкой |
| `location_def`, `diff`, `meta.gametext.qsp` | только qsps | границы локаций и текст между ними |
| `qspdocs` (`!@ #… - …`) | контекст в `qsp_base`, инклюднут в **ОБОИХ** форматах: `qsp.sublime-syntax#diff` И `qsp.qsrc.sublime-syntax#main` | НЕ оверинклюд: в qsrc `!@`-строка формально `!`-комментарий, но док-описанию сознательно даётся `entity.other.attribute-name.documentation.qsp` |
| `preprocessor` (`!@pp:`) | `qsp_base`: `body_common_mid` + `string_common` | директива препроцессора работает в обоих форматах |
| `*_braced` двойники | `qsp_base`, регион `@begin-generated` | тело внутри `{…}`; генерируются `gen_braced.py`, руками не правятся |

Следствие: `qspdocs`/`preprocessor` в qsrc — намеренное решение, НЕ повод «чистить» их оттуда.
