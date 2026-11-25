"""Production AI Agent — Part 6."""
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from utils.mock_llm import ask as llm_ask

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, record_cost
from .rate_limiter import check_rate_limit
from .redis_client import r, redis_healthy


logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level)
logger.addHandler(logging.StreamHandler())
logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        r.close()


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        logger.info(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "lvl": "INFO",
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "ms": round((perf_counter() - started) * 1000, 2),
        }))


@app.exception_handler(RedisConnectionError)
@app.exception_handler(RedisTimeoutError)
async def redis_unavailable(request: Request, exc: Exception):
    return JSONResponse(status_code=503, content={"detail": "Redis unavailable"})


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "ready"}


@app.post("/ask")
def ask(body: AskRequest, key: Annotated[str, Depends(verify_api_key)]):
    check_rate_limit(key)
    check_budget()
    answer = llm_ask(body.question)
    # Mock LLM chỉ trả văn bản, dùng số từ để ước lượng token.
    input_tokens = max(1, len(body.question.split()))
    output_tokens = max(1, len(answer.split()))
    cost = record_cost(input_tokens, output_tokens)
    return {"question": body.question, "answer": answer, "cost_usd": cost}
