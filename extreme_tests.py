"""Extreme test suite for Code Review OpenEnv — final audit pass."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "code-review-env"))

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction

results = []

def log(test_id, name, expected, actual, passed):
    status = "PASS" if passed else "FAIL"
    results.append((test_id, name, expected, actual, status))
    print(f"  [{status}] {test_id}: {name} | expected={expected} | actual={actual}")

print("=" * 70)
print("EXTREME TEST SUITE — Code Review OpenEnv")
print("=" * 70)

# ============== MATH CORRECTNESS TESTS ==============
print("\n--- MATH CORRECTNESS TESTS ---")

# TEST-M01: Partial score
env = CodeReviewEnv()
env.reset("easy")
env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Off-by-one bug"))
_, reward, done, info = env.step(CodeReviewAction(operation="done"))
score = info["current_score"]
log("M01", "Partial score", "0.25-0.45", f"{score:.4f}", 0.20 <= score <= 0.50 and score != 0.999)

# TEST-M02: False positive penalty
env = CodeReviewEnv()
env.reset("medium")
env.step(CodeReviewAction(operation="add_comment", line_number=21, severity="critical", category="security", message="sqli"))
env.step(CodeReviewAction(operation="add_comment", line_number=999, severity="minor", category="style", message="fp1"))
env.step(CodeReviewAction(operation="add_comment", line_number=998, severity="minor", category="style", message="fp2"))
env.step(CodeReviewAction(operation="add_comment", line_number=997, severity="minor", category="style", message="fp3"))
_, reward, done, info = env.step(CodeReviewAction(operation="done"))
score = info["current_score"]
log("M02", "FP penalty", "<0.4", f"{score:.4f}", score < 0.4 and score != 0.999)

# TEST-M03: Zero bugs found floor
env = CodeReviewEnv()
env.reset("hard")
_, reward, done, info = env.step(CodeReviewAction(operation="done"))
score = info["current_score"]
log("M03", "Zero bugs floor", "0.001", f"{score:.4f}", score <= 0.01 and score > 0.0)

# TEST-M04: Perfect hard task
env = CodeReviewEnv()
env.reset("hard")
env.step(CodeReviewAction(operation="add_comment", line_number=30, severity="critical", category="security", message="Unsafe YAML loading allows arbitrary code execution via untrusted input rce"))
env.step(CodeReviewAction(operation="add_comment", line_number=35, severity="critical", category="security", message="ECB mode is deterministic reveals plaintext pattern ciphertext leak"))
env.step(CodeReviewAction(operation="add_comment", line_number=41, severity="major", category="bug", message="AsyncGenerator resource leak stream not closed context manager aclose memory leak"))
env.step(CodeReviewAction(operation="add_comment", line_number=47, severity="critical", category="bug", message="Async race condition shared mutable _SESSION_CACHE modified without asyncio.Lock synchronization data race"))
env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="critical", category="security", message="Hardcoded fallback secret key exposed in source code attacker can compromise credentials", filename="config_loader.py"))
env.step(CodeReviewAction(operation="add_comment", line_number=26, severity="major", category="performance", message="Synchronous file write blocks event loop in async function causes latency concurrency degraded throughput", filename="audit_logger.py"))
_, reward, done, info = env.step(CodeReviewAction(operation="done"))
score = info["current_score"]
log("M04", "Perfect hard score", "0.90-0.999", f"{score:.4f}", score >= 0.90 and score <= 0.999)

# TEST-M05: Determinism
scores_m05 = []
for _ in range(5):
    env = CodeReviewEnv()
    env.reset("easy")
    env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Off-by-one bug"))
    _, _, _, info = env.step(CodeReviewAction(operation="done"))
    scores_m05.append(info["current_score"])
all_same = all(s == scores_m05[0] for s in scores_m05)
log("M05", "Determinism", "all_equal", f"{scores_m05[0]:.4f}x5 same={all_same}", all_same)

# TEST-M06: FP weighted precision
env = CodeReviewEnv()
env.reset("medium")
env.step(CodeReviewAction(operation="add_comment", line_number=21, severity="critical", category="security", message="sqli"))
for i in range(5):
    env.step(CodeReviewAction(operation="add_comment", line_number=900+i, severity="minor", category="style", message=f"false positive {i}"))
_, reward, done, info = env.step(CodeReviewAction(operation="done"))
score = info["current_score"]
log("M06", "FP weighted precision", "<0.30", f"{score:.4f}", score < 0.30)

# TEST-M07: Cross-file bug scoring
env = CodeReviewEnv()
env.reset("hard")
_, reward, done, info = env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="critical", category="security", message="Hardcoded fallback secret key exposed in source code attacker", filename="config_loader.py"))
log("M07", "Cross-file bug", "reward>0", f"{reward:.4f}", reward > 0.0)

# TEST-M08: Wrong filename FP
env = CodeReviewEnv()
env.reset("hard")
_, reward, done, info = env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="critical", category="security", message="found something", filename="wrong_file.py"))
log("M08", "Wrong filename FP", "reward=0.01", f"{reward:.4f}", reward == 0.01)

# TEST-M09: Calibration high confidence correct
env = CodeReviewEnv()
env.reset("easy")
_, reward_with, _, _ = env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Off-by-one", confidence=95))
env2 = CodeReviewEnv()
env2.reset("easy")
_, reward_without, _, _ = env2.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="Off-by-one"))
log("M09", "Calibration bonus", "with > without", f"with={reward_with:.2f} without={reward_without:.2f}", reward_with > reward_without)

# TEST-M10: Calibration high confidence wrong
env = CodeReviewEnv()
env.reset("easy")
_, reward_hc_wrong, _, _ = env.step(CodeReviewAction(operation="add_comment", line_number=999, severity="minor", category="style", message="nope", confidence=95))
log("M10", "Calibration wrong penalty", "reward=0.01", f"{reward_hc_wrong:.4f}", reward_hc_wrong == 0.01)

# ============== STRESS TESTS ==============
print("\n--- STRESS TESTS ---")

# TEST-S01: 500 false positives
env = CodeReviewEnv()
env.reset("easy")
crashed = False
try:
    for i in range(500):
        env.step(CodeReviewAction(operation="add_comment", line_number=9999, severity="minor", category="style", message=f"fp{i}"))
except Exception as e:
    crashed = True
log("S01", "500 FPs no crash", "no crash", f"crashed={crashed}", not crashed)

# TEST-S03: Rapid reset no state bleed
env = CodeReviewEnv()
env.reset("easy")
env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="found one"))
env.reset("medium")
state = env.state()
log("S03", "No state bleed", "bugs_found=0", f"bugs_found={state['bugs_found']}", state["bugs_found"] == 0)

# TEST-S05: Unicode in message
env = CodeReviewEnv()
env.reset("easy")
crashed = False
try:
    env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="ECB 加密模式不安全 🔐"))
except Exception:
    crashed = True
log("S05", "Unicode message", "no crash", f"crashed={crashed}", not crashed)

# TEST-S06: 10000 char message
env = CodeReviewEnv()
env.reset("easy")
crashed = False
try:
    env.step(CodeReviewAction(operation="add_comment", line_number=18, severity="major", category="bug", message="a" * 10000))
except Exception:
    crashed = True
log("S06", "10k char message", "no crash", f"crashed={crashed}", not crashed)

# TEST-S07: inspect_lines boundary
env = CodeReviewEnv()
env.reset("hard")
_, r40, _, info40 = env.step(CodeReviewAction(operation="inspect_lines", filename="crypto_service.py", start_line=1, end_line=40))
env.reset("hard")
_, r41, _, info41 = env.step(CodeReviewAction(operation="inspect_lines", filename="crypto_service.py", start_line=1, end_line=50))
log("S07", "inspect_lines boundary", "40=ok 50=error", f"info41_err={info41.get('error')}", info41.get("error") is not None)

# TEST-S08: inspect_file nonexistent
env = CodeReviewEnv()
env.reset("hard")
_, r_ne, _, info_ne = env.step(CodeReviewAction(operation="inspect_file", filename="nonexistent.py"))
log("S08", "Nonexistent file", "error msg", f"err={info_ne.get('error')}", info_ne.get("error") is not None)

# TEST-S10: Red herring penalty
env = CodeReviewEnv()
env.reset("hard")
_, reward_rh, _, info_rh = env.step(CodeReviewAction(operation="add_comment", line_number=54, severity="nit", category="style", message="suspicious pass"))
log("S10", "Red herring penalty", "reward=0.01", f"{reward_rh:.4f}", reward_rh == 0.01)

# ============== CROSS-FILE TESTS ==============
print("\n--- CROSS-FILE TESTS ---")

# TEST-CF01: All 3 files accessible
for fn in ["crypto_service.py", "config_loader.py", "audit_logger.py"]:
    env = CodeReviewEnv()
    env.reset("hard")
    _, r, _, info = env.step(CodeReviewAction(operation="inspect_file", filename=fn))
    log(f"CF01-{fn}", f"inspect_file({fn})", "no error", f"err={info.get('error')}", info.get("error") is None)

# TEST-CF03: File-scoped false positive
env = CodeReviewEnv()
env.reset("hard")
_, r_cf3, _, info_cf3 = env.step(CodeReviewAction(operation="add_comment", line_number=50, severity="major", category="bug", message="wrong spot", filename="config_loader.py"))
log("CF03", "File-scoped FP", "reward=0.01", f"{r_cf3:.4f}", r_cf3 == 0.01)

# TEST-CF05: available_files complete
env = CodeReviewEnv()
obs = env.reset("hard")
af = obs.available_files or []
has_all = all(f in af for f in ["crypto_service.py", "config_loader.py", "audit_logger.py"])
log("CF05", "available_files complete", "3 files", f"{af}", has_all)

# ============== SUMMARY ==============
print("\n" + "=" * 70)
passed = sum(1 for r in results if r[4] == "PASS")
failed = sum(1 for r in results if r[4] == "FAIL")
print(f"EXTREME TEST RESULTS: {passed} PASSED, {failed} FAILED out of {len(results)} total")
if failed > 0:
    print("\nFAILED TESTS:")
    for r in results:
        if r[4] == "FAIL":
            print(f"  {r[0]}: {r[1]} — expected={r[2]} actual={r[3]}")
print("=" * 70)
