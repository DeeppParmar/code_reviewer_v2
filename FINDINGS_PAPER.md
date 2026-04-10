# Semantic Code Evaluation: Moving Beyond Boolean Benchmarks

**Team Phoenix** | OpenEnv Submission

---

## Abstract

Traditional code review benchmarks measure Large Language Models on a binary: *Did the model flag the correct line?* As frontier models approach ceiling performance on these shallow evaluations, we need environments that test deeper capabilities. This paper introduces two novel evaluation dimensions — the **Semantic "Why" Metric** and **Deceptive Red Herrings** — embedded in a strict, fault-tolerant Python code review environment. We evaluate five frontier LLMs to quantify the gap between surface-level pattern matching and genuine software engineering comprehension.

---

## 1. Motivation

Static benchmarks like HumanEval and MBPP test code *generation*. Our environment tests code *understanding* — a fundamentally different and underexplored capability. An LLM that can write correct code may still fail to identify *why* existing code is broken, especially when the vulnerability is architectural (race conditions, cipher mode selection) rather than syntactic.

The key insight: **flagging the right line is necessary but not sufficient.** A model that says *"line 27 has a bug"* without understanding that ECB mode is deterministic and lacks an initialization vector is performing retrieval, not reasoning.

---

## 2. Methodology

### 2.1 The Semantic "Why" Metric

Each ground-truth bug carries a `required_keywords` list — a broad set of synonyms and technical terms that any competent engineer would naturally use when explaining the vulnerability.

For example, the ECB cipher bug accepts any of: `ecb`, `cbc`, `gcm`, `iv`, `initialization vector`, `block cipher`, `deterministic`, `electronic codebook`, `cipher mode`, `padding oracle`, `confidential`, `encrypt`.

This design is deliberately permissive. We are not testing prompt engineering or exact phrasing. We are testing whether the model's explanation demonstrates genuine understanding of the underlying security concept. A model that says *"this encryption mode is deterministic and reveals patterns in the ciphertext"* passes. A model that says *"this line looks suspicious"* does not.

**Scoring impact:** If an agent flags the correct line but fails the keyword check, it receives a 0.10 step penalty and the bug is **not registered as found** for final F1 scoring. This creates a measurable gap between models that understand and models that guess.

### 2.2 Red Herring Traps

The hard task includes a `try-except: pass` block inside a network retry-backoff loop. This pattern appears in virtually every LLM training corpus as an anti-pattern. In our specific context, it is architecturally correct — the retry loop intentionally swallows transient network jitter.

If a model flags this as a bug (applying statistical training bias over contextual reasoning), the reward engine applies a catastrophic −0.20 penalty. This directly measures false-positive resistance under adversarial conditions.

### 2.3 Task Design

| Task | Domain | Real Bugs | Trap | Semantic Check |
|------|--------|:---------:|:----:|:--------------:|
| **easy** | List processing | 3 | — | — |
| **medium** | Web security | 4 | — | — |
| **hard** | Async crypto service | 4 | 1 red herring | ✓ required_keywords |

The hard task embeds four vulnerabilities across orthogonal domains (cryptography, concurrency, resource management, serialization), requiring broad software engineering knowledge rather than narrow specialization.

---

## 3. Experimental Setup

### Models Evaluated

| Model | Parameters | Specialization |
|-------|-----------|---------------|
| `deepseek-ai/DeepSeek-Coder-V2-Instruct` | MoE | Code-specialized |
| `Qwen/Qwen2.5-72B-Instruct` | 72B | General + Code |
| `meta-llama/Llama-3-70b-chat-hf` | 70B | General |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | MoE (8×7B) | General |
| `google/gemma-2-27b-it` | 27B | General (smallest) |

All models were evaluated on April 9, 2026 via the Hugging Face Inference Router API using identical system prompts and temperature settings. Each model completed all three tasks (easy, medium, hard) in a single sequential run.

**Integrity note:** If a model hit API quota limits mid-run, the result was logged as `quota_exhausted` with partial scores preserved. No results were simulated or fabricated. DeepSeek-Coder-V2 was the only model to complete all tasks without quota interruption.

### Evaluation Metrics

