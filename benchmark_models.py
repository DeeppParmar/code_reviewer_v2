"""Multi-model benchmark orchestrator for Code Review OpenEnv.

Runs the inference pipeline against multiple frontier LLMs and records
real results to a CSV log.  Never simulates or fabricates data — if a
model hits API quota limits the run is logged as "quota_exhausted".
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODELS: List[str] = [
    "deepseek-ai/DeepSeek-Coder-V2-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3-70b-chat-hf",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "google/gemma-2-27b-it",
]

TASK_IDS = ["easy", "medium", "hard"]
RESULTS_CSV = "benchmark_results.csv"
RESULTS_JSON = "benchmark_results.json"
SUBPROCESS_TIMEOUT_S = 300  # 5 minutes per model run


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    task_id: str
    score: float
    steps: int
    success: bool
    rewards: List[float] = field(default_factory=list)
    quota_exhausted: bool = False


@dataclass
class ModelResult:
    model: str
    timestamp: str
    tasks: Dict[str, TaskResult] = field(default_factory=dict)
    avg_score: float = 0.0
    status: str = "completed"  # completed | quota_exhausted | timeout | error
    error_msg: Optional[str] = None


# ---------------------------------------------------------------------------
# Stdout parser — extracts [START]/[STEP]/[END] structured logs
# ---------------------------------------------------------------------------

def parse_inference_stdout(stdout: str) -> List[TaskResult]:
    """Parse real inference stdout into per-task results."""
    results: List[TaskResult] = []
    current_task: Optional[str] = None
    current_rewards: List[float] = []
    quota_hit = False

    for line in stdout.splitlines():
        line = line.strip()

        if line.startswith("[START]"):
            m = re.search(r"task=(\w+)", line)
            current_task = m.group(1) if m else "unknown"
            current_rewards = []
            quota_hit = False

        elif line.startswith("[STEP]"):
            rm = re.search(r"reward=([\d.]+)", line)
            if rm:
                current_rewards.append(float(rm.group(1)))
            if "402" in line or "depleted" in line.lower():
                quota_hit = True

        elif line.startswith("[END]") and current_task:
            sm = re.search(r"score=([\d.]+)", line)
            stm = re.search(r"steps=(\d+)", line)
            sucm = re.search(r"success=(true|false)", line)

            score = float(sm.group(1)) if sm else 0.0
            steps = int(stm.group(1)) if stm else 0
            success = (sucm.group(1) == "true") if sucm else False

            results.append(TaskResult(
                task_id=current_task,
                score=score,
                steps=steps,
                success=success,
                rewards=current_rewards[:],
                quota_exhausted=quota_hit,
            ))
            current_task = None

    return results


# ---------------------------------------------------------------------------
# Single model runner
# ---------------------------------------------------------------------------

def run_single_model(model: str) -> ModelResult:
    """Run inference.py as a subprocess for a single model.  Never fabricates."""
    ts = datetime.now(timezone.utc).isoformat()
    print(f"\n{'='*60}")
    print(f"[BENCH] {model}")
    print(f"[BENCH] Started at {ts}")
    print(f"{'='*60}")

    env = os.environ.copy()
    env["HF_MODEL"] = model
    env["REVIEW_STRATEGY"] = "llm"
    env["TASK_IDS"] = ",".join(TASK_IDS)

    try:
        proc = subprocess.run(
            [sys.executable, "code-review-env/inference.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_S,
        )
        stdout = proc.stdout
        stderr = proc.stderr

        task_results = parse_inference_stdout(stdout)

        result = ModelResult(model=model, timestamp=ts)
        any_quota = False

        for tr in task_results:
            result.tasks[tr.task_id] = tr
            if tr.quota_exhausted:
                any_quota = True

        if task_results:
            result.avg_score = sum(t.score for t in task_results) / len(task_results)
        else:
            result.avg_score = 0.0

        if any_quota:
            result.status = "quota_exhausted"
            print(f"[BENCH] WARNING: API quota was hit during run -- results are partial/fallback")
        else:
            result.status = "completed"

        for tid, tr in result.tasks.items():
            print(f"[BENCH]   {tid}: score={tr.score:.3f}  steps={tr.steps}  quota_hit={tr.quota_exhausted}")

        print(f"[BENCH] Average score: {result.avg_score:.3f}  Status: {result.status}")
        return result

    except subprocess.TimeoutExpired:
        print(f"[BENCH] TIMEOUT after {SUBPROCESS_TIMEOUT_S}s")
        return ModelResult(model=model, timestamp=ts, status="timeout", error_msg="subprocess timeout")

    except Exception as e:
        print(f"[BENCH] ERROR: {e}")
        return ModelResult(model=model, timestamp=ts, status="error", error_msg=str(e))


# ---------------------------------------------------------------------------
# CSV / JSON persistence
# ---------------------------------------------------------------------------

def save_results(results: List[ModelResult]) -> None:
    """Write results to both CSV and JSON — append-safe."""

    # JSON (full fidelity)
    json_data = []
    for r in results:
        entry = {
            "model": r.model,
            "timestamp": r.timestamp,
            "status": r.status,
            "avg_score": round(r.avg_score, 4),
            "error": r.error_msg,
            "tasks": {},
        }
        for tid, tr in r.tasks.items():
            entry["tasks"][tid] = {
                "score": tr.score,
                "steps": tr.steps,
                "success": tr.success,
                "rewards": tr.rewards,
                "quota_exhausted": tr.quota_exhausted,
            }
        json_data.append(entry)

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    # CSV (flat, human-scannable)
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "task", "score", "steps", "success", "quota_exhausted", "status", "timestamp"])
        for r in results:
            if r.tasks:
                for tid, tr in r.tasks.items():
                    writer.writerow([r.model, tid, f"{tr.score:.3f}", tr.steps, tr.success, tr.quota_exhausted, r.status, r.timestamp])
            else:
                writer.writerow([r.model, "-", "0.000", 0, False, False, r.status, r.timestamp])

    print(f"\n[BENCH] Results saved to {RESULTS_CSV} and {RESULTS_JSON}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Code Review OpenEnv — Multi-Model Benchmark")
    print(f"  Models: {len(MODELS)}  |  Tasks: {TASK_IDS}")
    print("  Mode: LIVE ONLY — no simulated data")
    print("=" * 60)

    all_results: List[ModelResult] = []

    for i, model in enumerate(MODELS):
        result = run_single_model(model)
        all_results.append(result)
        save_results(all_results)  # progressive save after each model

        # Cooldown between models to respect rate limits
        if i < len(MODELS) - 1:
            cooldown = 15
            print(f"[BENCH] Cooling down {cooldown}s before next model...")
            time.sleep(cooldown)

    # Final summary table
    print("\n" + "=" * 60)
    print("  FINAL RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Model':<45} {'Avg Score':>10} {'Status':>16}")
    print("-" * 71)
    for r in all_results:
        print(f"{r.model:<45} {r.avg_score:>10.3f} {r.status:>16}")
    print("=" * 60)


if __name__ == "__main__":
    main()
