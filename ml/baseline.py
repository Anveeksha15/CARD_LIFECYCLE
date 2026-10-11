"""Score the synthetic dataset with the baseline rules and record the results.

Usage: python -m ml.baseline [--data ml/data/transactions.csv]
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from ml.generate_data import HORIZON_SECONDS
from ml.metrics import report
from ml.offline_features import FEATURE_NAMES, compute_features
from services.fraud.rules import rules_flag

# Day 3 trains on the first 70% of the timeline and tests on the rest; the baseline is
# reported on the same test slice so the comparison is like-for-like.
TEST_START = 0.7 * HORIZON_SECONDS
RESULTS_DIR = Path("ml/results")


def evaluate(df: pd.DataFrame) -> dict:
    features = compute_features(df)
    flagged = [int(rules_flag(f)) for f in features[FEATURE_NAMES].to_dict("records")]
    df = df.assign(flagged=flagged)
    campaigns = df["campaign_id"].fillna("")

    test = df["ts"] >= TEST_START
    results = {
        "all": report(df["is_attack"], df["flagged"], campaigns),
        "test": report(df.loc[test, "is_attack"], df.loc[test, "flagged"], campaigns[test]),
        # Attack scenarios: share detected (recall). Normal scenarios: share flagged (FPR).
        "flag_rate_by_scenario": df.groupby("scenario")["flagged"].mean().round(4).to_dict(),
    }
    return results


def to_markdown(results: dict, n_rows: int) -> str:
    lines = [
        "# Rules baseline",
        "",
        f"Dataset: `python -m ml.generate_data` (seed 42, {n_rows:,} rows). Synthetic data only.",
        "Test slice = last 30% of the timeline (same split the models use).",
        "",
        "| slice | precision | recall | F1 | FPR (normal) | campaign recall |",
        "|---|---|---|---|---|---|",
    ]
    for name in ("all", "test"):
        r = results[name]
        lines.append(
            f"| {name} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} "
            f"| {r['fpr']:.4f} | {r['campaign_recall']:.3f} |"
        )
    lines += ["", "| scenario | share flagged |", "|---|---|"]
    for scenario, rate in results["flag_rate_by_scenario"].items():
        lines.append(f"| {scenario} | {rate:.3f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("ml/data/transactions.csv"))
    args = parser.parse_args()

    df = pd.read_csv(args.data, dtype={"bin": str})
    results = evaluate(df)
    markdown = to_markdown(results, len(df))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "baseline.json").write_text(json.dumps(results, indent=2) + "\n")
    (RESULTS_DIR / "baseline.md").write_text(markdown)
    print(markdown)


if __name__ == "__main__":
    main()
