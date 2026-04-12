"""ASGI app entrypoint expected by openenv validate."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import NoReturn

import uvicorn


def _load_impl_app() -> object:
    """Load FastAPI app from code-review-env/server.py."""

    repo_root = Path(__file__).resolve().parents[1]
    impl_root = repo_root / "code-review-env"
    impl_server = impl_root / "server.py"
    if not impl_server.exists():
        raise RuntimeError("Implementation server not found at code-review-env/server.py")
    if str(impl_root) not in sys.path:
        sys.path.insert(0, str(impl_root))
    spec = importlib.util.spec_from_file_location("code_review_env_impl_server", impl_server)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create module spec for implementation server")
    module = importlib.util.module_from_spec(spec)
    sys.modules["code_review_env_impl_server"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "app"):
        raise RuntimeError("Implementation server module does not define app")
    return getattr(module, "app")


app = _load_impl_app()


def main() -> NoReturn:
    """Run the ASGI app with uvicorn on port 7860."""

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("server:app", host=host, port=port)
    raise SystemExit(0)


if __name__ == "__main__":
    main()

