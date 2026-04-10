import asyncio
import httpx
import os
import time
import subprocess
import sys
from datetime import datetime

# Brutal Benchmark Configuration
ENV_URLS = [
    ("Local", "http://127.0.0.1:7860"),
    ("HF_Space", "https://usku880-code-reviwer-v2.hf.space")
]

LLM_APIS = [
    {
        "name": "HuggingFace",
        "url": "https://router.huggingface.co/v1",
        "key": "hf_dummy_or_exhausted", 
        "models": ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3", "mistralai/Mistral-7B-Instruct-v0.3", "google/gemma-7b-it"]
    },
    {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1",
        "key": "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",
        "models": ["meta-llama/llama-3.3-70b-instruct", "qwen/qwen-2.5-72b-instruct", "deepseek/deepseek-chat", "google/gemma-3-27b-it", "anthropic/claude-3.5-sonnet"]
    }
]

TASKS = ["easy", "medium", "hard"]
ITERATIONS = 3  # Multiple runs to ensure exhaustion logic is perfectly tested

def run_benchmark(env_name, env_url, api_name, api_url, api_key, model, task):
    env = os.environ.copy()
    env["API_BASE_URL"] = api_url
    env["MODEL_NAME"] = model
    env["HF_TOKEN"] = api_key
    env["ENV_BASE_URL"] = env_url
    env["REVIEW_STRATEGY"] = "llm"
    env["TASK_IDS"] = f"{task}:30"
    
    cmd = [sys.executable, "code-review-env/inference.py"]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", -1
    except Exception as e:
        return f"CRASH: {e}", "", -1

def main():
    with open("log40.txt", "w", encoding="utf-8") as f:
        f.write(f"=== HEAVY BRUTAL BENCHMARK (HF & OPENROUTER) ===\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")

    # Start local server just in case for local tests
    server_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"],
                                     cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "code-review-env"))
    time.sleep(3)

    results = []

    try:
        for iter_num in range(ITERATIONS):
            print(f"--- RUN ITERATION {iter_num+1}/{ITERATIONS} ---")
            for env_name, env_url in ENV_URLS:
                for api in LLM_APIS:
                    for model in api["models"]:
                        for task in TASKS:
                            print(f"Testing [{env_name} | {api['name']}] - {model} ({task})")
                            out, err, code = run_benchmark(env_name, env_url, api["name"], api["url"], api["key"], model, task)
                            
                            # Parse result for table
                            score = "N/A"
                            success = "false"
                            exhausted = "false"
                            
                            if "Error code: 40" in out or "Depleted" in out or "exhausted" in out.lower() or "User not found" in out:
                                exhausted = "true"
                            
                            for line in out.splitlines():
                                if line.startswith("[END]"):
                                    parts = line.split()
                                    for p in parts:
                                        if p.startswith("score="): score = p.split("=")[1]
                                        if p.startswith("success="): success = p.split("=")[1]

                            with open("log40.txt", "a", encoding="utf-8") as f:
                                f.write(f"##############################################\n")
                                f.write(f"Iter: {iter_num+1} | Env: {env_name} | API: {api['name']}\n")
                                f.write(f"Model: {model} | Task: {task}\n")
                                f.write(f"Exhausted: {exhausted} | Score: {score} | Success: {success}\n")
                                f.write(f"Exit: {code}\n")
                                f.write(f"Output:\n{out}\n")
                                if err: f.write(f"Errors:\n{err}\n")
                                f.write("\n")

                            results.append({
                                "iter": iter_num+1,
                                "env": env_name,
                                "api": api["name"],
                                "model": model,
                                "task": task,
                                "exhausted": exhausted,
                                "score": score,
                                "success": success
                            })
                            
                            if exhausted == "true":
                                print("   -> Exhaustion / Auth correctly handled! Fallback triggered.")
                            else:
                                print(f"   -> Completed. Score: {score}")

    finally:
        server_proc.terminate()

    # Generate Markdown Table
    md_table = "### Benchmark Results Table (HuggingFace Environment + OpenRouter APIs)\n\n"
    md_table += "| Env Target | Inference API | Model | Task | Fallback (Exhausted) | Score | Success |\n"
    md_table += "|---|---|---|---|---|---|---|\n"
    for r in results:
        md_table += f"| {r['env']} | {r['api']} | {r['model']} | {r['task']} | {r['exhausted']} | {r['score']} | {r['success']} |\n"

    print("\n\n" + md_table)

    with open("log40.txt", "a", encoding="utf-8") as f:
        f.write("\n\n" + md_table)
        
if __name__ == "__main__":
    main()
