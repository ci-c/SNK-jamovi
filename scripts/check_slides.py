#!/usr/bin/env python3
"""Compare slide titles in the presentation source and the scenario source."""

import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRES = glob.glob(str(ROOT / "presentation" / "*.tex"))[0]
SCEN = str(ROOT / "Сценарий-заседания.tex")


def presentation_titles(text):
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))
    pattern = re.compile(
        r"\\section\{([^}]*)\}"
        r"|\\begin\{frame\}(?:\[[^\]]*\])?\{([^}]*)\}"
        r"|\\begin\{screenslide\}\{([^}]*)\}"
    )
    titles = []
    if "\\workshoptitleslide" in text:
        titles.append("Введение в медицинскую статистику")
    for match in pattern.finditer(text):
        title = match.group(1) or match.group(2) or match.group(3)
        if title:
            titles.append(re.sub(r"\s+", " ", title).strip())
    if "\\workshopcontacts" in text:
        titles.append("Спасибо за внимание")
    return titles


def scenario_titles(text):
    pattern = re.compile(r"\\subsection\*\{Слайд (\d+)\. ([^}]*)\}")
    return {int(m.group(1)): m.group(2).strip() for m in pattern.finditer(text)}


def main():
    pres_text = Path(PRES).read_text(encoding="utf-8")
    scen_text = Path(SCEN).read_text(encoding="utf-8")
    pres = presentation_titles(pres_text)
    scen = scenario_titles(scen_text)
    print(f"Presentation frames: {len(pres)}")
    print(f"Scenario slides: {len(scen)}")
    errors = []
    if len(pres) != len(scen):
        errors.append("Slide counts differ.")
    for number, title in scen.items():
        if number > len(pres):
            errors.append(f"Scenario slide {number} has no presentation frame.")
            continue
        def norm(value):
            return (
                value.replace("–", "-")
                .replace("−", "-")
                .replace("--", "-")
                .replace("$", "")
                .replace("{,}", ",")
                .replace(" ", "")
            )
        if norm(title)[:30] not in norm(pres[number - 1])[:30]:
            errors.append(
                f"Slide {number}: scenario '{title}' vs presentation '{pres[number - 1]}'"
            )
    if errors:
        print("MISMATCHES:")
        for error in errors:
            print("-", error)
        raise SystemExit(1)
    print("OK: slide numbers and titles match.")


if __name__ == "__main__":
    main()
