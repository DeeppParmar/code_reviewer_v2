"""Console entrypoint expected by openenv validate.

Provides a `server` script that runs uvicorn for `server:app` on port 7860.
"""

from __future__ import annotations

import os
from typing import NoReturn

import uvicorn


def main() -> NoReturn:
    """Run the FastAPI app using uvicorn on the mandated port."""

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("server:app", host=host, port=port)
    raise SystemExit(0)

