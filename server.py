"""FastAPI server entrypoint (root-level) for OpenEnv validation and HF Spaces.

The Round 1 criteria expects `server.py` at the project root so `uvicorn server:app`
works from the repository root. The implementation lives in `code-review-env/`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_impl_app() -> object:
    """Load the implementation `app` from `code-review-env/server.py`.

    Returns:
        The FastAPI application instance.
    """

    repo_root = Path(__file__).resolve().parent
    impl_root = repo_root / "code-review-env"
    impl_server = impl_root / "server.py"

    if not impl_server.exists():
        raise RuntimeError("Implementation server not found at code-review-env/server.py")

    # Ensure `env/` package inside `code-review-env/` is importable.
    if str(impl_root) not in sys.path:
        sys.path.insert(0, str(impl_root))

    spec = importlib.util.spec_from_file_location("code_review_env_impl_server", impl_server)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for implementation server")

    module = importlib.util.module_from_spec(spec)
    sys.modules["code_review_env_impl_server"] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "app"):
        raise RuntimeError("Implementation server module does not define `app`")

    return getattr(module, "app")


app = _load_impl_app()

