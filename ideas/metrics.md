---
title: Git-метрики коммитов и изменения кода
updated: 2025-10-23
owners: [engineering-metrics@gitcto.space]
tags: [metrics, git, productivity, dashboards]
---

# Метрики Git: частота коммитов и размер изменений

## 1) Назначение
Система метрик помогает объективно оценивать активность разработки по Git:
- **Пульс работы**: стабильность темпа, спринтовые «волны».
- **Размер изменений**: где растёт код, где идёт рефакторинг.
- **Вклад участников**: баланс команды, нагрузка на людей/репозитории.
- **Стабильность**: признаки code churn и возможного техдолга.

---

## 2) Источники и агрегирование
- Источник: Git (через `pydriller` или `GitPython`).
- Гранулярность: `daily`, `weekly`.
- Срезы: автор, команда, репозиторий, ветка, модуль.

---

## 3) Частотные метрики коммитов

### 3.1. Базовые определения
- **CFI — Commit Frequency Index**

  \[
  \text{CFI} = \frac{N_{\text{commits}}}{T}
  \]
  где
  \( N_{\text{commits}} \) — число коммитов за период,
  \( T \) — длительность периода (в днях или неделях).

- **DCF — Daily Commit Frequency**

  \[
  \text{DCF} = \frac{N_{\text{commits}}}{\text{число дней}}
  \]

### 3.2. Интерпретация
- Ровная динамика → стабильный темп.
- Волнообразная динамика → неритмичность (сбрасывают в последний день спринта).
- Атипичные пики/провалы → проверить блокеры, релизы, онбординг и т.п.

### 3.3. Визуализации

#### Линейный график динамики CFI по авторам (weekly)
```python
import matplotlib.pyplot as plt

for author in weekly["author"].unique():
    subset = weekly[weekly["author"] == author]
    plt.plot(subset["date"], subset["CFI"], label=author)

plt.title("Commit Frequency Index по неделям")
plt.xlabel("Дата")
plt.ylabel("CFI (коммитов/день)")
plt.legend()
plt.grid(True)
plt.show()
```

#### Тепловая карта активности (календарная матрица)
- Оси: неделя × день недели.
- Значение: количество коммитов (или DCF).
- Вывод: быстро видно «горячие» и «холодные» дни.

#### Boxplot по авторам (распределение коммитов в день)
```python
import matplotlib.pyplot as plt

authors = daily["author"].unique()
data_by_author = [daily[daily["author"]==a]["commits"].values for a in authors]
plt.boxplot(data_by_author, labels=authors)
plt.title("Распределение частоты коммитов по авторам")
plt.ylabel("Коммитов в день")
plt.xticks(rotation=30, ha="right")
plt.grid(True, axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.show()
```

#### Накопленный тренд (cumulative)
```python
df_sorted = df.sort_values("date")
df_sorted["cumulative"] = range(1, len(df_sorted) + 1)
plt.plot(df_sorted["date"], df_sorted["cumulative"])
plt.title("Накопленная активность (Commit Trend)")
plt.xlabel("Дата")
plt.ylabel("Суммарное количество коммитов")
plt.grid(True)
plt.show()
```

## 4) Метрики размера изменений (diff)

### 4.1. Что оцениваем
- Сколько кода реально меняется во времени.
- Кто чаще делает крупные/мелкие изменения.
- Где возникают code churn (частые переписывания).
- Какие участки проекта постоянно изменяются / остаются стабильными.

### 4.2. Базовые расчёты

| Показатель | Формула/смысл | Интерпретация |
|------------|---------------|----------------|
| **LA — Lines Added** | ∑ добавленных строк | Прирост кода |
| **LD — Lines Deleted** | ∑ удалённых строк | Рефакторинг / чистка |
| **NLC — Net Lines Changed** | LA − LD | Чистый прирост |
| **Code Churn, %** | (LA + LD) / LOC_total × 100% | Подвижность кода |

Рекомендация: считать также rolling churn (на 2–4 недели) для сглаживания.

## 5) Индекс ценности изменений (CVI)

### 5.1. Идея
CVI (Code Value Index) — взвешенная оценка полезности и объёма изменений с нормализацией по масштабу коммита и типу файла. Помогает ответить:
- Кто внес наибольший вклад за месяц?
- Когда были пики разработки?
- Баланс вкладов по людям/репозиториям?
- Нет ли нестабильных зон (рост churn при низкой ценности)?

### 5.2. Вес строки по типу изменения

| Тип изменения | Вес |
|---------------|-----|
| Добавлена строка кода | +1.00 |
| Удалена строка кода | +1.00 |
| Изменена строка (в diff как add+del) | +2.00 |
| Изменена строка комментария/документации | +0.25 |

