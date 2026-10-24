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

## Шаги (пошагово, с ручной проверкой после каждого)

- [ ] **Шаг 0. Подготовка.** Зафиксировать «эталонное» поведение: открыть
      тестовые `.qsps` из `_examples/`, запомнить текущую подсветку как ориентир.
- [ ] **Шаг 1. Создать `qsp_base.sublime-syntax`.** Hidden-файл: перенести в
      него общие `variables` + все общие `contexts` из текущего `qsp.sublime-syntax`.
      `main` базы = тривиальный `- include: location_body`. Пока ничего на него
      не ссылается — проверить только, что файл компилируется (нет ошибок в
      Syntax Dev / консоли).
- [ ] **Шаг 2. qsps → `extends`.** Переписать `qsp.sublime-syntax`: добавить
      `extends: qsp_base.sublime-syntax`, удалить перенесённые общие контексты,
      оставить локально `main`/`diff`/`location_def`/`qspgame_header`/границы/
      между-локационный комментарий. Обновить `file_extensions` на
      `qsps, qsp-text, text-qsp`. Ручной тест: qsps-подсветка **идентична** Шагу 0.
- [ ] **Шаг 3. qsrc-синтаксис.** Переработать `qsp_locations.sublime-syntax` →
      `qsp.qsrc.sublime-syntax`: `extends: qsp_base`, `file_extensions: qsrc`,
      снять `hidden`, переписать `main` под «одна локация, границы = statements».
      Ручной тест: открыть `.qsrc`, убедиться что подсвечивается всё тело.
- [ ] **Шаг 4. Сверка расхождений.** Исправить в базе найденные баги дублирования
      (единый источник для обоих форматов):
      - `iinvalid.illegal.qsp` → `invalid.illegal.qsp` (опечатка, см. CONVENTIONS в CONTEXT.md);
      - расхождение `kw_operators` (`modobj|resetobj` есть в qsps, нет в locations);
      - `meta.excess_manilines_else` → `..._multiline_else`.
- [ ] **Шаг 5. Зачистка.** Убрать `# TODO` на строке 16 `qsp.sublime-syntax`;
      при необходимости — решение по `meta.diff` vs `comment.block`;
      финальная проверка сохранности всех `avs_*`-маркеров.

## Критерии готовности

- Оба формата грузятся без ошибок компиляции синтаксиса.
- qsps-поведение не изменилось относительно Шага 0 (кроме исправленных багов Шага 4).
- qsrc подсвечивает всё тело одной локации, границы — statements, без блока.
- Общая логика тела живёт в одном месте (`qsp_base`) — дублирование устранено.
- Все `avs_*`-маркеры и `entity.name.*`/`callable_locs`/`label_to_jump` сохранены
  (плагин не должен ничего потерять).
- Ссылка плагина `Packages/QSP/qsp.sublime-syntax` остаётся валидной.
