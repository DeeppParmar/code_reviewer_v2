"""Root-level inference script (required by Round 1 validator).

Delegates to the implementation in `code-review-env/inference.py` while ensuring:
  - Uses OpenAI client with API_BASE_URL
  - Reads credentials from HF_TOKEN (preferred) or OPENAI_API_KEY (fallback)
  - Emits mandatory [START]/[STEP]/[END] logs
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _ensure_token_env() -> None:
    """Ensure HF_TOKEN is set, falling back to OPENAI_API_KEY if present."""

    if os.getenv("HF_TOKEN"):
        return
    if os.getenv("OPENAI_API_KEY"):
        os.environ["HF_TOKEN"] = os.environ["OPENAI_API_KEY"]


def _run_impl() -> int:
    """Load and run the implementation inference main()."""

    repo_root = Path(__file__).resolve().parent
    impl_root = repo_root / "code-review-env"
    impl_file = impl_root / "inference.py"

    if not impl_file.exists():
        raise RuntimeError("Implementation inference not found at code-review-env/inference.py")

    if str(impl_root) not in sys.path:
        sys.path.insert(0, str(impl_root))

    spec = importlib.util.spec_from_file_location("code_review_env_impl_inference", impl_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load inference implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules["code_review_env_impl_inference"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "main"):
        raise RuntimeError("Implementation inference module does not define main()")

    return int(module.main())


def main() -> int:
    """Entry point for validator-compatible inference."""

    _ensure_token_env()
    return _run_impl()


if __name__ == "__main__":
    raise SystemExit(main())

