#!/usr/bin/env python3
"""Check that the session script agrees with the built presentation.

Usage: python3 scripts/check_sync.py <repo_root>

The checks are informational except for slide count, block coverage and the
UCI dataset id.  The block rule follows the current project requirement:
'На слайде' is mandatory, 'Демонстрация в Jamovi' exists only where an action
is performed, and explanations are plain text rather than a named block.
"""

import math
import re
from collections import Counter
from pathlib import Path

import click
import pdfplumber

EXPECTED_UCI_ID = "45"


def tokens(text: str) -> list[str]:
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    return [word[:5] for word in re.findall(r"[а-яёa-z]{4,}", text.lower())]


def cosine(a: Counter, b: Counter) -> float:
    numerator = sum(a[key] * b[key] for key in a.keys() & b.keys())
    denominator = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(
        sum(v * v for v in b.values())
    )
    return numerator / denominator if denominator else 0.0


def number_tokens(text: str) -> set[str]:
    text = text.replace("{,}", ",").replace("$", " ").replace("\\,", "")
    return {
        token.replace(".", ",")
        for token in re.findall(r"(?<![A-Za-z_\\])\d+(?:[.,]\d+)?", text)
    }


@click.command()
@click.argument("repo_root", type=click.Path(exists=True, path_type=Path))
def main(repo_root: Path) -> None:
    pdf_path = repo_root / "presentation" / "Презентация-Статистика-Jamovi-v1.pdf"
    script_path = repo_root / "Сценарий-заседания.tex"
    pres_path = repo_root / "presentation" / "Презентация-Статистика-Jamovi-v1.tex"
    readme_path = repo_root / "README.md"

    script = script_path.read_text(encoding="utf-8")
    presentation = pres_path.read_text(encoding="utf-8")
    readme = readme_path.read_text(encoding="utf-8")

    parts = re.split(r"\\subsection\*\{Слайд (\d+)\.", script)
    blocks: dict[int, str] = {}
    for index in range(1, len(parts), 2):
        blocks[int(parts[index])] = parts[index + 1].split(
            "\\section*{Источники формул}"
        )[0]

    with pdfplumber.open(pdf_path) as pdf:
        pages = {number: page.extract_text() or "" for number, page in enumerate(pdf.pages, 1)}

    failures = 0
    click.echo(f"slides in script: {len(blocks)}, pages in PDF: {len(pages)}")
    if len(blocks) != len(pages):
        click.echo("FAIL: slide count differs")
        failures += 1

    page_vectors = {number: Counter(tokens(text)) for number, text in pages.items()}
    click.echo("\n[1] script slide text similarity (informational):")
    for number, body in sorted(blocks.items()):
        match = re.search(r"\\begin\{onslide\}(.*?)\\end\{onslide\}", body, re.DOTALL)
        vector = Counter(tokens(match.group(1))) if match else Counter()
        if sum(vector.values()) < 20 or number not in page_vectors:
            continue
        similarities = {page: cosine(vector, vec) for page, vec in page_vectors.items()}
        best = max(similarities, key=similarities.get)
        if best != number and similarities[best] > similarities[number] + 0.25:
            click.echo(
                f"  slide {number}: own={similarities[number]:.2f}, "
                f"best page {best}={similarities[best]:.2f}"
            )
            failures += 1

    click.echo("\n[2] numbers missing on the same PDF page (informational):")
    for number, body in sorted(blocks.items()):
        match = re.search(r"\\begin\{onslide\}(.*?)\\end\{onslide\}", body, re.DOTALL)
        if not match:
            continue
        page_numbers = number_tokens(pages.get(number, ""))
        missing = sorted(
            token
            for token in number_tokens(match.group(1))
            if token not in page_numbers and token not in {"0", "1", "2", "3"}
        )
        if missing:
            click.echo(f"  slide {number}: {missing}")

    onslide_count = sum("\\begin{onslide}" in body for body in blocks.values())
    jamovi_count = sum("\\begin{jamovi}" in body for body in blocks.values())
    explain_count = sum("\\begin{explain}" in body for body in blocks.values())
    click.echo(
        f"\n[3] blocks: onslide={onslide_count}, jamovi={jamovi_count}, "
        f"explain={explain_count}"
    )
    if onslide_count != len(blocks):
        click.echo("FAIL: every slide needs an 'На слайде' block")
        failures += 1
    if explain_count != 0:
        click.echo("FAIL: explanations must be plain text, not a named block")
        failures += 1

    click.echo("\n[4] UCI dataset links:")
    for name, text in (
        ("presentation", presentation),
        ("script", script),
        ("README", readme),
    ):
        ids = set(re.findall(r"archive\.ics\.uci\.edu/dataset/(\d+)", text))
        flag = "" if ids <= {EXPECTED_UCI_ID} else "  <-- FAIL"
        click.echo(f"  {name}: {sorted(ids)}{flag}")
        if ids - {EXPECTED_UCI_ID}:
            failures += 1

    if failures:
        raise SystemExit(1)
    click.echo("\nOK: script and presentation are synchronized.")


if __name__ == "__main__":
    main()
