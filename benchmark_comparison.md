# 🏆 Code Review OpenEnv - Complete Master Benchmark Trajectory

## 📉 Final Performance Summary & Evaluation

Throughout the ascending environments, score clamping was mathematically refined from raw score inflation to strict OpenEnv F1 constraints, explicitly limited to **0.999**.

### 🥇 MASTER HISTORICAL BENCHMARK RESULTS
| Exact Model ID (No Manual Labels) | Phase | Easy F1 | Medium F1 | Hard F1 | **Avg F1** | Avg Conf. |
| :-------------------------------- | :---- | :------ | :-------- | :------ | :--------- | :-------- |
| `deepseek-ai/DeepSeek-V3` | 🕒 *Old Baseline* | 0.999 | 0.667 | 0.800 | **0.822** | 96% |
| `qwen/qwen-2.5-72b-instruct` | 🕒 *Old Baseline* | 0.727 | 0.824 | 0.500 | **0.684** | 95% |
| `meta-llama/llama-3.3-70b-instruct`| 🕒 *Old Baseline* | 0.556 | 0.625 | 0.375 | **0.519** | 94% |
| `deepseek-ai/DeepSeek-V3` | 🕒 *Old Concurrency* | 0.999 | 0.667 | 0.621 | **0.762** | 90% |
| `meta-llama/llama-3.1-70b-instruct`| 🕒 *Old Concurrency* | 0.833 | 0.636 | 0.545 | **0.671** | 96% |
| `qwen/qwen-2.5-72b-instruct` | 🕒 *Old Concurrency* | 0.667 | 0.625 | 0.500 | **0.597** | 99% |
| `openai/gpt-4o-mini` | 🕒 *Old Concurrency* | 0.667 | 0.588 | 0.308 | **0.521** | 90% |
| `meta-llama/llama-3.3-70b-instruct`| 🕒 *Live OpenRouter* | 0.999 | 0.625 | 0.545 | **0.723** | 95% |
| `deepseek-ai/DeepSeek-V3` | 🕒 *Live OpenRouter* | 0.600 | 0.667 | 0.500 | **0.589** | 94% |
| `openai/gpt-4o-mini` | 🕒 *Live OpenRouter* | 0.600 | 0.667 | 0.324 | **0.530** | 90% |
| `qwen/qwen-2.5-72b-instruct` | 🕒 *Live OpenRouter* | 0.500 | 0.588 | 0.500 | **0.529** | 98% |
| `mistralai/mistral-small-3.1-24b` | 🕒 *Live OpenRouter* | 0.100 | 0.333 | 0.999 | **0.477** | 100% |

<br>

> [!TIP]
> ### 🏆 HUGGING FACE NATIVE SERVERLESS (Final Production Phase)
> Native inference parsing successfully verified directly over `https://router.huggingface.co/v1`. 
> 
> **DeepSeek-AI** completely dominated the native test group, surgically identifying every web vulnerability in the medium test environment to achieve a mathematically perfect `0.999` limit ceiling.

| Native Model Identifier | Environment | Easy F1 | Medium F1 | Hard F1 | **Avg F1** | Avg Conf. |
| :---------------------- | :---------- | :------ | :-------- | :------ | :--------- | :-------- |
| `deepseek-ai/DeepSeek-V3` | ✨ **HuggingFace** | 0.667 | **0.999** | 0.564 | **0.743** | 97% |
| `Qwen/Qwen2.5-72B-Instruct` | ✨ **HuggingFace** | 0.200 | 0.588 | 0.286 | **0.358** | 95% |
| `meta-llama/Meta-Llama-3-8B-Instruct` | ✨ **HuggingFace** | 0.429 | 0.001 | 0.001 | **0.144** | 96% |
| `meta-llama/Llama-3.3-70B-Instruct` | ❌ Rate Limited | - | - | - | **-** | - |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | ❌ Model Unsupported | - | - | - | **-** | - |

<br>

### 🌐 POST-SUBMISSION OPENROUTER BENCHMARKS
*Final stress test verification leveraging OpenRouter failover.*

| Native Model Identifier | Environment | Easy F1 | Medium F1 | Hard F1 | **Avg F1** | Avg Conf. |
| :---------------------- | :---------- | :------ | :-------- | :------ | :--------- | :-------- |
| `deepseek-ai/DeepSeek-V3` | 🚀 **OpenRouter** | 0.750 | 0.667 | 0.720 | **0.712** | 92% |
| `openai/gpt-4o-mini` | 🚀 **OpenRouter** | 0.833 | 0.667 | 0.581 | **0.694** | 90% |
| `meta-llama/llama-3.3-70b-instruct` | 🚀 **OpenRouter** | 0.500 | 0.833 | 0.545 | **0.626** | 94% |
| `qwen/qwen-2.5-72b-instruct` | 🚀 **OpenRouter** | 0.800 | 0.556 | 0.500 | **0.619** | 97% |
| `mistralai/mistral-small-3.1-24b` | 🚀 **OpenRouter** | 0.001 | 0.001 | 0.999 | **0.334** | 100% |

<br>

### 🧠 Performance Analysis: Why Models Succeed or Fail
Our deterministic grading environment reveals deep behaviors not captured by standard multiple-choice benchmarks:

- 🥇 **DeepSeek-V3 (The Winner):** Dominated because of superior **confidence calibration** and **semantic reasoning**. Unlike other models, DeepSeek doesn't just guess. When faced with the adversarial "Red Herring" (`try...except: pass` inside a backoff loop), its confidence drops, allowing it to bypass the trap entirely. It correctly uses multi-step logic to deduce *why* code is conceptually flawed rather than just syntactically incorrect.
- 🥈 **Qwen-2.5-72B:** Highly capable at identifying localized syntax and logic errors in the Easy and Medium environments. However, it suffered in the Hard task, demonstrating **limitations in long-context, cross-file reasoning**. It often failed to correctly track how keys generated in `config_loader.py` were insecurely consumed in `crypto_service.py`.
- 🥉 **Llama-3.3-70B (The Overconfident Guesser):** Suffered mathematically due to **overconfidence syndrome**. The environment heavily penalizes false positives submitted with `>80%` confidence. Llama consistently flagged totally secure, verified code blocks as "Critical Vulnerabilities" with `95%` confidence, causing its F1 score to crash dynamically. It could not differentiate real bugs from the adversarial comment injections.
- 📉 **Smaller/Local Models (Mixtral, Meta-Llama-8B, Gemma):** Generally failed either due to **JSON parsing collapse** (outputting conversational text or reasoning tags instead of strict operation schemas) or by reaching maximum timeout limits when scanning larger codeblocks.
