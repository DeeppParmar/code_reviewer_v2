"""FastAPI server exposing the CodeReviewEnv for evaluation."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from env.environment import CodeReviewEnv
from env.models import CodeReviewAction, CodeReviewObservation

app = FastAPI()

ENV = CodeReviewEnv()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a JSON error response for unhandled exceptions (never crash server)."""

    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors as JSON without crashing."""

    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.get("/")
async def root() -> Dict[str, str]:
    """Root route for HF Spaces UI health."""

    return {"status": "ok", "message": "Code Review OpenEnv is running. See /health, /reset, /step, /state."}


@app.post("/reset", response_model=CodeReviewObservation)
async def reset(payload: Optional[Dict[str, Any]] = Body(default=None)) -> CodeReviewObservation:
    """Reset the environment for a given task_id (defaults to easy)."""

    task_id = "easy"
    if payload and isinstance(payload, dict) and "task_id" in payload:
        task_id = str(payload["task_id"])
    try:
        return ENV.reset(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/step")
async def step(action: CodeReviewAction) -> Dict[str, Any]:
    """Apply an action to the environment and return the step result."""

    observation, reward, done, info = ENV.step(action)
    return {"observation": observation.model_dump(), "reward": reward, "done": done, "info": info}


@app.get("/state")
async def state() -> Dict[str, Any]:
    """Return current environment state as JSON."""

    return ENV.state()


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok", "version": "1.0.0"}

