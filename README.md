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

## What Makes This Environment Unique

| Feature | Description |
|---|---|
| **Semantic "Why" Metric** | Models must explain *why* something is a bug, not just flag the line. Missing required keywords (e.g. `"ecb"`, `"lock"`) halves the precision credit. |
| **Red Herring Traps** | Deliberately planted code that *looks* buggy but is semantically correct. Penalizes statistical pattern-matching over true comprehension. |
| **Multi-Model Benchmarking** | Built-in orchestrator (`benchmark_models.py`) to compare 5+ frontier LLMs head-to-head across all difficulty tiers. |
| **Fault-Tolerant Inference** | Gracefully handles API credit depletion (HTTP 402), malformed LLM output, and schema violations without crashing. |
| **Dense Reward Shaping** | Non-sparse, per-step rewards guide RL agents toward optimal review strategies. |

📄 **[Architecture Blueprint](ARCHITECTURE_BLUEPRINT.md)** · 📄 **[Findings Paper](FINDINGS_PAPER.md)**

---

## Key Features

- **FastAPI server** with `reset` / `step` / `state` endpoints
- **Three difficulty tiers** — `easy` · `medium` · `hard`
- **Deterministic grading** with dense, step-level rewards
- **Dual-mode inference** — LLM mode (HF Router) and benchmark mode (perfect deterministic)
- **Fault-tolerant** — handles malformed output, schema variants, and provider failures (401/402/403)

---

## Observation Space

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | `easy`, `medium`, or `hard` |
| `pr_title` / `pr_description` | `str` | Pull request metadata |
| `full_file` | `str` | Complete file under review |
| `code_diff` | `str` | Unified diff |
| `existing_comments` | `list` | Agent's prior comments |
| `step_number` / `max_steps` | `int` | Step progress |

## Action Space

| Operation | Parameters |
|---|---|
| `add_comment` | `line_number`, `severity`, `category`, `message` |
| `approve` | `summary` |
| `request_changes` | `summary` |
| `done` | _(none)_ |

---

## Tasks

| Task | Domain | Bugs | Semantic Keywords | Description |
|------|--------|------|:-:|-------------|
| **easy** | List processing | 3 | — | Off-by-one, null check, bad conditional |
| **medium** | Web handler | 4 | — | SQL injection, XSS, IDOR, hardcoded secret |
| **hard** | Async crypto service | 4 + 1 trap | ✓ | Unsafe YAML, ECB cipher, generator leak, race condition |

## Reward Function

| Condition | Reward |
|---|---:|
| Correct bug comment (first match ±5 lines) | +0.15 |
| Severity / category match bonus (each) | +0.05 |
| **Semantic keyword miss** (hard task) | **−0.10** |
| Duplicate comment | −0.05 |
| False positive | −0.10 |
| Red herring match | −0.20 |
| `done` | Final grader score |
| Efficiency bonus (fast + high score) | +0.10 |

**Grader:** Weighted F1 (`critical=3, major=2, minor=1, nit=0.5`). Deterministic.

---

## Benchmark Results (5 Frontier Models)

| Model | Easy | Medium | Hard | Avg |
|-------|:----:|:------:|:----:|:---:|
| Llama-3-70B | 0.435 | 0.398 | 0.072 | 0.302 |
| Mixtral-8x7B | 0.422 | 0.398 | 0.084 | 0.301 |
| Qwen-72B | 0.435 | 0.333 | 0.069 | 0.279 |
| DeepSeek-Coder-V2 ✓ | 0.435 | 0.333 | 0.056 | 0.275 |
| Gemma-2-27B | 0.350 | 0.333 | 0.084 | 0.256 |

✓ Only fully clean run (no quota limits hit)

**Key findings:**
- The code-specialized model (DeepSeek-Coder) scored *lowest* on the hard task — code generation training does not transfer to architectural reasoning
- Gemma-27B matched Mixtral-8x7B on hard despite being half the size — parameter count ≠ reasoning ability
- All models collapsed below 0.09 on hard, validating the semantic keyword requirement creates a genuine capability ceiling

See [`FINDINGS_PAPER.md`](./FINDINGS_PAPER.md) for full analysis · [`BENCHMARK_LOG.txt`](./BENCHMARK_LOG.txt) for per-step logs.

### Run Your Own Benchmark

```bash
HF_TOKEN=<token> python benchmark_models.py
```

Results are saved incrementally to `benchmark_results.json` and `benchmark_results.csv`.

---

## Quick Start

```bash
pip install -r requirements.txt
python -m pytest code-review-env/tests -q      # 52 passed
uvicorn server:app --host 0.0.0.0 --port 7860  # run server
```

```bash
# Docker
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Run Inference

```bash
# Benchmark mode (deterministic, no LLM)
REVIEW_STRATEGY=benchmark TASK_IDS=easy,medium,hard python inference.py

# LLM mode
HF_TOKEN=<token> REVIEW_STRATEGY=llm python inference.py
```

---

## Validation

- `pytest` → **52 passed**
- `openenv validate` → **Ready for multi-mode deployment**
- All live endpoints return HTTP 200
