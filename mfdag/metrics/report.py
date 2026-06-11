from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from mfdag.metrics.cohort_metrics import compute_cohort_metrics
from mfdag.metrics.efficiency import compare_efficiency, load_efficiency
from mfdag.metrics.propagation import compute_propagation_metrics
from mfdag.utils.io import read_json, write_json


def evaluate_run(run_dir: Path, baseline_dirs: List[Path] | None = None) -> Dict[str, Any]:
    run_dir = Path(run_dir)
    efficiency = load_efficiency(run_dir)
    propagation = compute_propagation_metrics(run_dir)
    cohort = compute_cohort_metrics(run_dir)
    config = {}
    if (run_dir / "config.yaml").exists():
        import yaml

        with open(run_dir / "config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

    summary = read_json(run_dir / "run_summary.json")
    metrics = {
        "run_id": run_dir.name,
        "method": summary.get("method"),
        "efficiency_metrics": efficiency,
        "propagation_metrics": propagation,
        "cohort_metrics": cohort,
    }

    metrics_dir = run_dir / "metrics"
    metrics_dir.mkdir(exist_ok=True)
    write_json(metrics_dir / "efficiency_metrics.json", efficiency)
    write_json(metrics_dir / "propagation_metrics.json", propagation)
    write_json(metrics_dir / "cohort_metrics.json", cohort)
    write_json(metrics_dir / "metrics_summary.json", metrics)

    baseline_eff = []
    if baseline_dirs:
        for bdir in baseline_dirs:
            if (bdir / "run_summary.json").exists():
                baseline_eff.append(load_efficiency(bdir))
    if summary.get("method") == "mfdag":
        metrics["comparison"] = compare_efficiency(baseline_eff, efficiency)

    report_lines = [
        "# MF-DAG Blacksky Experiment Report",
        "",
        "## Configuration",
        f"- Feed: {config.get('data', {}).get('feed_name', 'Blacksky')}",
        f"- Method: {summary.get('method')}",
        f"- Threads processed: {summary.get('threads_processed')}",
        f"- Agents: {summary.get('agents', 'N/A')}",
        f"- Cohorts: {summary.get('cohorts', 'N/A')}",
        "",
        "## Efficiency",
        f"- LLM calls: {efficiency.get('llm_calls')}",
        f"- Total tokens: {efficiency.get('total_tokens')}",
        f"- Runtime (s): {efficiency.get('runtime_s')}",
        "",
        "## Propagation Metrics",
        f"- Continuation size MAE: {propagation.get('continuation_size_mae')}",
        f"- User F1 mean: {propagation.get('user_f1_mean')}",
        f"- User Recall mean: {propagation.get('user_recall_mean')}",
        "",
        "## Cohort Metrics",
        f"- JS distance mean: {cohort.get('cohort_js_distance_mean')}",
        f"- KL distance mean: {cohort.get('cohort_kl_distance_mean')}",
    ]
    if metrics.get("comparison"):
        report_lines.extend(
            [
                "",
                "## MF-DAG vs Baselines",
                f"- LLM call reduction ratio: {metrics['comparison'].get('llm_call_reduction_ratio')}",
                f"- Token reduction ratio: {metrics['comparison'].get('token_reduction_ratio')}",
            ]
        )
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return metrics
