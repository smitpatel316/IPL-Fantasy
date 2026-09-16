"""IPL Fantasy API — FastAPI backend (D1: Next.js + FastAPI, Pi-hosted).

Run:  uvicorn api.index:app --port 8014        (dev; NEVER 8000 — NBA prod)
Docs: http://localhost:8014/api/docs
"""

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# CRITICAL: load env before importing modules that read it.
load_dotenv()

from fastapi import FastAPI, Request, WebSocket  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from api import draft_ws, schemas  # noqa: E402
from api.constants import SANDBOX_LEAGUE_NAME, SCORING_TABLE_VERSION  # noqa: E402
from api.database import init_db  # noqa: E402
from api.routers import admin, drafts, leagues, lineups, matchups, players, trades, waivers  # noqa: E402
from api.sandbox import seed_if_empty  # noqa: E402

APP_VERSION = "0.1.0-scaffold"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("api")


def _sandbox_mode() -> bool:
    return os.getenv("SANDBOX_MODE", "true").lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if _sandbox_mode():
        from api.database import connect

        with connect() as con:
            seed_if_empty(con)
    log.info(f"IPL Fantasy API {APP_VERSION} started sandbox={_sandbox_mode()}")
    sweeper = draft_ws.start_sweeper()
    yield
    sweeper.cancel()


app = FastAPI(
    lifespan=lifespan,
    title="IPL Fantasy API",
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        response = await call_next(request)
        ms = int((time.time() - start) * 1000)
        log.info(f"{req_id} {request.method} {request.url.path} -> {response.status_code} {ms}ms")
        response.headers["X-Request-Id"] = req_id
        return response
    except Exception as e:  # never leak a stack to the client
        ms = int((time.time() - start) * 1000)
        log.error(f"{req_id} {request.method} {request.url.path} FAILED {ms}ms err={e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "internal error", "request_id": req_id})


# CORS: local dev on any port (worktrees use 3014/3018/...) + FRONTEND_URL when set.
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in origins:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=schemas.HealthOut)
def health():
    return schemas.HealthOut(
        version=APP_VERSION, sandbox=_sandbox_mode(), scoring_table=SCORING_TABLE_VERSION
    )


app.include_router(leagues.router, prefix="/api/leagues", tags=["leagues"])
app.include_router(lineups.router, prefix="/api", tags=["lineups"])
app.include_router(drafts.router, prefix="/api/drafts", tags=["drafts"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(waivers.router, prefix="/api/waivers", tags=["waivers"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(matchups.router, prefix="/api/matchups", tags=["matchups"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.websocket("/api/drafts/{draft_id}/ws")
async def _draft_room_ws(websocket: WebSocket, draft_id: int):
    await draft_ws.draft_room_ws(websocket, draft_id)
