# MASTER BENCHMARK HISTORY & CONFIDENCE TRACKING

---

## 1. ALL SESSIONS MASTER COMPARISON TABLE (Ascending Order)

This table tracks the evolution of models across the entire benchmark development cycle.

| Session | Model | Easy | Medium | Hard | Avg | Notes / Event |
|---------|-------|------|--------|------|-----|---------------|
| **Session #1** | DeepSeek-V3 | 0.999* | 0.667 | 0.476 | 0.714 | *Pre-Grader Fix (Ceiling Bug Inflated Easy)* |
| **Session #1** | Qwen-2.5-72B | 0.889 | 0.737 | 0.240 | 0.622 | Pre-Grader Fix |
| **Session #1** | Llama-3.3-70B | 0.615 | 0.667 | 0.486 | 0.589 | Pre-Grader Fix |
|---------|-------|------|--------|------|-----|---------------|

*\*Note on Session 1: The 0.999 Easy task score for DeepSeek is artificially inflated due to an early ceiling bug. It is NOT comparable to future fully standardized runs. Grader logic was mathematically fixed in Session 2 to accurately mandate one-to-one False Positive penalties.*
| **Session #2** | Llama-3.3-70B | 0.714 | 0.690 | 0.524 | 0.643 | *Post-Grader Fix (Weighted FPs penalty added)* |
| **Session #2** | DeepSeek-V3 | 0.667 | 0.556 | 0.667 | 0.630 | Post-Grader Fix |
| **Session #2** | Qwen-2.5-72B | 0.800 | 0.273 | 0.643 | 0.572 | Post-Grader Fix |
|---------|-------|------|--------|------|-----|---------------|
| **Session #3** | DeepSeek-V3 | 0.462 | 0.667 | 0.720 | 0.616 | *Final Stable Baseline.* DeepSeek peaks Hard |
| **Session #3** | Llama-3.3-70B | 0.533 | 0.645 | 0.474 | 0.551 | Stable |
| **Session #3** | Qwen-2.5-72B | 0.800 | 0.500 | 0.240 | 0.513 | Inconsistent precision on hard. |
|---------|-------|------|--------|------|-----|---------------|
| **Session #4** | Determ. Baseline | 0.999 | 0.999 | 0.999 | 0.999 | *Validation Run (Hardcoded Python script bypass)* |
|---------|-------|------|--------|------|-----|---------------|
| **Session #5** | DeepSeek-Chat | 0.999 | 0.667 | 0.800 | 0.822 | *LATEST (Confidence enabled). DeepSeek dominates.* |
| **Session #5** | Qwen-2.5-72B | 0.727 | 0.824 | 0.500 | 0.684 | *LATEST (Confidence enabled).* |
| **Session #5** | GPT-4o-Mini | 0.999 | 0.588 | 0.323 | 0.637 | *LATEST (Confidence enabled). Crumbles on Hard.* |
| **Session #5** | Llama-3.3-70B | 0.556 | 0.625 | 0.375 | 0.519 | *LATEST (Confidence enabled). Severely overconfident.* |
| **Session #5** | Mistral-Small | 0.308 | 0.333 | 0.295 | 0.312 | *LATEST (Confidence enabled). Hits 34k token limit.* |

---

## 2. THE CONFIDENCE TELEMETRY METRICS (Session #5 Deep Dive)

With the prompt fix explicitly mapping `"confidence": 87` to the JSON parser, the LLMs returned detailed self-awareness metrics. 
The Grader penalized False Positives when models had `confidence >= 80%` and awarded bonuses when `confidence >= 80%` correctly flagged a true bug.

### Model Self-Awareness & Calibration Breakdown
| Model | Avg Confidence Reported | High-Confidence Correct | High-Confidence Wrong | Calibration Penalty/Score | Verdict |
|-------|--------------------------|-----------------------|---------------------|---------------------------|---------|
| **DeepSeek-Chat** | **96% - 100%** | **8** `(Highest)` | **1** `(Lowest)` | **0.800+** `(Calibration Bonus)`| DeepSeek is exceptionally self-aware. When it is confident, it is right. |
| **Qwen-2.5-72B** | **90% - 100%** | **7** | **3** | **0.750** `(Minor Bonus)` | Solid self-awareness, but susceptible to minor hallucinations. |
| **GPT-4o-Mini** | **90% - 95%** | **5** | **8** | **0.429** `(Warning/Penalty)` | Moderately overconfident. Assumes normal code patterns are bugs heavily. |
| **Llama-3.3-70B** | **88% - 99%** | **5** | **19** `(Highest)` | **0.222** `(Heavy Penalty)` | Dangerously overconfident. Blindly flags 19 false positives with 90%+ certainty. |
| **Mistral-Small** | **85% - 100%** | **3** | **22** `(Critical)` | **0.222** `(Heavy Penalty)` | Severely compromised precision. Cannot distinguish genuine bugs from the Red Herrings. Hit API token limit (34k context) during Hard test. |


---

## 3. LATEST RUNS RAW SUMMARY (Appended Output)

### Execution Times (Concurrent Matrix):
- `gpt-4o-mini`: 32.60s 
- `qwen-2.5-72b`: 30.06s
- `deepseek-chat`: 46.53s
- `mistral-small`: 82.66s
- `llama-3.3-70b`: 121.32s

### Final OpenEnv Output Grader Logic Used for these Benchmarks:
1. The **Confidence Modifier** strictly adds +0.05 efficiency points internally per valid high-confidence guess, but subtracts -0.10 for incorrect guesses.
2. Llama-3.3-70B failed dramatically precisely because the Confidence Tracker applied severe cumulative `-0.10` hits to its precision metric every time it hallucinated a bug with `>80%` stated confidence.
3. Mistral-Small's long generation context surpassed the 21,372 OpenRouter cutoff token limit producing a `HTTP 402` Mid-stream block. The environment recovered perfectly from this parsing interruption, closing the task with `0.295` rather than crashing the testing suite.
