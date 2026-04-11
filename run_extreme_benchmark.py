import os
import subprocess
import time
import sys

def main():
    print("Starting background server...")
    # Start the fast api server
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "7860"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(4)  # Wait for server to start

    models_to_test = [
        "openai/gpt-4o-mini",
        # Adding a stronger model for extreme competition since gpt-4o-mini alone might fail or be weak
        "mistralai/mistral-small-3.1-24b-instruct" 
    ]
    
    api_key = "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"

    output_lines = []
    output_lines.append("=======================================================================")
    output_lines.append("CODE REVIEW OPENENV - EXTREME INTERNATIONAL BENCHMARK TESTING")
    output_lines.append("=======================================================================\n")

    for model in models_to_test:
        output_lines.append(f"--- RUNNING ELITE EXTREME TEST ON MODEL: {model} ---")
        env_vars = os.environ.copy()
        env_vars["API_BASE_URL"] = "https://openrouter.ai/api/v1"
        env_vars["MODEL_NAME"] = model
        env_vars["HF_TOKEN"] = api_key
        env_vars["TASK_IDS"] = "easy,medium,hard"

        print(f"Benchmarking {model}...")
        
        # Run inference and capture both stdout and stderr (since we added stderr confidence tracking)
        try:
            result = subprocess.run(
                [sys.executable, "code-review-env/inference.py"],
                env=env_vars,
                capture_output=True,
                text=True,
                timeout=600 # 10 minutes timeout per model
            )
            # We want to capture both streams in order
            output_lines.append("--- STDOUT (Environment Steps & Actions) ---")
            output_lines.append(result.stdout)
            output_lines.append("--- STDERR (Telemetry, Confidence & Parsing Status) ---")
            output_lines.append(result.stderr)
            
        except subprocess.TimeoutExpired:
            output_lines.append(f"\n[ERROR] Model {model} timed out after 600 seconds.")

    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()

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

    with open("latest-test.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
        
    print("Done! Check latest-test.txt")

if __name__ == "__main__":
    main()
