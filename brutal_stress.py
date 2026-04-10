import asyncio
import httpx
import time
import random
from typing import Dict, Any

SERVER_URL = "http://127.0.0.1:7860"

def generate_random_action() -> Dict[str, Any]:
    operations = ["add_comment", "approve", "request_changes", "inspect_file", "inspect_lines", "done", "invalid_op"]
    op = random.choice(operations)
    
    # Boundary/glitch values
    line_nums = [-1, 0, 1, 100, 999999, None]
    severities = ["critical", "major", "minor", "nit", "invalid", "", None]
    categories = ["bug", "security", "performance", "style", "invalid", "", None]
    confidences = [-10, 0, 50, 100, 150, "string", None]
    
    action = {"operation": op}
    
    if op == "add_comment":
        action["line_number"] = random.choice(line_nums)
        action["severity"] = random.choice(severities)
        action["category"] = random.choice(categories)
        action["message"] = f"Random glitch test {random.random()} \x00 unicode 🎉"
        action["confidence"] = random.choice(confidences)
        # Randomly omit keys
        if random.random() < 0.1: del action["line_number"]
    elif op in ["approve", "request_changes"]:
        action["summary"] = f"Glitch summary {random.random()}"
        if random.random() < 0.1: del action["summary"]
    elif op == "inspect_file":
        action["filename"] = random.choice(["server.py", "../../../etc/passwd", "", None])
    elif op == "inspect_lines":
        action["filename"] = "server.py"
        action["start_line"] = random.choice([-100, 0, 1, 50])
        action["end_line"] = random.choice([-10, 0, 1, 100, 500])
        
    return action

async def stress_worker(worker_id: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Reset task randomly
        task = random.choice(["easy", "medium", "hard", "invalid"])
        try:
            r = await client.post(f"{SERVER_URL}/reset", json={"task_id": task})
            print(f"Worker {worker_id} RESET {task}: {r.status_code}")
        except Exception as e:
            print(f"Worker {worker_id} RESET error: {e}")
            
        for step in range(50):
            action = generate_random_action()
            try:
                r = await client.post(f"{SERVER_URL}/step", json=action)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("done"):
                        print(f"Worker {worker_id} DONE reached at step {step}")
                        break
            except Exception as e:
                pass # network drops or connection limits
                
        # Randomly check state
        try:
            r = await client.get(f"{SERVER_URL}/state")
        except Exception as e:
            pass

async def main():
    print("Beginning BRUTAL STRESS TEST on /reset and /step endpoints...")
    # Fire off 200 concurrent aggressive workers
    start = time.time()
    workers = [stress_worker(i) for i in range(200)]
    await asyncio.gather(*workers)
    duration = time.time() - start
    print(f"Brutal stress test completed 200 concurrent runs in {duration:.2f}s")
    
    # Final health check
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{SERVER_URL}/health")
            print(f"Server survival check: HTTP {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Server CRASHED or UNRESPONSIVE: {e}")

if __name__ == "__main__":
    asyncio.run(main())
