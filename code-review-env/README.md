# code-review-env

Core environment package for Code Review OpenEnv.

## Structure

```
env/
├── environment.py      # Reset / step loop
├── models.py           # Pydantic schemas
├── reward_engine.py    # Dense reward computation
├── state_manager.py    # Observation tracking
├── graders/            # Per-task deterministic graders
└── tasks/              # Task definitions (easy, medium, hard)
server.py               # FastAPI endpoints
inference.py            # Implementation engine (Execute from ROOT via ../inference.py)
tests/                  # Pytest suite (70 tests)
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/reset` | Start task (body: `{"task_id": "easy"}`) |
| `POST` | `/step` | Submit action, get observation + reward |
| `GET` | `/state` | Debug current state |

## Inference Modes

| Mode | Env Var | LLM Needed | Deterministic |
|------|---------|:---:|:---:|
| Benchmark | `REVIEW_STRATEGY=benchmark` | No | Yes |
| LLM | `REVIEW_STRATEGY=llm` | Yes | No |

Features: schema normalization, line clamping, early-stop on complete findings, deterministic fallback on provider errors, telemetric confidence calibration tracking, red herring traps, adversarial injection hooks.

## Benchmark Results (Latest)

For a complete breakdown, refer to `benchmark_comparison.md` in the repository root.

**Hugging Face Native (Production Phase):**
| Model | Environment | Avg F1 | Avg Conf |
|---|---|---|---|
| `deepseek-ai/DeepSeek-V3` | ✨ HuggingFace | **0.743** | 97% |
| `Qwen/Qwen2.5-72B-Instruct` | ✨ HuggingFace | **0.358** | 95% |
| `meta-llama/Meta-Llama-3-8B-Instruct` | ✨ HuggingFace | **0.144** | 96% |

**OpenRouter (Final Validation):**
| Model | Environment | Avg F1 | Avg Conf |
|---|---|---|---|
| `deepseek-ai/DeepSeek-V3` | 🚀 OpenRouter | **0.712** | 92% |
| `openai/gpt-4o-mini` | 🚀 OpenRouter | **0.694** | 90% |
| `meta-llama/llama-3.3-70b-instruct` | 🚀 OpenRouter | **0.626** | 94% |
| `qwen/qwen-2.5-72b-instruct` | 🚀 OpenRouter | **0.619** | 97% |

## Tests

```bash
python -m pytest tests -v   # 70 passed
```
