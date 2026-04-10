"""Hard task definition.

Provides a realistic async Python service function with exactly 4 real bugs and
1 red herring, plus ground truth metadata with exact line numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from env.models import GroundTruthBug


@dataclass(frozen=True)
class TaskSpec:
    """Container for a task specification used by the environment."""

    task_id: str
    max_steps: int
    pr_title: str
    pr_description: str
    full_file: str
    code_diff: str
    ground_truth: List[GroundTruthBug]


def get_task() -> TaskSpec:
    """Return the hard task specification (buggy code + ground truth)."""

    full_file = "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import asyncio",
            "import yaml",
            "from typing import Dict, List, AsyncGenerator",
            "from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes",
            "from cryptography.hazmat.backends import default_backend",
            "",
            "class NetworkStreamer:",
            "    async def stream_data(self, url: str) -> AsyncGenerator[bytes, None]:",
            "        for i in range(3):",
            "            yield b'data_chunk'",
            "",
            "_KEY_MATERIAL = b'sixteen_byte_key'",
            "_SESSION_CACHE: Dict[str, str] = {}",
            "",
            "async def process_user_sessions(user_params: List[str]) -> Dict[str, str]:",
            '    """Fetch user configs, decrypt tokens, and cache session state."""',
            "    streamer = NetworkStreamer()",
            "    ",
            "    async def _handle_user(param: str) -> None:",
            "        # Load user configuration YAML from parameter string",
            "        config = yaml.load(param, Loader=yaml.Loader)",
            "        user_id = config.get('uid', 'anonymous')",
            "        ",
            "        # Decrypt session token",
            "        cipher = Cipher(algorithms.AES(_KEY_MATERIAL), modes.ECB(), backend=default_backend())",
            "        decryptor = cipher.decryptor()",
            "        token = decryptor.update(config['token'].encode()) + decryptor.finalize()",
            "        ",
            "        # Stream audit logs to remote",
            "        audit_stream = streamer.stream_data('audit_service')",
            "        async for chunk in audit_stream:",
            "            if not chunk:",
            "                break",
            "        ",
            "        # Update global cache without synchronization",
            "        _SESSION_CACHE[user_id] = token.decode('utf-8', errors='ignore')",
            "        ",
            "        # Network backoff retry block",
            "        for attempt in range(3):",
            "            try:",
            "                await asyncio.sleep(0.1)",
            "                return",
            "            except Exception:",
            "                pass",
            "",
            "    tasks = [_handle_user(p) for p in user_params]",
            "    await asyncio.gather(*tasks)",
            "    return _SESSION_CACHE",
            ""
        ]
    )

    code_diff = "\n".join(
        [
            "--- a/crypto_service.py",
            "+++ b/crypto_service.py",
            "@@",
            "+async def process_user_sessions(user_params: List[str]) -> Dict[str, str]:",
            "+    async def _handle_user(param: str) -> None:",
            "+        config = yaml.load(param, Loader=yaml.Loader)",
            "+        user_id = config.get('uid', 'anonymous')",
            "+        cipher = Cipher(algorithms.AES(_KEY_MATERIAL), modes.ECB(), backend=default_backend())",
            "+        decryptor = cipher.decryptor()",
            "+        token = decryptor.update(config['token'].encode()) + decryptor.finalize()",
            "+        audit_stream = streamer.stream_data('audit_service')",
            "+        async for chunk in audit_stream:",
            "+            if not chunk:",
            "+                break",
            "+        _SESSION_CACHE[user_id] = token.decode('utf-8', errors='ignore')",
            "+        for attempt in range(3):",
            "+            try:",
            "+                await asyncio.sleep(0.1)",
            "+                return",
            "+            except Exception:",
            "+                pass",
            "+    tasks = [_handle_user(p) for p in user_params]",
            "+    await asyncio.gather(*tasks)",
            "+    return _SESSION_CACHE"
        ]
    )

    ground_truth = [
        GroundTruthBug(
            line_number=23,
            severity="critical",
            category="security",
            description="Unsafe YAML loading leading to arbitrary code execution.",
            required_keywords=[
                "safe_load", "unsafe", "loader", "injection", "execution",
                "deserializ", "arbitrary", "yaml.safe", "untrusted", "rce",
                "remote code", "pickle", "code execution", "malicious",
            ]
        ),
        GroundTruthBug(
            line_number=27,
            severity="critical",
            category="security",
            description="Use of insecure ECB mode for AES encryption.",
            required_keywords=[
                "ecb", "mode", "insecure", "cbc", "iv", "gcm",
                "block cipher", "initialization vector", "deterministic",
                "ciphertext", "encrypt", "cipher mode", "aes-ecb",
                "electronic codebook", "padding oracle", "confidential",
            ]
        ),
        GroundTruthBug(
            line_number=32,
            severity="major",
            category="bug",
            description="AsyncGenerator leak: stream is not explicitly closed and may leak resources.",
            required_keywords=[
                "close", "leak", "generator", "finally", "aclose",
                "resource", "cleanup", "context manager", "async with",
                "not closed", "file handle", "stream", "dispose",
                "exhausted", "iteration", "memory",
            ]
        ),
        GroundTruthBug(
            line_number=38,
            severity="critical",
            category="bug",
            description="Async race condition modifying global _SESSION_CACHE without a lock.",
            required_keywords=[
                "race", "lock", "sync", "concurrency", "thread",
                "race condition", "thread safe", "mutex", "asyncio.lock",
                "atomic", "shared state", "global", "concurrent",
                "gather", "parallel", "data race", "synchroniz",
            ]
        ),
        GroundTruthBug(
            line_number=45,
            severity="nit",
            category="style",
            description="Red herring exception swallow inside a deliberate retry-backoff polling loop.",
            is_red_herring=True,
        ),
    ]

    return TaskSpec(
        task_id="hard",
        max_steps=25,
        pr_title="Async Crypto: Session Caching Service",
        pr_description=(
            "This PR adds a highly concurrent background worker that parses YAML configs, "
            "decrypts AES user session tokens, streams an audit payload, and records the "
            "results into a shared global dictionary."
        ),
        full_file=full_file,
        code_diff=code_diff,
        ground_truth=ground_truth,
    )