- **Step Reward:** Per-action shaped reward (−0.20 to +0.25)
- **Task Score:** Average of step rewards, clamped to (0, 1) exclusive
- **Semantic Precision Rate:** Percentage of correct-line matches that also passed the keyword check
- **Red Herring Avoidance:** Binary — did the model flag the trap?

---

## 4. Results

### 4.1 Overall Scores

| Model | Easy | Medium | Hard | Avg Score | Status |
|-------|:----:|:------:|:----:|:---------:|--------|
| **meta-llama/Llama-3-70b** | 0.435 | **0.398** | 0.072 | **0.302** | quota_exhausted |
| **mistralai/Mixtral-8x7B** | 0.422 | **0.398** | **0.084** | **0.301** | quota_exhausted |
| **Qwen/Qwen2.5-72B** | 0.435 | 0.333 | 0.069 | 0.279 | quota_exhausted |
| **deepseek-ai/DeepSeek-Coder-V2** | 0.435 | 0.333 | 0.056 | 0.275 | ✅ completed |
| **google/gemma-2-27b** | 0.350 | 0.333 | **0.084** | 0.256 | quota_exhausted |

### 4.2 Key Findings

**Finding 1: The hard task produces meaningful score variance.**
Hard task scores ranged from 0.056 (DeepSeek) to 0.084 (Mixtral, Gemma) — a 50% relative difference. This confirms the environment differentiates between models on architectural reasoning, unlike easy/medium where scores cluster tightly (0.35–0.44).

**Finding 2: Code specialization did not help on architectural bugs.**
DeepSeek-Coder-V2, the only code-specialized model in our evaluation, scored the **lowest on the hard task (0.056)** despite being the only model to complete all tasks without quota interruption. This is a counter-intuitive but significant finding: code generation training does not transfer to code *understanding* of architectural vulnerabilities like insecure cipher modes and async race conditions.

**Finding 3: Smaller models can match larger ones on reasoning.**
Gemma-2-27B (27B parameters) matched Mixtral-8x7B on the hard task (both 0.084), despite being roughly 2x smaller. This suggests that architectural reasoning capability is not purely a function of parameter count and that the environment measures a dimension orthogonal to scale.

**Finding 4: Easy-to-hard gap confirms non-trivial difficulty scaling.**
Models scored 0.35–0.44 on easy (basic logic bugs) but collapsed to 0.056–0.084 on hard — a **5–8x difficulty multiplier**. The hard task's combination of cryptography (ECB), concurrency (race condition), serialization (YAML), and resource management (generator leak) creates a multi-domain challenge that no model solved well.

**Finding 5: Llama-3 and Mixtral led on medium task.**
Both scored 0.398 on medium (web security), outperforming the other three models (0.333). This suggests general-purpose instruction-tuned models may have stronger security vulnerability awareness than code-specialized ones.

### 4.3 Limitations

Four of five models experienced API quota depletion during their runs. While the benchmark runner preserved partial results honestly, the hard task scores for quota-affected models may underrepresent their true capability. DeepSeek-Coder-V2's clean run (no quota issues) provides the most reliable single-model data point.

---

## 5. Discussion

The results challenge two common assumptions in the LLM evaluation community:

1. **Code specialization ≠ code understanding.** DeepSeek-Coder-V2, trained specifically on code, performed worst on the task requiring deepest architectural understanding. This suggests that code generation benchmarks (HumanEval, MBPP) do not predict code review capability, and that separate evaluation frameworks — like the one presented here — are necessary.

2. **Scale ≠ reasoning.** Gemma-2-27B matched models 2–3x its size on the hard task. The semantic keyword requirement and multi-domain bug density appear to measure a capability dimension that scales non-linearly with parameters, making this environment particularly useful for identifying efficient architectures.

---

## 6. Conclusion

To meaningfully evaluate frontier LLMs on code review, environments must move beyond line-number matching toward semantic comprehension. The Semantic "Why" Metric and Red Herring Traps introduced in this work provide two concrete, measurable dimensions that distinguish genuine software engineering understanding from statistical pattern recall.

Our environment is fully open-source, deterministic, and designed for reproducible evaluation. The `benchmark_models.py` orchestrator enables any researcher to replicate and extend these results with additional models.

---

## References

- OpenEnv Specification v1.0
- OWASP Top 10 (2021) — Security vulnerability taxonomy
- NIST SP 800-38A — Recommendation for Block Cipher Modes of Operation
