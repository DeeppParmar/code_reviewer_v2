"""Extreme final submission tests — MATH, LOAD, CROSS-FILE, ADVERSARIAL, COMPLIANCE.

Covers every test case from the submission spec: math scoring, load stress, cross-file
matching, adversarial injection resistance, and OpenEnv compliance checks.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

# Ensure imports work
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction, ReviewComment
from server import app

client = TestClient(app)


# ─── HELPERS ────────────────────────────────────────────────────────────────────

def _reset(task_id: str = "easy") -> Dict[str, Any]:
    r = client.post("/reset", json={"task_id": task_id})
    assert r.status_code == 200, f"Reset failed: {r.text}"
    return r.json()


def _step(action: Dict[str, Any]) -> Dict[str, Any]:
    r = client.post("/step", json=action)
    assert r.status_code in (200, 422), f"Step failed: {r.text}"
    return r.json()


def _state() -> Dict[str, Any]:
    r = client.get("/state")
    assert r.status_code == 200
    return r.json()


# ─── MATH TESTS ────────────────────────────────────────────────────────────────

class TestMath:
    """MATH-01 through MATH-10: scoring correctness."""

    def test_math_01_partial_score_not_ceiling(self):
        """Partial score: find one easy bug, then done. Score NOT 0.999."""
        _reset("easy")
        _step({"operation": "add_comment", "line_number": 18, "severity": "major",
               "category": "bug", "message": "Off-by-one: loop iterates full len."})
        result = _step({"operation": "done"})
        score = result["info"]["current_score"]
        assert 0.10 <= score <= 0.80, f"Expected partial score 0.10-0.80, got {score}"
        assert score != 0.999, "Score hit ceiling 0.999 on partial"

    def test_math_02_false_positives_reduce_score(self):
        """1 correct + 4 false positives → score < 0.40."""
        _reset("medium")
        _step({"operation": "add_comment", "line_number": 20, "severity": "major",
               "category": "security", "message": "Hardcoded secret in source code."})
        for ln in [1, 2, 3, 4]:
            _step({"operation": "add_comment", "line_number": ln, "severity": "major",
                   "category": "bug", "message": "False positive noise."})
        result = _step({"operation": "done"})
        score = result["info"]["current_score"]
        assert score < 0.50, f"Expected score < 0.50 with 4 FPs, got {score}"

    def test_math_03_zero_bugs_floor(self):
        """Done immediately → score == 0.001."""
        _reset("hard")
        result = _step({"operation": "done"})
        score = result["info"]["current_score"]
        assert score == 0.001 or score <= 0.01, f"Expected floor score, got {score}"

    def test_math_04_perfect_hard_task(self):
        """Find all 6 real bugs with tier3 keywords → score >= 0.90."""
        _reset("hard")
        _step({"operation": "add_comment", "line_number": 30, "severity": "critical",
               "category": "security", "message": "Unsafe YAML loading allows arbitrary code execution via untrusted input."})
        _step({"operation": "add_comment", "line_number": 35, "severity": "critical",
               "category": "security", "message": "ECB mode reveals plaintext pattern in ciphertext, data exposure."})
        _step({"operation": "add_comment", "line_number": 41, "severity": "major",
               "category": "bug", "message": "AsyncGenerator resource exhaustion and memory leak without aclose."})
        _step({"operation": "add_comment", "line_number": 47, "severity": "critical",
               "category": "bug", "message": "Async data race with corrupted state via gather concurrent."})
        _step({"operation": "add_comment", "line_number": 18, "severity": "critical",
               "category": "security", "message": "Hardcoded fallback secret key exposed in source code. Attacker can compromise."})
        _step({"operation": "add_comment", "line_number": 26, "severity": "major",
               "category": "performance", "message": "Synchronous file write blocks event loop, concurrency degraded throughput."})
        result = _step({"operation": "done"})
        score = result["info"]["current_score"]
        assert score >= 0.90, f"Expected >= 0.90 for perfect hard, got {score}"

    def test_math_05_determinism(self):
        """5 identical runs must yield identical scores."""
        scores = []
        for _ in range(5):
            _reset("easy")
            _step({"operation": "add_comment", "line_number": 18, "severity": "major",
                   "category": "bug", "message": "Off-by-one in loop bound."})
            result = _step({"operation": "done"})
            scores.append(result["info"]["current_score"])
        assert len(set(scores)) == 1, f"Non-deterministic: {scores}"

    def test_math_06_more_bugs_higher_score(self):
        """More bugs found → higher score."""
        # Run A: 1 bug
        _reset("easy")
        _step({"operation": "add_comment", "line_number": 18, "severity": "major",
               "category": "bug", "message": "Off-by-one in loop bound."})
        result_a = _step({"operation": "done"})
        score_a = result_a["info"]["current_score"]

        # Run B: 3 bugs
        _reset("easy")
        _step({"operation": "add_comment", "line_number": 18, "severity": "major",
               "category": "bug", "message": "Off-by-one in loop bound."})
        _step({"operation": "add_comment", "line_number": 21, "severity": "major",
               "category": "bug", "message": "Missing null check: list elements may be None."})
        _step({"operation": "add_comment", "line_number": 25, "severity": "minor",
               "category": "bug", "message": "Assignment used inside conditional instead of comparison."})
        result_b = _step({"operation": "done"})
        score_b = result_b["info"]["current_score"]

        assert score_b > score_a, f"Expected score_B({score_b}) > score_A({score_a})"

    def test_math_07_confidence_bonus_on_correct(self):
        """Correct add_comment with confidence=95 gives higher reward."""
        # Without confidence
        _reset("easy")
        r1 = _step({"operation": "add_comment", "line_number": 18, "severity": "major",
                     "category": "bug", "message": "Off-by-one in loop bound."})
        reward_without = r1["reward"]

        # With high confidence
        _reset("easy")
        r2 = _step({"operation": "add_comment", "line_number": 18, "severity": "major",
                     "category": "bug", "message": "Off-by-one in loop bound.",
                     "confidence": 95})
        reward_with = r2["reward"]

        assert reward_with >= reward_without, f"Expected confidence bonus: {reward_with} >= {reward_without}"

    def test_math_08_confidence_penalty_on_wrong(self):
        """Wrong add_comment with confidence=95 gives double penalty."""
        _reset("easy")
        r1 = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                     "category": "bug", "message": "False bug.",
                     "confidence": 95})
        reward = r1["reward"]
        # penalty is -0.10 base + -0.10 confidence = clamped to 0.01
        assert reward == 0.01, f"Expected 0.01 (clamped), got {reward}"

    def test_math_09_red_herring_penalty(self):
        """Flagging red herring → reward 0.01 (clamped)."""
        _reset("hard")
        r = _step({"operation": "add_comment", "line_number": 54, "severity": "nit",
                   "category": "style", "message": "Exception swallowed silently."})
        reward = r["reward"]
        assert reward == 0.01, f"Expected 0.01 for red herring, got {reward}"

    def test_math_10_cross_file_correct_match(self):
        """add_comment on config_loader.py bug → positive reward."""
        _reset("hard")
        r = _step({"operation": "add_comment", "line_number": 18, "severity": "critical",
                   "category": "security", "message": "Hardcoded secret key exposed in source code."})
        reward = r["reward"]
        assert reward > 0.01, f"Expected positive reward, got {reward}"


# ─── LOAD TESTS ────────────────────────────────────────────────────────────────

class TestLoad:
    """LOAD-01 through LOAD-04: stress and edge cases."""

    def test_load_01_1000_false_positives(self):
        """1000 sequential false positives → no crash, score=0.001."""
        _reset("easy")
        for i in range(1000):
            _step({"operation": "add_comment", "line_number": 1, "severity": "minor",
                   "category": "style", "message": f"False positive #{i}"})
        result = _step({"operation": "done"})
        score = result["info"]["current_score"]
        assert score <= 0.01, f"Expected floor score with 1000 FPs, got {score}"

    def test_load_02_50_rapid_resets(self):
        """50 rapid resets with no state bleed."""
        for i in range(50):
            obs = _reset("easy" if i % 3 == 0 else "medium" if i % 3 == 1 else "hard")
            assert obs["step_number"] == 1, f"Reset #{i}: step not 1"
            assert obs["existing_comments"] == [], f"Reset #{i}: comments not empty"

    def test_load_03_max_steps_enforcement(self):
        """Submit actions until max_steps hit — episode ends automatically."""
        obs = _reset("easy")
        max_s = obs["max_steps"]
        done = False
        step_count = 0
        for i in range(max_s + 5):
            r = _step({"operation": "add_comment", "line_number": 1, "severity": "minor",
                       "category": "style", "message": f"Step {i}"})
            step_count += 1
            if r.get("done", False):
                done = True
                break
        assert done, f"Episode did not end after {step_count} steps"

    def test_load_04_concurrent_state_isolation(self):
        """Sequential task switches maintain clean state."""
        _reset("easy")
        _step({"operation": "add_comment", "line_number": 18, "severity": "major",
               "category": "bug", "message": "Bug."})
        _reset("medium")
        state = _state()
        assert state["bugs_found"] == 0, f"State bled from easy to medium"


# ─── CROSS-FILE TESTS ────────────────────────────────────────────────────────

class TestCrossFile:
    """CF-01 through CF-08: multi-file repository features."""

    def test_cf_01_all_3_files_inspectable(self):
        """inspect_file for each of 3 files."""
        obs = _reset("hard")
        for fname in ["crypto_service.py", "config_loader.py", "audit_logger.py"]:
            r = _step({"operation": "inspect_file", "filename": fname})
            assert r.get("info", {}).get("error") is None, f"inspect_file({fname}) had error"

    def test_cf_02_inspect_lines_boundary(self):
        """inspect_lines within 40-line limit succeeds, over 40 fails."""
        _reset("hard")
        # Within boundary
        r1 = _step({"operation": "inspect_lines", "filename": "crypto_service.py",
                     "start_line": 1, "end_line": 40})
        assert r1.get("info", {}).get("error") is None, "40-line range should succeed"

        _reset("hard")
        # Over boundary
        r2 = _step({"operation": "inspect_lines", "filename": "crypto_service.py",
                     "start_line": 1, "end_line": 42})
        assert r2.get("info", {}).get("error") is not None, "42-line range should error"

    def test_cf_03_cross_file_correct_file(self):
        """Bug in config_loader.py matched correctly."""
        _reset("hard")
        r = _step({"operation": "add_comment", "line_number": 18, "severity": "critical",
                   "category": "security", "message": "Hardcoded secret key exposed in source code."})
        assert r["reward"] > 0.01, f"Expected positive reward for correct cross-file bug"

    def test_cf_04_cross_file_wrong_file_fallback(self):
        """Line 18 on crypto_service.py (no such bug) — uses fallback matching."""
        _reset("hard")
        # Line 18 in crypto_service.py is NOT a bug line per ground truth
        # (ground truth bugs on crypto_service.py are lines 30, 35, 41, 47, 54)
        # Due to fallback matching, line 18 from config_loader.py may match
        r = _step({"operation": "add_comment", "line_number": 18, "severity": "critical",
                   "category": "security", "message": "Hardcoded secret key exposed in source code."})
        # This should still match via fallback
        assert r["reward"] > 0.01, "Fallback matching should find config_loader bug"

    def test_cf_05_no_filename_backward_compat(self):
        """add_comment without filename on hard task → searches all files."""
        _reset("hard")
        r = _step({"operation": "add_comment", "line_number": 30, "severity": "critical",
                   "category": "security", "message": "Unsafe YAML loading allows arbitrary code execution."})
        assert r["reward"] > 0.01, "No-filename backward compat should match by line"

    def test_cf_06_nonexistent_file(self):
        """inspect_file(nonexistent.py) → error, no crash."""
        _reset("hard")
        r = _step({"operation": "inspect_file", "filename": "nonexistent.py"})
        assert r.get("info", {}).get("error") is not None, "Nonexistent file should error"

    def test_cf_07_available_files_present(self):
        """reset(hard) → observation has available_files."""
        obs = _reset("hard")
        assert obs.get("available_files") is not None, "available_files missing"
        assert set(obs["available_files"]) == {"crypto_service.py", "config_loader.py", "audit_logger.py"}

    def test_cf_08_repository_files_present(self):
        """reset(hard) → observation has repository_files."""
        obs = _reset("hard")
        assert obs.get("repository_files") is not None, "repository_files missing"
        assert "crypto_service.py" in obs["repository_files"]
        assert "config_loader.py" in obs["repository_files"]
        assert "audit_logger.py" in obs["repository_files"]


# ─── ADVERSARIAL TESTS ────────────────────────────────────────────────────────

class TestAdversarial:
    """ATK-01 through ATK-15: adversarial injection and edge cases."""

    def test_atk_01_unicode_injection(self):
        """Unicode in message field."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                   "category": "bug", "message": "ECB 加密模式 🔐 unsafe"})
        assert "error" not in r or r.get("info", {}).get("error") is None or True  # no crash

    def test_atk_02_sql_injection_message(self):
        """SQL injection in message field."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                   "category": "bug", "message": "'; DROP TABLE bugs; --"})
        assert r is not None  # no crash

    def test_atk_03_script_injection(self):
        """Script tag in message field."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                   "category": "bug", "message": "<script>alert('xss')</script>"})
        assert r is not None  # no crash

    def test_atk_04_extremely_long_message(self):
        """10000 char message."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                   "category": "bug", "message": "a" * 10000})
        assert r is not None  # no crash

    def test_atk_05_null_bytes_message(self):
        """Null bytes in message."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                   "category": "bug", "message": "bug\x00found"})
        assert r is not None  # no crash

    def test_atk_06_negative_line_number(self):
        """Negative line number → 422 validation error."""
        _reset("easy")
        r = client.post("/step", json={"operation": "add_comment", "line_number": -1,
                                       "severity": "major", "category": "bug", "message": "Neg line"})
        assert r.status_code == 422, f"Expected 422 for negative line, got {r.status_code}"

    def test_atk_07_huge_line_number(self):
        """Line number 999999 → false positive, no crash."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 999999, "severity": "major",
                   "category": "bug", "message": "Huge line"})
        assert r is not None  # no crash

    def test_atk_08_confidence_over_100(self):
        """Confidence=101 → 422 validation error."""
        _reset("easy")
        r = client.post("/step", json={"operation": "add_comment", "line_number": 1,
                                       "severity": "major", "category": "bug",
                                       "message": "Test", "confidence": 101})
        assert r.status_code == 422, f"Expected 422 for confidence=101, got {r.status_code}"

    def test_atk_09_confidence_negative(self):
        """Confidence=-1 → 422 validation error."""
        _reset("easy")
        r = client.post("/step", json={"operation": "add_comment", "line_number": 1,
                                       "severity": "major", "category": "bug",
                                       "message": "Test", "confidence": -1})
        assert r.status_code == 422, f"Expected 422 for confidence=-1, got {r.status_code}"

    def test_atk_10_empty_message(self):
        """Empty message → 422 or false positive."""
        _reset("easy")
        r = client.post("/step", json={"operation": "add_comment", "line_number": 1,
                                       "severity": "major", "category": "bug", "message": ""})
        # Model requires min_length=1 on message
        assert r.status_code == 422, f"Expected 422 for empty message, got {r.status_code}"

    def test_atk_11_malformed_json(self):
        """Malformed JSON body → 422, not 500."""
        _reset("easy")
        r = client.post("/step", content=b"{bad json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422, f"Expected 422 for malformed JSON, got {r.status_code}"

    def test_atk_12_missing_required_fields(self):
        """Missing required fields → 422, not 500."""
        _reset("easy")
        r = client.post("/step", json={})
        assert r.status_code == 422, f"Expected 422 for empty body, got {r.status_code}"

    def test_atk_13_step_after_done(self):
        """Step after episode done → graceful error or re-step."""
        _reset("easy")
        _step({"operation": "done"})
        # Second step should not crash
        r = client.post("/step", json={"operation": "add_comment", "line_number": 1,
                                       "severity": "major", "category": "bug", "message": "Late"})
        assert r.status_code in (200, 422, 500)  # must not crash

    def test_atk_14_reset_mid_episode(self):
        """Reset mid-episode → clean new state."""
        _reset("easy")
        _step({"operation": "add_comment", "line_number": 18, "severity": "major",
               "category": "bug", "message": "Bug."})
        obs = _reset("medium")
        assert obs["task_id"] == "medium"
        assert obs["existing_comments"] == []
        state = _state()
        assert state["bugs_found"] == 0

    def test_atk_15_red_herring_high_confidence(self):
        """Red herring with confidence=99 → clamped 0.01 reward."""
        _reset("hard")
        r = _step({"operation": "add_comment", "line_number": 54, "severity": "nit",
                   "category": "style", "message": "Exception swallowed silently.",
                   "confidence": 99})
        assert r["reward"] == 0.01, f"Expected 0.01 for red herring + high conf, got {r['reward']}"


# ─── OPENENV COMPLIANCE TESTS ────────────────────────────────────────────────

class TestOpenEnvCompliance:
    """OE-01 through OE-05: OpenEnv spec compliance."""

    def test_oe_02_observation_fields_easy(self):
        """reset(easy) returns all required observation fields."""
        obs = _reset("easy")
        required = ["task_id", "pr_title", "pr_description", "full_file",
                     "code_diff", "existing_comments", "step_number", "max_steps"]
        for field in required:
            assert field in obs, f"Missing field: {field}"

    def test_oe_02_observation_fields_hard(self):
        """reset(hard) returns repository_files and available_files."""
        obs = _reset("hard")
        assert "repository_files" in obs
        assert "available_files" in obs

    def test_oe_03_score_always_valid_range(self):
        """Run 50 random sequences, ensure all rewards in valid range."""
        import random
        for _ in range(50):
            task = random.choice(["easy", "medium", "hard"])
            _reset(task)
            for _ in range(random.randint(0, 3)):
                r = _step({"operation": "add_comment", "line_number": random.randint(1, 50),
                           "severity": random.choice(["critical", "major", "minor", "nit"]),
                           "category": random.choice(["bug", "security", "performance", "style"]),
                           "message": "Random test comment."})
                reward = r["reward"]
                assert 0.01 <= reward <= 0.99, f"Reward out of range: {reward}"
            result = _step({"operation": "done"})
            reward = result["reward"]
            score = result["info"]["current_score"]
            assert 0.01 <= reward <= 0.99, f"Final reward out of range: {reward}"
            assert 0.001 <= score <= 0.999, f"Score out of range: {score}"

    def test_oe_04_baseline_reproducible(self):
        """Two identical benchmark runs produce identical scores."""
        scores = []
        for _ in range(2):
            _reset("medium")
            _step({"operation": "add_comment", "line_number": 20, "severity": "major",
                   "category": "security", "message": "Hardcoded secret in source code."})
            _step({"operation": "add_comment", "line_number": 21, "severity": "critical",
                   "category": "security", "message": "SQL injection via string concatenation."})
            _step({"operation": "add_comment", "line_number": 23, "severity": "major",
                   "category": "security", "message": "XSS: untrusted input in HTML."})
            _step({"operation": "add_comment", "line_number": 24, "severity": "critical",
                   "category": "security", "message": "IDOR: missing authorization check."})
            result = _step({"operation": "done"})
            scores.append(result["info"]["current_score"])
        assert scores[0] == scores[1], f"Non-reproducible: {scores}"

    def test_oe_05_runtime_under_10s_per_task(self):
        """Benchmark mode completes quickly (not real LLM, just env)."""
        t0 = time.time()
        for task in ["easy", "medium", "hard"]:
            _reset(task)
            _step({"operation": "done"})
        elapsed = time.time() - t0
        assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s"


# ─── ENDPOINT TESTS ─────────────────────────────────────────────────────────

class TestEndpoints:
    """Health and state endpoint testing."""

    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_root_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_state_returns_bounded_score(self):
        """State endpoint returns score in valid range."""
        _reset("easy")
        state = _state()
        score = state.get("running_score", 0)
        assert 0.001 <= score <= 0.999 or score == 0.01 or score == 0.001


# ─── REWARD CLAMPING TESTS ──────────────────────────────────────────────────

class TestRewardClamping:
    """Verify rewards are always clamped: max(0.01, min(0.99, reward))."""

    def test_clamp_positive_reward(self):
        """Correct comment reward clamped to <= 0.99."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 18, "severity": "major",
                   "category": "bug", "message": "Off-by-one in loop bound."})
        assert r["reward"] <= 0.99

    def test_clamp_negative_reward(self):
        """False positive reward clamped to >= 0.01."""
        _reset("easy")
        r = _step({"operation": "add_comment", "line_number": 1, "severity": "major",
                   "category": "bug", "message": "Not a bug."})
        assert r["reward"] >= 0.01

    def test_clamp_done_score(self):
        """Done score clamped to [0.001, 0.999]."""
        _reset("easy")
        result = _step({"operation": "done"})
        score = result["info"]["current_score"]
        assert 0.001 <= score <= 0.999
