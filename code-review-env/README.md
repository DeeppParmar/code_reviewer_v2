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

## Tests

```bash
python -m pytest tests -v   # 70 passed
```
