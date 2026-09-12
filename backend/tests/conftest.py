"""Test doubles: an in-memory repository that enforces ownership like Supabase RLS."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import TELEMETRY_COLUMNS, User
from app.main import create_app
from app.ml.model import RulModel

ALICE = User(id="00000000-0000-0000-0000-00000000000a", email="alice@example.com", token="token-alice")
BOB = User(id="00000000-0000-0000-0000-00000000000b", email="bob@example.com", token="token-bob")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryRepository:
    def __init__(self):
        self.engines: dict[str, dict] = {}
        self.telemetry: dict[str, list[dict]] = {}
        self.assessments: list[dict] = []

    def _owned(self, user: User, engine_id: str) -> dict | None:
        e = self.engines.get(engine_id)
        return e if e and e["owner_id"] == user.id else None

    async def list_engines(self, user):
        return sorted((e for e in self.engines.values() if e["owner_id"] == user.id), key=lambda e: e["created_at"], reverse=True)

    async def get_engine(self, user, engine_id):
        return self._owned(user, engine_id)

    async def create_engine(self, user, fields):
        e = {"id": str(uuid.uuid4()), "owner_id": user.id, "status": "active", "health": None, "metadata": None, "created_at": now(), **fields}
        self.engines[e["id"]] = e
        return e

    async def update_engine(self, user, engine_id, fields):
        e = self._owned(user, engine_id)
        e.update(fields)
        return dict(e)

    async def delete_engine(self, user, engine_id):
        if self._owned(user, engine_id):
            del self.engines[engine_id]
            self.telemetry.pop(engine_id, None)

    async def get_telemetry(self, user, engine_id):
        if not self._owned(user, engine_id):
            return pd.DataFrame(columns=list(TELEMETRY_COLUMNS))
        rows = sorted(self.telemetry.get(engine_id, []), key=lambda r: r["cycle"])
        return pd.DataFrame([{c: r.get(c) for c in TELEMETRY_COLUMNS} for r in rows], columns=list(TELEMETRY_COLUMNS))

    async def insert_telemetry(self, user, engine_id, rows, source):
        assert self._owned(user, engine_id), "RLS would reject this insert"
        existing = {r["cycle"] for r in self.telemetry.get(engine_id, [])}
        assert not existing & {r["cycle"] for r in rows}, "unique (engine_id, cycle) violated"
        self.telemetry.setdefault(engine_id, []).extend({**r, "source": source} for r in rows)

    async def delete_telemetry(self, user, engine_id):
        if self._owned(user, engine_id):
            self.telemetry[engine_id] = []

    async def insert_assessment(self, user, record):
        assert self._owned(user, record["engine_id"])
        row = {"id": str(uuid.uuid4()), "created_at": now(), "created_by": user.id, **record}
        self.assessments.append(row)
        return row

    async def list_assessments(self, user, engine_id, limit=50):
        if not self._owned(user, engine_id):
            return []
        return [a for a in reversed(self.assessments) if a["engine_id"] == engine_id][:limit]


class MemoryAuth:
    async def user_for(self, token):
        return {u.token: u for u in (ALICE, BOB)}.get(token)


@pytest.fixture(scope="session")
def model() -> RulModel:
    return RulModel()


@pytest.fixture
def repo() -> MemoryRepository:
    return MemoryRepository()


@pytest.fixture
def client(repo, model):
    settings = Settings(supabase_url="http://supabase.invalid", supabase_anon_key="anon")
    app = create_app(settings, repo=repo, auth=MemoryAuth(), model=model)
    with TestClient(app) as c:
        yield c


def auth(user: User = ALICE) -> dict:
    return {"Authorization": f"Bearer {user.token}"}
