#!/usr/bin/env python3
"""Reproduce the JZS Bayes factors quoted in the presentation.

The two-sample JZS Bayes factor integrates the Cauchy prior on the
standardized effect size.  The effective sample size is the harmonic
mean factor n1*n2/(n1+n2), which is the quantity entering the t statistic.
"""

import csv
import math
from pathlib import Path

import numpy as np
from scipy import integrate

DATA = Path(__file__).resolve().parents[1] / "data" / "heart-disease.csv"
PRIOR_R = 1.0 / math.sqrt(2.0)


def load_column(column: str, group: str) -> list[float]:
    with DATA.open(encoding="utf-8") as handle:
        return [
            float(row[column])
            for row in csv.DictReader(handle)
            if row["sex"] == group and row[column]
        ]


def jzs_bf10(t: float, n1: int, n2: int, r: float = PRIOR_R) -> float:
    df = n1 + n2 - 2
    n_eff = n1 * n2 / (n1 + n2)
    numerator = lambda g: (
        (2 * math.pi) ** -0.5
        / r
        * math.exp(-(g**2) / (2 * r**2))
        * (1 + n_eff * g**2) ** -0.5
        * (1 + t**2 / (df * (1 + n_eff * g**2))) ** (-(df + 1) / 2)
    )
    integral = integrate.quad(numerator, 0.0, np.inf)[0]
    denominator = (1 + t**2 / df) ** (-(df + 1) / 2)
    return float(integral / denominator)


def student_t(x: list[float], y: list[float]) -> tuple[float, float, float]:
    """Pooled-variance t statistic used by the JZS Bayes factor table."""
    n1, n2 = len(x), len(y)
    mean_diff = float(np.mean(x) - np.mean(y))
    v1, v2 = float(np.var(x, ddof=1)), float(np.var(y, ddof=1))
    pooled = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    t = mean_diff / math.sqrt(pooled * (1 / n1 + 1 / n2))
    return t, float(n1 + n2 - 2), mean_diff


def main() -> None:
    chol0 = load_column("chol", "0.0")
    chol1 = load_column("chol", "1.0")
    thal0 = load_column("thalach", "0.0")
    thal1 = load_column("thalach", "1.0")
    t_chol, _, diff = student_t(chol0, chol1)
    t_thal, _, _ = student_t(thal0, thal1)
    print(f"chol, sex=0 minus sex=1: t={t_chol:.3f}, diff={diff:.2f} mg/dl")
    print(f"BF10(chol), JZS r={PRIOR_R:.4f}: {jzs_bf10(t_chol, len(chol0), len(chol1)):.2f}")
    print(f"BF10(thalach), JZS r={PRIOR_R:.4f}: {jzs_bf10(t_thal, len(thal0), len(thal1)):.3f}")
    print(f"BF01(thalach): {1 / jzs_bf10(t_thal, len(thal0), len(thal1)):.2f}")


if __name__ == "__main__":
    main()
