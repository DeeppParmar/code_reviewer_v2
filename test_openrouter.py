import os
import subprocess
import sys
from datetime import datetime

# OpenRouter Heavy Stress Test configuration
API_BASE = "https://openrouter.ai/api/v1"
TOKEN = "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"
ENV_URL = "https://usku880-code-reviwer-v2.hf.space"

MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
    "google/gemma-3-27b-it",
    "anthropic/claude-3.5-sonnet"
]
TASKS = ["easy", "medium", "hard"]
STRESS_ITERATIONS = 3  # heavy iteration over exhausted quotas

def main():
    print(f"==========================================================================")
    print(f"HEAVY STRESS TESTING: OPEN ROUTER API")
    print(f"==========================================================================")
    
    env = os.environ.copy()
    env["ENV_BASE_URL"] = ENV_URL
    env["API_BASE_URL"] = API_BASE
    env["HF_TOKEN"] = TOKEN
    env["REVIEW_STRATEGY"] = "llm" 
    
    for iteration in range(STRESS_ITERATIONS):
        print(f"\n==========================================================================")
        print(f"  [STRESS ITERATION {iteration + 1}/{STRESS_ITERATIONS}]")
        print(f"==========================================================================")
        
        for model in MODELS:
            for task in TASKS:
                env["MODEL_NAME"] = model
                env["TASK_IDS"] = task
                print(f"Testing Model: {model} | Task: {task}")
                
                cmd = [sys.executable, "code-review-env/inference.py"]
                proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                print(proc.stdout)
                if proc.stderr:
                    print("Errors:", proc.stderr)

if __name__ == "__main__":
    main()
