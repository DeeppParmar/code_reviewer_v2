---
title: Code Review OpenEnv
emoji: "\U0001F50E"
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Code Review OpenEnv

A deterministic, OpenEnv-style benchmark environment for evaluating AI code review agents. The agent receives buggy Python pull requests, leaves structured review comments, and is graded on precision, recall, and **semantic understanding** against ground-truth bugs.

**Live Space:** https://deepparmar-code-review.hf.space

---

## Environment Description & Motivation

Traditional code review benchmarks measure LLMs on a binary metric: *Did the model flag the correct line?* As frontier models approach ceiling performance on these shallow evaluations, we need environments that test deeper capabilities.

This environment simulates **real-world code review** — a task that software engineers perform daily. An AI agent must:
1. Read buggy Python code (pull request diffs)
2. Identify security vulnerabilities, logic bugs, and performance issues
3. Explain *why* something is broken (not just *where*)
4. Avoid false positives and deliberately planted traps

---

## Action Space

| Operation | Parameters | Description |
|---|---|---|
| `add_comment` | `line_number`, `severity`, `category`, `message`, `confidence` | Flag a bug with explanation + Telemetry calibration tracking |
| `approve` | `summary` | Approve the PR (risky if bugs remain) |
| `request_changes` | `summary` | Request changes with summary |
| `done` | _(none)_ | Finish review, trigger final grading |
| `inspect_file` | `filename` | View a specific file (hard task) |
| `inspect_lines` | `filename`, `start_line`, `end_line` | View specific lines |

**Severity:** `critical` | `major` | `minor` | `nit`
**Category:** `bug` | `security` | `performance` | `style`

## Observation Space

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | `easy`, `medium`, or `hard` |
| `pr_title` / `pr_description` | `str` | Pull request metadata |
| `full_file` | `str` | Complete file under review |
| `code_diff` | `str` | Unified diff |
| `existing_comments` | `list` | Agent's prior comments |
| `step_number` / `max_steps` | `int` | Step progress |
| `available_files` | `list` | Files available for inspection (hard task) |

---

## Tasks (3 Difficulty Tiers)

| Task | Domain | Real Bugs | Files | Traps | Semantic Check |
|------|--------|:---------:|:-----:|:-----:|:--------------:|
| **easy** | List processing | 3 | 1 | — | — |
| **medium** | Web API handler | 4 | 1 | — | — |
| **hard** | Async crypto service | 6 | 3 | 1 red herring + 2 adversarial comments | ✓ explanation_tiers |

### Task Details
- **Easy:** Off-by-one IndexError, null safety check, assignment-in-conditional syntax bug
- **Medium:** SQL injection, XSS, IDOR, hardcoded API secret
- **Hard:** Unsafe YAML deserialization (RCE), ECB cipher mode, async generator leak, race condition on shared dict, hardcoded secret key fallback, sync I/O blocking event loop — plus a red herring `try-except: pass` in a retry loop

---

## Reward Function

| Condition | Reward |
|---|---:|
| Correct bug match (±5 lines, severity+category) | +0.15 to +0.30 |
| Severity / category match bonus | +0.05 |
| **Semantic keyword miss** (hard task) | **−0.10** |
| **Confidence Calibration** (if confidence > 80%) | **+0.05 (correct) or −0.10 (wrong)** |
| Duplicate comment | −0.05 |
| False positive | −0.10 |
| Red herring flagged | −0.20 |
| `done` action | Final weighted F1 grader score |
| Efficiency bonus (fast + high score) | +0.10 |

**Grader:** Weighted F1 with strict 1-to-1 bug-to-comment matching.
Severity weights: `critical=3, major=2, minor=1, nit=0.5`.
False positives are weighted by their assigned severity to penalize spamming.
All scores deterministic and reproducible.

---

## Baseline Scores (Latest Results)

Includes Telemetric Confidence Scoring.

### 🏆 HUGGING FACE NATIVE SERVERLESS (Final Production Phase)
Native inference parsing successfully verified directly over `https://router.huggingface.co/v1`. DeepSeek-V3 completely dominated the native test group, surgically identifying every web vulnerability in the medium test environment to achieve a mathematically perfect 0.999 limit ceiling.

| Native Model Identifier | Environment | Easy F1 | Medium F1 | Hard F1 | **Avg F1** | Avg Conf. |
| :---------------------- | :---------- | :------ | :-------- | :------ | :--------- | :-------- |
| `deepseek-ai/DeepSeek-V3` | ✨ **HuggingFace** | 0.667 | **0.999** | 0.564 | **0.743** | 97% |
| `Qwen/Qwen2.5-72B-Instruct` | ✨ **HuggingFace** | 0.200 | 0.588 | 0.286 | **0.358** | 95% |
| `meta-llama/Meta-Llama-3-8B-Instruct` | ✨ **HuggingFace** | 0.429 | 0.001 | 0.001 | **0.144** | 96% |
| `meta-llama/Llama-3.3-70B-Instruct` | ❌ Rate Limited | - | - | - | **-** | - |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | ❌ Model Unsupported | - | - | - | **-** | - |

### 🌐 POST-SUBMISSION OPENROUTER BENCHMARKS
Final stress test verification leveraging OpenRouter API failover.

| Native Model Identifier | Environment | Easy F1 | Medium F1 | Hard F1 | **Avg F1** | Avg Conf. |
| :---------------------- | :---------- | :------ | :-------- | :------ | :--------- | :-------- |
| `deepseek-ai/DeepSeek-V3` | 🚀 **OpenRouter** | 0.750 | 0.667 | 0.720 | **0.712** | 92% |
| `openai/gpt-4o-mini` | 🚀 **OpenRouter** | 0.833 | 0.667 | 0.581 | **0.694** | 90% |
| `meta-llama/llama-3.3-70b-instruct` | 🚀 **OpenRouter** | 0.500 | 0.833 | 0.545 | **0.626** | 94% |
| `qwen/qwen-2.5-72b-instruct` | 🚀 **OpenRouter** | 0.800 | 0.556 | 0.500 | **0.619** | 97% |
| `mistralai/mistral-small-3.1-24b` | 🚀 **OpenRouter** | 0.001 | 0.001 | 0.999 | **0.334** | 100% |

