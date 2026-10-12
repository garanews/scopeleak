"""Run every scenario through one or more models and report metrics.

    py -m eval.run --models gemma3:4b
    py -m eval.run --models baseline,gemma3:4b,gemma3:12b --base-url http://gpu-box:11434/v1
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from core import classifier, llm

SCENARIOS = Path(__file__).parent / "scenarios"
RESULTS = Path(__file__).parent / "results"
LABELS = ("included", "extra", "ambiguous")

# The naive approach a script would take: phrases that usually signal new work.
CREEP_WORDS = re.compile(r"\b(also|add|another|more|too|extra|new|once more|as well)\b", re.I)


def baseline(message: str) -> dict:
    verdict = "extra" if CREEP_WORDS.search(message) else "included"
    return {"verdict": verdict, "model_verdict": verdict, "evidence": {"downgraded": False}}


def load_cases():
    for scenario in sorted(p for p in SCENARIOS.iterdir() if p.is_dir()):
        agreement = (scenario / "contract.txt").read_text(encoding="utf-8")
        for case in json.loads((scenario / "requests.json").read_text(encoding="utf-8")):
            yield scenario.name, agreement, case


def run_model(model: str, config: dict) -> list[dict]:
    rows = []
    for scenario, agreement, case in load_cases():
        start = time.perf_counter()
        if model == "baseline":
            items = [baseline(case["message"])]
        else:
            try:
                items = classifier.classify(agreement, case["message"], {**config, "model": model})
            except Exception as exc:  # keep going: a failed case is a data point
                items = [{"verdict": "ambiguous", "model_verdict": "error", "error": str(exc),
                          "evidence": {"downgraded": False}}]
        elapsed = time.perf_counter() - start
        first = items[0] if items else {"verdict": "ambiguous", "model_verdict": "none", "evidence": {}}
        rows.append({
            "scenario": scenario, "id": case["id"], "expected": case["expected"],
            "predicted": first["verdict"], "model_verdict": first.get("model_verdict"),
            "downgraded": first.get("evidence", {}).get("downgraded", False),
            "n_requests": len(items), "seconds": round(elapsed, 2), "items": items,
        })
        print(f"  {case['id']:<8} expected={case['expected']:<9} predicted={first['verdict']:<9} "
              f"{'(downgraded) ' if rows[-1]['downgraded'] else ''}{elapsed:5.1f}s", flush=True)
    return rows


def metrics(rows: list[dict]) -> dict:
    tp = sum(r["expected"] == "extra" and r["predicted"] == "extra" for r in rows)
    fp = sum(r["expected"] != "extra" and r["predicted"] == "extra" for r in rows)
    fn = sum(r["expected"] == "extra" and r["predicted"] != "extra" for r in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": sum(r["expected"] == r["predicted"] for r in rows) / len(rows),
        "extra_precision": precision,
        "extra_recall": recall,
        "extra_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "false_extra": fp,
        "downgraded": sum(r["downgraded"] for r in rows),
        "avg_seconds": sum(r["seconds"] for r in rows) / len(rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="baseline")
    parser.add_argument("--base-url")
    args = parser.parse_args()

    config = llm.load_config()
    if args.base_url:
        config["base_url"] = args.base_url

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary = {}
    for model in args.models.split(","):
        print(f"\n== {model}")
        rows = run_model(model, config)
        summary[model] = metrics(rows)
        out = RESULTS / f"{stamp}-{model.replace(':', '_')}.json"
        out.write_text(json.dumps({"model": model, "prompt_version": classifier.PROMPT_VERSION,
                                   "base_url": config["base_url"], "rows": rows}, indent=2),
                       encoding="utf-8")

    print(f"\n{'model':<16}{'acc':>6}{'prec':>7}{'rec':>7}{'f1':>7}{'falseX':>8}{'downg':>7}{'sec':>7}")
    for model, m in summary.items():
        print(f"{model:<16}{m['accuracy']:>6.0%}{m['extra_precision']:>7.0%}{m['extra_recall']:>7.0%}"
              f"{m['extra_f1']:>7.0%}{m['false_extra']:>8}{m['downgraded']:>7}{m['avg_seconds']:>7.1f}")


if __name__ == "__main__":
    main()
