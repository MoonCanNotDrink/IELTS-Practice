from __future__ import annotations

import asyncio
import importlib
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
SAMPLES_DIR = PROJECT_ROOT / "evaluation" / "samples"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RUNS_PER_SAMPLE = 3

SCORE_KEYS = [
    "fluency_score",
    "vocabulary_score",
    "grammar_score",
    "pronunciation_score",
    "overall_score",
]


sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

score_speaking = importlib.import_module("app.services.scoring_service").score_speaking


def load_samples() -> list[dict[str, Any]]:
    sample_paths = sorted(SAMPLES_DIR.glob("*.json"))
    if not sample_paths:
        raise FileNotFoundError(f"No sample files found in {SAMPLES_DIR}")

    samples: list[dict[str, Any]] = []
    for path in sample_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_file"] = path.name
        samples.append(payload)
    return samples


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: float | None, digits: int = 2, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if signed:
        return f"{value:+.{digits}f}"
    return f"{value:.{digits}f}"


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    header_line = " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * w for w in widths)
    print(header_line)
    print(sep_line)
    for row in rows:
        print(" | ".join(f"{cell:<{widths[i]}}" for i, cell in enumerate(row)))


async def run_one(sample: dict[str, Any], run_index: int) -> dict[str, Any]:
    try:
        result = await score_speaking(
            sample["transcript"],
            sample["question"],
            sample["part"],
        )
    except Exception as exc:
        return {
            "run": run_index,
            "status": "failed",
            "error": "exception",
            "detail": str(exc),
            "raw": None,
            "scores": None,
        }

    if not isinstance(result, dict):
        return {
            "run": run_index,
            "status": "failed",
            "error": "invalid_response",
            "detail": f"Unexpected response type: {type(result).__name__}",
            "raw": result,
            "scores": None,
        }

    if "error" in result:
        return {
            "run": run_index,
            "status": "failed",
            "error": result.get("error"),
            "detail": result.get("detail"),
            "raw": result,
            "scores": None,
        }

    extracted = {k: _safe_float(result.get(k)) for k in SCORE_KEYS}
    if any(v is None for v in extracted.values()):
        return {
            "run": run_index,
            "status": "failed",
            "error": "missing_scores",
            "detail": "One or more score keys missing or non-numeric",
            "raw": result,
            "scores": extracted,
        }

    return {
        "run": run_index,
        "status": "ok",
        "error": None,
        "detail": None,
        "raw": result,
        "scores": extracted,
    }


def aggregate(sample: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    expected = sample["human_expected"]
    ok_runs = [r for r in runs if r["status"] == "ok"]

    dimensions: dict[str, dict[str, float | None]] = {}
    for key in SCORE_KEYS:
        vals = [
            r["scores"][key]
            for r in ok_runs
            if r["scores"] and r["scores"][key] is not None
        ]
        expected_value = _safe_float(expected.get(key))
        mean_val = statistics.mean(vals) if vals else None
        std_val = (
            statistics.stdev(vals)
            if len(vals) >= 2
            else (0.0 if len(vals) == 1 else None)
        )
        delta = (
            (mean_val - expected_value)
            if (mean_val is not None and expected_value is not None)
            else None
        )

        dimensions[key] = {
            "expected": expected_value,
            "mean": mean_val,
            "stddev": std_val,
            "delta": delta,
        }

    return {
        "sample_id": sample["id"],
        "file": sample["_file"],
        "part": sample["part"],
        "band_level": sample["band_level"],
        "question": sample["question"],
        "notes": sample.get("notes", ""),
        "runs_total": len(runs),
        "runs_success": len(ok_runs),
        "runs_failed": len(runs) - len(ok_runs),
        "dimensions": dimensions,
        "runs": runs,
    }


async def main() -> None:
    samples = load_samples()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = datetime.now().isoformat(timespec="seconds")

    all_results: list[dict[str, Any]] = []
    for sample in samples:
        runs: list[dict[str, Any]] = []
        for run_idx in range(1, RUNS_PER_SAMPLE + 1):
            runs.append(await run_one(sample, run_idx))
        all_results.append(aggregate(sample, runs))

    payload = {
        "meta": {
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "runs_per_sample": RUNS_PER_SAMPLE,
            "sample_count": len(samples),
            "gemini_model": os.getenv("GEMINI_MODEL", ""),
        },
        "samples": all_results,
    }

    out_path = RESULTS_DIR / f"{stamp}.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    headers = [
        "ID",
        "band",
        "overall_expected",
        "overall_mean",
        "overall_stddev",
        "overall_delta",
    ]
    rows: list[list[str]] = []
    for item in all_results:
        overall = item["dimensions"]["overall_score"]
        rows.append(
            [
                item["sample_id"],
                item["band_level"],
                _fmt(overall["expected"]),
                _fmt(overall["mean"]),
                _fmt(overall["stddev"]),
                _fmt(overall["delta"], signed=True),
            ]
        )

    print(f"Saved full results to: {out_path}")
    print()
    _print_table(headers, rows)


if __name__ == "__main__":
    asyncio.run(main())