### 🧠 Performance Analysis: Why Models Succeed or Fail
Our deterministic grading environment reveals deep behaviors not captured by standard multiple-choice benchmarks:

- 🥇 **DeepSeek-V3 (The Winner):** Dominated because of superior **confidence calibration** and **semantic reasoning**. Unlike other models, DeepSeek doesn't just guess. When faced with the adversarial "Red Herring" (`try...except: pass` inside a backoff loop), its confidence drops, allowing it to bypass the trap entirely. It correctly uses multi-step logic to deduce *why* code is conceptually flawed rather than just syntactically incorrect.
- 🥈 **Qwen-2.5-72B:** Highly capable at identifying localized syntax and logic errors in the Easy and Medium environments. However, it suffered in the Hard task, demonstrating **limitations in long-context, cross-file reasoning**. It often failed to correctly track how keys generated in `config_loader.py` were insecurely consumed in `crypto_service.py`.
- 🥉 **Llama-3.3-70B (The Overconfident Guesser):** Suffered mathematically due to **overconfidence syndrome**. The environment heavily penalizes false positives submitted with `>80%` confidence. Llama consistently flagged totally secure, verified code blocks as "Critical Vulnerabilities" with `95%` confidence, causing its F1 score to crash dynamically. It could not differentiate real bugs from the adversarial comment injections.
- 📉 **Smaller/Local Models (Mixtral, Meta-Llama-8B, Gemma):** Generally failed either due to **JSON parsing collapse** (outputting conversational text or reasoning tags instead of strict operation schemas) or by reaching maximum timeout limits when scanning larger codeblocks.

See [`FINDINGS_PAPER.md`](./FINDINGS_PAPER.md) for full analysis.

---

## Setup & Usage

### Prerequisites
```bash
pip install -r code-review-env/requirements.txt
```

### Run Server
```bash
cd code-review-env
uvicorn server:app --host 0.0.0.0 --port 7860
```

### Docker
```bash
cd code-review-env
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Run Inference

The inference script reads these environment variables:
- `API_BASE_URL` — The API endpoint for the LLM (default: `https://router.huggingface.co/v1`)
- `MODEL_NAME` — The model identifier (default: `Qwen/Qwen2.5-72B-Instruct`)
- `HF_TOKEN` — Your Hugging Face / API key (**required**)
- `ENV_BASE_URL` — Environment server URL (default: `http://127.0.0.1:7860`)

```bash
# LLM mode (requires API key)
API_BASE_URL=https://router.huggingface.co/v1 \
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct \
HF_TOKEN=<your-token> \
python inference.py

# Benchmark mode (deterministic, no LLM needed)
REVIEW_STRATEGY=benchmark TASK_IDS=easy,medium,hard \
python inference.py
```

### Run Tests
```bash
python -m pytest code-review-env/tests -v
```

---

## Project Structure

```
code-reviewer-v2/
├── server.py                    # Root FastAPI entrypoint (delegates to impl)
├── inference.py                 # Root inference shim (delegates to impl)
├── openenv.yaml                 # OpenEnv specification manifest
├── Dockerfile                   # Container build definition
├── pyproject.toml               # Project config + pytest settings
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── FINDINGS_PAPER.md            # Academic findings paper
├── ARCHITECTURE_BLUEPRINT.md    # Technical architecture docs
├── AUDIT_RESULTS.md             # Full audit & compliance results
├── REQUIREMENTS_CHECKLIST.md    # OpenEnv requirements checklist
├── updatess.txt                 # Benchmark progression & change log
├── lgos-complate.txt            # Benchmark log (Run 1 — 5 models)
├── logs-2m.txt                  # Benchmark log (Run 2 — 6 models)
├── logs-3.txt                   # Benchmark log (Run 3 — 6 models, latest)
├── code-review-env/
│   ├── server.py                # FastAPI server with /reset, /step, /state, /health
│   ├── inference.py             # Full LLM inference engine + benchmark mode
│   ├── openenv.yaml             # OpenEnv spec (impl copy)
│   ├── Dockerfile               # Impl Dockerfile
│   ├── requirements.txt         # Impl dependencies
│   ├── env/
│   │   ├── environment.py       # Core environment engine
│   │   ├── reward_engine.py     # Shaped reward computation
│   │   ├── state_manager.py     # Episode state tracking
│   │   ├── models.py            # Pydantic data schemas
│   │   ├── graders/
│   │   │   ├── base_grader.py   # Weighted F1 with semantic gates
│   │   │   ├── grader_easy.py   # Easy task grader
│   │   │   ├── grader_medium.py # Medium task grader
│   │   │   └── grader_hard.py   # Hard task grader (multi-file)
│   │   └── tasks/
│   │       ├── task_easy.py     # 3 runtime logic bugs
│   │       ├── task_medium.py   # 4 security vulnerabilities
│   │       └── task_hard.py     # 6 bugs across 3 files + 1 red herring
│   └── tests/                   # 70+ automated tests
└── server/                      # Alternate ASGI entrypoint
```

## Validation

```bash
openenv validate
```

- `pytest` → **70 passed**
- `openenv validate` → **Passes**
- All live endpoints return HTTP 200
- Dockerfile builds and runs cleanly
- Inference completes in <20 minutes on vcpu=2, memory=8gb
