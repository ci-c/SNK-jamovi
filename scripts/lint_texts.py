#!/usr/bin/env python3
"""Mechanical lint of the LaTeX sources against the project text requirements.

Usage: python3 scripts/lint_texts.py <repo_root>

A hit is a heuristic prompt to inspect the source.  Rules marked HARD block
the exit code.  Dashes inside mathematical legends are allowed.
"""

import re
from collections import Counter
from pathlib import Path

import click

RULES: list[tuple[str, bool, str, str]] = [
    ("S1", False, "imperative verb forms", r"\b(Откройте|Выберите|Включите|Нажмите|Укажите|Задайте|Перенесите|Проверьте|Сравните|Используйте|Запишите|Добавьте)\b"),
    ("S2", False, "arrow chains instead of sentences", r"\\to\b|→|\\rightarrow"),
    ("S3", True, "'Коэна d' / 'Хеджеса g' word order", r"Коэна d|Хеджеса g"),
    ("S4", False, "task for the audience", r"Попробуйте|Повторите самостоятельно|Задание для студент"),
    ("S5", True, "English words leaking into Russian prose", r"\b(correspond to|means that|which)\b"),
    ("S6", True, "backtick quotes", r"`[A-Za-z][^`']{2,40}`"),
    ("A1", True, "normality decides the method", r"применяется при нормальном распределении|определяет выбор критерия|выбор критерия определяется типом данных, типом групп и нормальностью"),
    ("A2", True, "CI excluding zero declared significant", r"не пересекает ноль, поэтому различие значимо"),
    ("A3", True, "Rouder cited for r = 0.707", r"0[{,.]*707[^\n]{0,80}Rouder|Rouder[^\n]{0,80}0[{,.]*707"),
    ("A4", True, "CONSORT 2025 attributed to Schulz", r"Schulz K\.? et al\.? CONSORT 2025|CONSORT 2025[^\n]{0,40}Schulz K\.? et al"),
    ("U1", True, "UCI dataset id other than 45", r"archive\.ics\.uci\.edu/dataset/(?!45/)\d+"),
]


def body(path: Path) -> str:
    text = path.read_text(encoding="utf-8").split("\\begin{document}", 1)[1]
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))


def strip_math(text: str) -> str:
    text = re.sub(r"\$[^$]*\$", " M ", text)
    text = re.sub(r"\\texttt\{[^}]*\}", " T ", text)
    return text


def dash_hits(text: str) -> list[int]:
    hits, in_legend = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if "{Обозначения}" in line or "Условные обозначения" in line:
            in_legend = True
        if " — " in line and not in_legend and "$" not in line:
            hits.append(number)
        if "\\end{block}" in line or "\\end{tcolorbox}" in line:
            in_legend = False
    return hits


@click.command()
@click.argument("repo_root", type=click.Path(exists=True, path_type=Path))
def main(repo_root: Path) -> None:
    files = {
        "presentation": repo_root / "presentation" / "Презентация-Статистика-Jamovi-v1.tex",
        "script": repo_root / "Сценарий-заседания.tex",
    }
    failed = False
    for name, path in files.items():
        raw = body(path)
        full = path.read_text(encoding="utf-8")
        text = strip_math(raw)
        click.echo(f"===== {name}")
        for rule_id, hard, description, pattern in RULES:
            source = full if rule_id in {"U1", "A3", "A4"} else text
            found = re.findall(pattern, source)
            if found:
                counts = Counter(item if isinstance(item, str) else item[0] for item in found)
                click.echo(
                    f"  {rule_id}{' HARD' if hard else ''} {description}: "
                    f"{len(found)} {dict(counts.most_common(3))}"
                )
                failed |= hard
        dashes = dash_hits(raw)
        if dashes:
            click.echo(f"  S7 dash outside legends: {len(dashes)} lines, first {dashes[:8]}")
            failed = True
    if failed:
        raise SystemExit(1)
    click.echo("OK: no hard lint failures.")


if __name__ == "__main__":
    main()
