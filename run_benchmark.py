"""Run benchmark with OpenRouter API.

Usage: python run_benchmark.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

# OpenRouter API configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Models to benchmark via OpenRouter
MODELS = [
    "deepseek/deepseek-chat",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemma-3-27b-it",
]

TASK_IDS = ["easy", "medium", "hard"]


def run_model(model_name: str, server_proc) -> dict:
    """Run inference for one model."""
    print(f"\n{'='*60}")
    print(f"[RUN] Model: {model_name}")
    print(f"{'='*60}")

    env = os.environ.copy()
    env["API_BASE_URL"] = OPENROUTER_BASE_URL
    env["MODEL_NAME"] = model_name
    env["HF_TOKEN"] = OPENROUTER_API_KEY
    env["ENV_BASE_URL"] = "http://127.0.0.1:7860"
    env["REVIEW_STRATEGY"] = "llm"
    env["TASK_IDS"] = ",".join(TASK_IDS)
    env["TASK_TIMEOUT_S"] = "120"

    try:
        proc = subprocess.run(
            [sys.executable, "code-review-env/inference.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        stdout = proc.stdout
        stderr = proc.stderr

        if stderr:
            print(f"[STDERR] {stderr[:500]}")

        print(stdout)

        return {
            "model": model_name,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": proc.returncode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {model_name}")
        return {
            "model": model_name,
            "stdout": "",
            "stderr": "TIMEOUT",
            "returncode": -1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"[ERROR] {model_name}: {e}")
        return {
            "model": model_name,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def main():
    print("=" * 60)
    print("  Code Review OpenEnv — Benchmark with OpenRouter API")
    print(f"  Models: {len(MODELS)}")
    print(f"  Tasks: {TASK_IDS}")
    print("=" * 60)

    # Start the server
    print("\n[SETUP] Starting environment server...")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"],
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "code-review-env"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)  # Wait for server to start

    # Check server health
    import httpx
    try:
        r = httpx.get("http://127.0.0.1:7860/health", timeout=5)
        print(f"[SETUP] Server health: {r.json()}")
    except Exception as e:
        print(f"[ERROR] Server not responding: {e}")
        server_proc.terminate()
        return

    all_results = []
    all_logs = []

    for i, model in enumerate(MODELS):
        result = run_model(model, server_proc)
        all_results.append(result)
        all_logs.append(result["stdout"])

        # Save progressive results
        with open("benchmark_run_log.txt", "w", encoding="utf-8") as f:
            for r in all_results:
                f.write(f"\n{'='*60}\n")
                f.write(f"Model: {r['model']}\n")
                f.write(f"Timestamp: {r['timestamp']}\n")
                f.write(f"Return code: {r['returncode']}\n")
                f.write(f"STDOUT:\n{r['stdout']}\n")
                if r['stderr']:
                    f.write(f"STDERR:\n{r['stderr'][:500]}\n")

        # Cooldown between models
        if i < len(MODELS) - 1:
            print(f"[COOLDOWN] 10s before next model...")
            time.sleep(10)

    # Write final results
    with open("result.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  Code Review OpenEnv — Benchmark Results\n")
        f.write(f"  Date: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("=" * 60 + "\n\n")

        for r in all_results:
            f.write(f"\n{'='*60}\n")
            f.write(f"Model: {r['model']}\n")
            f.write(f"Timestamp: {r['timestamp']}\n")
            f.write(f"Return code: {r['returncode']}\n")
            f.write(f"\nOutput:\n{r['stdout']}\n")

    print(f"\n[DONE] Results saved to result.txt and benchmark_run_log.txt")

    # Shutdown server
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()

    print("[DONE] Server stopped.")


if __name__ == "__main__":
    main()