### 5.3. Модификатор по типу файла (пример)

| Тип файла | Множитель |
|-----------|-----------|
| Код (prod) | ×1.00 |
| Тесты | ×0.75 |
| Документация | ×0.75 |

Примечание: множители и веса — настраиваемые под продукт (например, усилить вес тестов до 0.9 в культурах TDD).

### 5.4. Нормализация объёма изменения коммита
Чтобы не «ломать» метрику огромными пачками кода, вводим лог-нормализацию:

\[
\text{DiffDelta(commit)} = \log(1 + \text{WeightedChanges})
\]

где WeightedChanges — сумма взвешенных изменений коммита с учётом типа изменения и типа файла.

### 5.5. Агрегирование CVI
- По автору: ∑ DiffDelta за период.
- По репозиторию/команде/ветке: аналогично.
- Баланс: доли участников в общекомандном CVI.
- Стабильность: высокий churn при низком CVI → сигнал к ревью архитектуры/процессов.

## 6) Разрезы визуализации
- По разработчикам: вклад, распределение размеров коммитов, CVI по неделям.
- По командам: баланс и пики разработки.
- По репозиториям/модулям: горячие зоны изменений.
- Жизненный цикл ветки: активность и CVI от создания до мержа.

## 7) Пример извлечения данных (Python, pydriller)

```python
from pydriller import Repository
import math
import pandas as pd
from pathlib import Path

REPO_PATH = Path("path/to/your/repo")

# Пример простого фильтра типов файлов (дополните своими расширениями/папками)
CODE_EXT = {".py", ".js", ".ts", ".java", ".go", ".cpp", ".c", ".rb"}
TEST_HINTS = ("test", "tests", "_test")
DOC_EXT = {".md", ".rst", ".adoc"}

def file_multiplier(filename: str) -> float:
    fn = filename.lower()
    ext = Path(fn).suffix
    if ext in DOC_EXT:
        return 0.75
    if any(h in fn for h in TEST_HINTS):
        return 0.75
    if ext in CODE_EXT:
        return 1.00
    return 0.50  # прочее: снизить влияние

def weighted_changes(mod) -> int:
    # pydriller даёт mod.added / mod.removed, но «изменённые» строки как add+del
    added = mod.added or 0
    removed = mod.removed or 0
    # Базовая стоимость: add(+1), del(+1); изменённые считаются естественно как add+del (~2)
    base = added + removed
    w = file_multiplier(mod.filename or "")
    return int(base * w)

rows = []
for commit in Repository(str(REPO_PATH)).traverse_commits():
    wc = 0
    for mod in commit.modifications:
        # Пропускаем бинарные/автогенерируемые по своим критериям (при необходимости)
        if not mod.filename:
            continue
        wc += weighted_changes(mod)

    diff_delta = math.log1p(wc)  # нормализация
    rows.append({
        "date": commit.committer_date,
        "author": commit.author.name,
        "email": commit.author.email,
        "hash": commit.hash,
        "repo": REPO_PATH.name,
        "weighted_changes": wc,
        "diff_delta": diff_delta,
    })

df = pd.DataFrame(rows)
```

## 8) Пример метрик и графиков поверх DataFrame

### 8.1. Частота коммитов (daily / weekly)
```python
# daily commits
daily = (
    df.assign(day=df["date"].dt.date)
      .groupby(["day", "author"], as_index=False)
      .agg(commits=("hash", "count"))
)
daily["DCF"] = daily["commits"]  # коммитов в день (на автора)

# weekly CFI
weekly = (
    df.assign(week=df["date"].dt.to_period("W").apply(lambda p: p.start_time))
      .groupby(["week", "author"], as_index=False)
      .agg(commits=("hash", "count"))
)
weekly["CFI"] = weekly["commits"] / 7.0
```

### 8.2. Code Churn на окно (rolling)
```python
# Пример: оценка churn как (LA+LD)/LOC_total — в этом примере используем surrogate: weighted_changes
# Если есть LOC_total по модулю/репо — подставьте реальный знаменатель.
roll = (
    df.assign(day=df["date"].dt.date)
      .groupby("day", as_index=False)
      .agg(weighted_changes=("weighted_changes", "sum"))
      .sort_values("day")
)
roll["rolling_changes_14d"] = roll["weighted_changes"].rolling(14, min_periods=3).sum()
# churn_% = rolling_changes_14d / LOC_total * 100 — если известен LOC_total
```

### 8.3. CVI по авторам за период
```python
cvi_by_author = (
    df.groupby("author", as_index=False)
      .agg(CVI=("diff_delta", "sum"))
      .sort_values("CVI", ascending=False)
)
```
