from __future__ import annotations

import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from slowapi import Limiter

from app import services
from app.config import Settings
from app.db import Repository, User
from app.ingest import UploadError, parse_history, validate_rows
from app.ml.model import RulModel

bearer = HTTPBearer(auto_error=False)


def _rate_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth:
        return hashlib.sha256(auth.encode()).hexdigest()[:16]
    return request.client.host if request.client else "anonymous"


limiter = Limiter(key_func=_rate_key)
WRITE_LIMIT = "60/minute"
router = APIRouter(prefix="/api")


# ------------------------------------------------------------------ deps


def get_model(request: Request) -> RulModel:
    return request.app.state.model


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_user(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None:
        raise HTTPException(401, "Sign in to continue")
    user = await request.app.state.auth.user_for(credentials.credentials)
    if user is None:
        raise HTTPException(401, "Your session has expired. Sign in again.")
    return user


ModelDep = Annotated[RulModel, Depends(get_model)]
RepoDep = Annotated[Repository, Depends(get_repo)]
UserDep = Annotated[User, Depends(get_user)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def _engine(repo: Repository, user: User, engine_id: UUID) -> dict:
    try:
        return await services.load_engine(repo, user, str(engine_id))
    except services.NotFound:
        raise HTTPException(404, "Engine not found") from None


# --------------------------------------------------------------- schemas


class EngineCreate(BaseModel):
    engine_id: str = Field(min_length=1, max_length=64, description="Name shown in the fleet, e.g. ENG-042")
    model: str | None = Field(None, max_length=120)
    serial_number: str | None = Field(None, max_length=120)
    aircraft_registration: str | None = Field(None, max_length=32)


class ReadingsIn(BaseModel):
    readings: list[dict[str, float | int | None]] = Field(max_length=2000)
    replace: bool = False


class DemoFleetIn(BaseModel):
    size: int = Field(8, ge=1, le=12)


# ---------------------------------------------------------------- public


@router.get("/health")
async def health(model: ModelDep):
    return {"status": "ok", "model_version": model.version}


@router.get("/model")
async def model_card(model: ModelDep):
    return model.card()


# --------------------------------------------------------------- engines


@router.get("/engines")
async def list_engines(user: UserDep, repo: RepoDep):
    return await repo.list_engines(user)


@router.post("/engines", status_code=201)
@limiter.limit(WRITE_LIMIT)
async def create_engine(request: Request, body: EngineCreate, user: UserDep, repo: RepoDep):
    existing = await repo.list_engines(user)
    if any(e["engine_id"] == body.engine_id for e in existing):
        raise HTTPException(409, f"You already have an engine named {body.engine_id}")
    return await repo.create_engine(user, body.model_dump())


@router.get("/engines/{engine_id}")
async def get_engine(engine_id: UUID, user: UserDep, repo: RepoDep, model: ModelDep):
    engine = await _engine(repo, user, engine_id)
    return await services.analyze(repo, model, user, engine)


@router.delete("/engines/{engine_id}", status_code=204)
@limiter.limit(WRITE_LIMIT)
async def delete_engine(request: Request, engine_id: UUID, user: UserDep, repo: RepoDep):
    await _engine(repo, user, engine_id)
    await repo.delete_engine(user, str(engine_id))


@router.post("/engines/{engine_id}/assess")
@limiter.limit(WRITE_LIMIT)
async def assess_engine(request: Request, engine_id: UUID, user: UserDep, repo: RepoDep, model: ModelDep):
    engine = await _engine(repo, user, engine_id)
    result = await services.assess_and_store(repo, model, user, engine)
    if result["analysis"] is None:
        raise HTTPException(400, "This engine has no recorded cycles yet")
    return result


@router.post("/engines/{engine_id}/readings")
@limiter.limit(WRITE_LIMIT)
async def add_readings(
    request: Request, engine_id: UUID, body: ReadingsIn, user: UserDep, repo: RepoDep, model: ModelDep, settings: SettingsDep
):
    engine = await _engine(repo, user, engine_id)
    try:
        rows = validate_rows(body.readings, settings.max_history_cycles)
        await services.append_history(repo, settings, user, engine, rows, "api", body.replace)
    except UploadError as e:
        raise HTTPException(400, str(e)) from None
    return await services.assess_and_store(repo, model, user, engine)


@router.post("/engines/{engine_id}/upload")
@limiter.limit(WRITE_LIMIT)
async def upload_history(
    request: Request,
    engine_id: UUID,
    user: UserDep,
    repo: RepoDep,
    model: ModelDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    unit: int | None = Form(None),
    replace: bool = Form(False),
):
    engine = await _engine(repo, user, engine_id)
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, f"Files are limited to {settings.max_upload_bytes // 1_000_000} MB")
    try:
        rows = parse_history(content, unit, settings.max_history_cycles)
        await services.append_history(repo, settings, user, engine, rows, "upload", replace)
    except UploadError as e:
        raise HTTPException(400, str(e)) from None
    return await services.assess_and_store(repo, model, user, engine)


@router.post("/engines/{engine_id}/replay")
@limiter.limit(WRITE_LIMIT)
async def advance_replay(
    request: Request,
    engine_id: UUID,
    user: UserDep,
    repo: RepoDep,
    model: ModelDep,
    settings: SettingsDep,
    steps: int = Query(1, ge=1, le=100),
):
    engine = await _engine(repo, user, engine_id)
    try:
        return await services.step_replay(repo, model, settings, user, engine, steps)
    except UploadError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/fleet/demo", status_code=201)
@limiter.limit("5/minute")
async def demo_fleet(request: Request, body: DemoFleetIn, user: UserDep, repo: RepoDep, model: ModelDep, settings: SettingsDep):
    return await services.create_demo_fleet(repo, model, settings, user, body.size)
