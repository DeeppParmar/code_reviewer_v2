import os
import subprocess
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_model_test(model_name, port_index):
    port = 7860 + port_index
    print(f"[{model_name}] Starting server on port {port}...")
    
    # Start an independent server for this process to avoid state collisions
    # The root server.py loads app from env.environment via code-review-env/server.py if we are in code_reviewer_v2 root.
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(5)  # Wait for uvicorn to settle
    print(f"[{model_name}] Server running on port {port}. Starting inference...")
    
    api_key = "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"
    
    env_vars = os.environ.copy()
    env_vars["API_BASE_URL"] = "https://openrouter.ai/api/v1"
    env_vars["MODEL_NAME"] = model_name
    env_vars["HF_TOKEN"] = api_key
    env_vars["TASK_IDS"] = "easy,medium,hard"
    env_vars["ENV_BASE_URL"] = f"http://127.0.0.1:{port}"
    
    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, "code-review-env/inference.py"],
            env=env_vars,
            capture_output=True,
            text=True,
            timeout=1800 # 30 mins per model max
        )
        elapsed = time.time() - start_time
        
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        
        print(f"[{model_name}] Completed in {elapsed:.1f}s.")
        return {
            "model": model_name,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": None,
            "elapsed": elapsed
        }
    except subprocess.TimeoutExpired as e:
        server_proc.terminate()
        print(f"[{model_name}] TIMEOUT after {time.time() - start_time:.1f}s.")
        return {
            "model": model_name,
            "stdout": "",
            "stderr": "",
            "error": "TimeoutExpired",
            "elapsed": time.time() - start_time
        }
    except Exception as e:
        server_proc.terminate()
        print(f"[{model_name}] ERROR: {str(e)}")
        return {
            "model": model_name,
            "stdout": "",
            "stderr": "",
            "error": str(e),
            "elapsed": time.time() - start_time
        }

def main():
    models_to_test = [
        "openai/gpt-4o-mini",
        "mistralai/mistral-small-3.1-24b-instruct"
    ]
    
    output_lines = []
    output_lines.append("=======================================================================")
    output_lines.append("CODE REVIEW OPENENV - CONCURRENT MASS INTERNATIONAL BENCHMARK TESTING")
    output_lines.append("=======================================================================\n")
    
    # We will use max workers 2
    print("Executing tests concurrently...")
    results = []
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for i, model in enumerate(models_to_test):
            futures.append(executor.submit(run_model_test, model, i + 1))
            
        for future in as_completed(futures):
            results.append(future.result())
            
    # Process results sequentially into file
    for res in results:
        model = res["model"]
        output_lines.append(f"\n=======================================================================")
        output_lines.append(f"--- RUNNING ELITE EXTREME TEST ON MODEL: {model} ---")
        output_lines.append(f"--- Execution Time: {res['elapsed']:.2f}s ---")
        
        if res["error"]:
            output_lines.append(f"[CRITICAL ERROR] {res['error']}")
        else:
            output_lines.append("--- STDOUT (Environment Steps & Actions) ---")
            output_lines.append(res['stdout'])
            output_lines.append("--- STDERR (Telemetry, Confidence & Parsing Status) ---")
            output_lines.append(res['stderr'])

    # Part 2: Explanation of how it works as requested by user
    explanation = """
=======================================================================
HOW THE GRADING, DECISION, AND CONFIDENCE LOGIC WORKS (Detailed Math)
=======================================================================

1. THE MULTI-FILE CODE REVIEW ARCHITECTURE:
An agent is presented with PRs. The Hard Task spans 3 distinct files 
(`crypto_service.py`, `config_loader.py`, `audit_logger.py`). The agent 
must use `inspect_file` and `inspect_lines` to traverse the repository, 
understand cross-file dependencies (e.g. secret keys generated in one file 
and misused in another), and find 6 major/critical bugs while ignoring 1 
deliberately planted Red Herring trap.

2. BUG MATCHING & DECISIONS:
When an agent submits an `add_comment` action, the environment:
- Proximity Check: Verifies the provided line_number is within +/- 5 lines 
  of a confirmed Ground Truth Bug.
- Attribute Check: Exact match required for `severity` and `category`.
- Semantic Explanation Tiering: The message must contain specific technical 
  keywords to prove the agent understands *why* it's broken, not just *where*. 
  Higher explanation tiers grant full marks, missing semantic keywords results 
  in a -0.10 penalty.

3. CONFIDENCE CALIBRATION & MODIFIER:
If the model provides a "confidence" field (0-100), the system evaluates the 
Agent's self-awareness:
- If confidence >= 80% and the comment is CORRECT -> +0.05 calibration bonus.
- If confidence >= 80% and the comment is WRONG -> -0.10 heavy penalty.
- The episode tracks `calibration_events` and calculates a final calibration_score 
  (printed in STDERR) based on proper probabilistic alignment.

4. FALSE POSITIVES & THE RED HERRING:
- Each incorrect comment generates a False Positive (FP). FPs are weighted 
  by severity: Critical=3, Major=2, Minor=1, Nit=0.5.
- The Red Herring is a deliberately suspicious block of code (try: ... except: pass 
  in a backoff loop). If an agent flags it, they trigger a catastrophic penalty of -0.20,
  heavily crashing their precision score.

5. FINAL SCORE CALCULATION (Weighted F1 Grader):
The formula strictly limits ceiling inflation:
- Weighted True Positives (WTP) = sum of weights of correctly found bugs.
- Weighted False Positives (WFP) = sum of weights of false positive comments.
- Weighted False Negatives (WFN) = sum of weights of bugs completely missed.

Precision (P) = WTP / (WTP + WFP)
Recall (R) = WTP / (WTP + WFN)
F1 Score = 2 * (P * R) / (P + R)

Final Output = F1 Score + Efficiency Bonus (if done in few steps) + Calibration Modifier.
Values strictly clamped to max 0.999 to prevent gamification. No LLM hits 1.0!
"""
    output_lines.append(explanation)

    with open("logs-con-gpt.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print("Done! Check logs-con-gpt.txt")

if __name__ == "__main__":
    main()
