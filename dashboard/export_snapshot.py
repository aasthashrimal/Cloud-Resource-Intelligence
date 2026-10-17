"""Build a small dashboard snapshot from saved analysis.ipynb outputs.

Run after saving a successful Colab notebook. This reads the notebook's
structured table outputs; it does not load the raw trace or retrain models.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK = ROOT / "analysis.ipynb"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "snapshot.json"
TABLE_MIME = "application/vnd.microsoft.datawrangler.viewer.v0+json"


def _text(value):
    return "".join(value) if isinstance(value, list) else str(value)


def _streams(cell):
    return "\n".join(_text(out.get("text", "")) for out in cell.get("outputs", [])
                     if out.get("output_type") == "stream")


def _convert(raw, kind):
    if raw is None or str(raw).lower() in {"", "none", "nan"}:
        return None
    if kind == "integer":
        return int(raw)
    if kind == "float":
        return float(raw)
    if kind == "boolean":
        return str(raw).lower() in {"true", "1"}
    return str(raw)


def _tables(notebook):
    for cell in notebook["cells"]:
        for output in cell.get("outputs", []):
            table = output.get("data", {}).get(TABLE_MIME)
            if not table:
                continue
            columns = table["columns"]
            names = [column["name"] for column in columns]
            records = []
            for row in table["rows"]:
                if len(row) != len(columns):
                    raise ValueError("Malformed saved table: column/row length mismatch")
                records.append({("label" if name == "index" else name):
                                _convert(value, column.get("type"))
                                for name, value, column in zip(names, row, columns)
                                if name != "index" or column.get("type") == "string"})
            yield set(names), records


def _table(tables, required):
    matches = [(len(columns - required), rows) for columns, rows in tables
               if required <= columns]
    matches.sort(key=lambda item: item[0])
    if not matches or not matches[0][1] or (len(matches) > 1 and matches[0][0] == matches[1][0]):
        raise ValueError(f"Expected one populated saved table with {sorted(required)}; "
                         "save a complete Colab run before exporting")
    return matches[0][1]


def _match(pattern, text, cast=str):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Missing saved run output matching {pattern!r}")
    return cast(match.group(1))


def build_snapshot(notebook_path: Path) -> dict:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    counts = [cell.get("execution_count") for cell in code_cells]
    if not counts or counts != list(range(1, len(counts) + 1)):
        raise ValueError("Saved notebook is not a sequential run from cell 1")
    if any(output.get("output_type") == "error" for cell in code_cells
           for output in cell.get("outputs", [])):
        raise ValueError("Saved notebook contains a cell error")

    tables = list(_tables(notebook))
    streams = "\n".join(_streams(cell) for cell in code_cells)
    setup = _streams(code_cells[0])
    quality_text = _streams(code_cells[3])
    try:
        quality = json.loads(quality_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Missing saved Module 2 cleaning report") from exc

    validation = _table(tables, {"resource", "model", "fit_seconds", "MAE", "RMSE", "R2"})
    test = _table(tables, {"resource", "model", "MAE", "RMSE", "R2"})
    baseline = _table(tables, {"policy", "resource", "unused_resource_seconds",
                               "unmet_resource_seconds", "unmet_fraction"})
    scenarios = _table(tables, {"scenario", "policy", "resource", "unmet_fraction",
                                "pool_saturation_fraction"})
    if len(baseline) != 6 or len(scenarios) != 24:
        raise ValueError("The policy or scenario output is incomplete")
    for row in baseline + scenarios:
        for name in ("utilization", "unmet_fraction", "overloaded_task_fraction",
                     "pool_saturation_fraction"):
            value = row[name]
            if value is None or not 0 <= value <= 1:
                raise ValueError(f"Invalid saved {name}")
    for row in baseline:
        other = next((item for item in scenarios
                      if item["scenario"] == "original"
                      and item["policy"] == row["policy"]
                      and item["resource"] == row["resource"]), None)
        if other is None or abs(row["unmet_fraction"] - other["unmet_fraction"]) > 1e-8:
            raise ValueError("Saved baseline and original scenario disagree")

    selected_models = ast.literal_eval(_match(r"Selected by validation MAE: (\{[^\n]+\})",
                                              streams))
    selected_classifier = _match(r"Selected by validation macro-F1: ([^\n]+)", streams)
    return {
        "schema_version": 1,
        "source": "saved outputs in analysis.ipynb",
        "run": {
            "code_cells": len(code_cells),
            "shards": _match(r"Shards: (\d+)", setup, int),
            "source_rows": _match(r"Rows: ([\d,]+)", setup, lambda x: int(x.replace(",", ""))),
            "hours": _match(r"Hours: ([\d.]+)", setup, float),
            "eligible_pairs": _match(r"Loaded Module 2: (\d+) eligible pairs", streams, int),
            "test_intervals": _match(r"test rows: (\d+)", streams, int),
            "project_mb": _match(r"Project data/artifacts: ([\d.]+) MB\nConclusion:",
                                 streams, float),
            "horizon_seconds": 300,
        },
        "quality": quality,
        "split_counts": _table(tables, {"split", "eligible pairs"}),
        "clustering": {
            "scores": _table(tables, {"k", "silhouette", "smallest_scoring_cluster"}),
            "profiles": _table(tables, {"cluster", "train_rows", "cpu_now", "memory_now"}),
        },
        "forecasting": {
            "selected_models": selected_models,
            "validation": validation,
            "test": test,
        },
        "risk": {
            "selected_model": selected_classifier,
            "class_counts": _table(tables, {"train", "validation", "test"}),
            "validation": _table(tables, {"model", "macro_F1", "recall_both"}),
            "test_macro_f1": _match(r"Test macro-F1 - selected: ([\d.]+)", streams, float),
            "majority_test_macro_f1": _match(r"\| majority: ([\d.]+)", streams, float),
        },
        "allocation": {
            "margin": _match(r"Frozen forest margin: ([\d.]+)", streams, float),
            "margin_search": _table(tables, {"margin", "risk_feasible",
                                             "cpu_utilization", "memory_utilization"}),
            "baseline": baseline,
            "scenarios": scenarios,
        },
        "limitations": [
            "First six task_usage shards and an identity-hash sample, not the full trace.",
            "CPU and memory are normalized usage units, not physical cores or GB.",
            "Observed usage is treated as demand; unconstrained demand is unknown.",
            "Allocation pools and contention are simulated for the sampled cohort.",
            "Risk classes are allocation-derived proxy labels, not verified failures.",
            "No machine placement, latency, SLA, production cost, or real savings are measured.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    snapshot = build_snapshot(args.notebook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(f"Saved {args.output} ({args.output.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
