import os
import subprocess
import time
import sys

def main():
    models_to_test = [
        "deepseek/deepseek-chat",
        "qwen/qwen-2.5-72b-instruct",
        "openai/gpt-4o-mini",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-small-3.1-24b-instruct"
    ]

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    hf_token = os.environ.get("HF_TOKEN_LIVE", "")

    output_lines = []
    output_lines.append("=======================================================================")
    output_lines.append("CODE REVIEW OPENENV - LIVE HUGGING FACE INFERENCE BENCHMARK TESTING")
    output_lines.append("=======================================================================\n")
    output_lines.append(f"Target Environment: https://ksiki-code-test.hf.space")
    output_lines.append(f"Target LLM Gateway: https://openrouter.ai/api/v1\n")

    print("Executing tests sequentially against Live HF Space...")

    for model in models_to_test:
        print(f"[{model}] Starting inference...")
        
        env_vars = os.environ.copy()
        env_vars["API_BASE_URL"] = "https://openrouter.ai/api/v1"
        env_vars["MODEL_NAME"] = model
        env_vars["HF_TOKEN"] = api_key  # This goes to the LLM (OpenRouter)
        env_vars["ENV_BASE_URL"] = "https://ksiki-code-test.hf.space"
        env_vars["TASK_IDS"] = "easy,medium,hard"

        # Give the HF space a moment to guarantee clean reset
        time.sleep(2)

        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "code-review-env/inference.py"],
                env=env_vars,
                capture_output=True,
                text=True,
                timeout=1800 # 30 mins per model
            )
            elapsed = time.time() - start_time
            print(f"[{model}] Completed in {elapsed:.1f}s.")
            
            output_lines.append(f"\n=======================================================================")
            output_lines.append(f"--- RUNNING ELITE EXTREME TEST ON MODEL: {model} ---")
            output_lines.append(f"--- Execution Time: {elapsed:.2f}s ---")
            output_lines.append("--- STDOUT (Environment Steps & Actions) ---")
            output_lines.append(result.stdout)
            output_lines.append("--- STDERR (Telemetry, Confidence & Parsing Status) ---")
            output_lines.append(result.stderr)

        except subprocess.TimeoutExpired as e:
            print(f"[{model}] TIMEOUT after {time.time() - start_time:.1f}s.")
            output_lines.append(f"\n[CRITICAL ERROR] {model} timed out.")
        except Exception as e:
            print(f"[{model}] ERROR: {str(e)}")
            output_lines.append(f"\n[CRITICAL ERROR] {model} threw exception: {str(e)}")

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

    with open("final test-2last.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print("Done! Check final test-2last.txt")

if __name__ == "__main__":
    main()
