"""Server package exposing ASGI app for `uvicorn server:app`."""

from server.app import app, main

__all__ = ["app", "main"]

