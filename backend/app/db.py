"""Supabase access through its REST APIs (GoTrue for auth, PostgREST for data).

Every data request carries the caller's access token, so Postgres row-level
security decides what each user can read and write.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
import pandas as pd

from app.ml.cmapss import ALL_SENSORS, SETTINGS

TELEMETRY_COLUMNS = ("cycle", *SETTINGS, *ALL_SENSORS)
PAGE_SIZE = 1000  # PostgREST's default max rows per response on Supabase
INSERT_CHUNK = 500


class DatabaseError(Exception):
    """A Supabase request failed. The message is safe to show to the user."""


@dataclass(frozen=True)
class User:
    id: str
    email: str | None
    token: str


class Repository(Protocol):
    """Data access used by the API. Supabase in production, in-memory in tests."""

    async def list_engines(self, user: User) -> list[dict]: ...
    async def get_engine(self, user: User, engine_id: str) -> dict | None: ...
    async def create_engine(self, user: User, fields: dict) -> dict: ...
    async def update_engine(self, user: User, engine_id: str, fields: dict) -> dict: ...
    async def delete_engine(self, user: User, engine_id: str) -> None: ...
    async def get_telemetry(self, user: User, engine_id: str) -> pd.DataFrame: ...
    async def insert_telemetry(self, user: User, engine_id: str, rows: list[dict], source: str) -> None: ...
    async def delete_telemetry(self, user: User, engine_id: str) -> None: ...
    async def insert_assessment(self, user: User, record: dict) -> dict: ...
    async def list_assessments(self, user: User, engine_id: str, limit: int = 50) -> list[dict]: ...


class SupabaseAuth:
    """Validates access tokens with Supabase Auth, with a short in-memory cache."""

    def __init__(self, client: httpx.AsyncClient, url: str, anon_key: str, ttl: float = 60.0):
        self._client = client
        self._url = url
        self._anon_key = anon_key
        self._ttl = ttl
        self._cache: dict[str, tuple[float, User]] = {}

    async def user_for(self, token: str) -> User | None:
        now = time.monotonic()
        hit = self._cache.get(token)
        if hit and hit[0] > now:
            return hit[1]
        try:
            r = await self._client.get(
                f"{self._url}/auth/v1/user",
                headers={"apikey": self._anon_key, "Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as e:
            raise DatabaseError("Could not reach the authentication service") from e
        if r.status_code != 200:
            return None
        body = r.json()
        user = User(id=body["id"], email=body.get("email"), token=token)
        if len(self._cache) > 1000:
            self._cache = {k: v for k, v in self._cache.items() if v[0] > now}
        self._cache[token] = (now + self._ttl, user)
        return user


class SupabaseRepository:
    def __init__(self, client: httpx.AsyncClient, url: str, anon_key: str):
        self._client = client
        self._rest = f"{url}/rest/v1"
        self._anon_key = anon_key

    # -------------------------------------------------------------- plumbing

    def _headers(self, user: User, **extra: str) -> dict[str, str]:
        return {"apikey": self._anon_key, "Authorization": f"Bearer {user.token}", **extra}

    async def _request(self, method: str, path: str, user: User, *, params=None, json=None, headers=None) -> Any:
        try:
            r = await self._client.request(
                method, f"{self._rest}/{path}", params=params, json=json, headers=self._headers(user, **(headers or {}))
            )
        except httpx.HTTPError as e:
            raise DatabaseError("Could not reach the database") from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("message", r.text)
            except ValueError:
                detail = r.text
            raise DatabaseError(f"Database request failed ({r.status_code}): {detail}")
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    # --------------------------------------------------------------- engines

    async def list_engines(self, user: User) -> list[dict]:
        return await self._request("GET", "engines", user, params={"select": "*", "order": "created_at.desc"})

    async def get_engine(self, user: User, engine_id: str) -> dict | None:
        rows = await self._request("GET", "engines", user, params={"select": "*", "id": f"eq.{engine_id}"})
        return rows[0] if rows else None

    async def create_engine(self, user: User, fields: dict) -> dict:
        rows = await self._request(
            "POST", "engines", user, json={**fields, "owner_id": user.id}, headers={"Prefer": "return=representation"}
        )
        return rows[0]

    async def update_engine(self, user: User, engine_id: str, fields: dict) -> dict:
        rows = await self._request(
            "PATCH",
            "engines",
            user,
            params={"id": f"eq.{engine_id}"},
            json=fields,
            headers={"Prefer": "return=representation"},
        )
        if not rows:
            raise DatabaseError("Engine not found")
        return rows[0]

    async def delete_engine(self, user: User, engine_id: str) -> None:
        await self._request("DELETE", "engines", user, params={"id": f"eq.{engine_id}"})

    # ------------------------------------------------------------- telemetry

    async def get_telemetry(self, user: User, engine_id: str) -> pd.DataFrame:
        rows: list[dict] = []
        offset = 0
        while True:
            page = await self._request(
                "GET",
                "telemetry",
                user,
                params={
                    "select": ",".join(TELEMETRY_COLUMNS),
                    "engine_id": f"eq.{engine_id}",
                    "cycle": "not.is.null",
                    "order": "cycle.asc",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                },
            )
            rows += page
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return pd.DataFrame(rows, columns=list(TELEMETRY_COLUMNS))

    async def insert_telemetry(self, user: User, engine_id: str, rows: list[dict], source: str) -> None:
        payload = [{"engine_id": engine_id, "source": source, **r} for r in rows]
        for i in range(0, len(payload), INSERT_CHUNK):
            await self._request(
                "POST", "telemetry", user, json=payload[i : i + INSERT_CHUNK], headers={"Prefer": "return=minimal"}
            )

    async def delete_telemetry(self, user: User, engine_id: str) -> None:
        await self._request("DELETE", "telemetry", user, params={"engine_id": f"eq.{engine_id}"})

    # ----------------------------------------------------------- assessments

    async def insert_assessment(self, user: User, record: dict) -> dict:
        rows = await self._request(
            "POST",
            "assessments",
            user,
            json={**record, "created_by": user.id},
            headers={"Prefer": "return=representation"},
        )
        return rows[0]

    async def list_assessments(self, user: User, engine_id: str, limit: int = 50) -> list[dict]:
        return await self._request(
            "GET",
            "assessments",
            user,
            params={
                "select": "id,cycle,status,rul,rul_low,rul_high,failure_probability,summary,model_version,created_at",
                "engine_id": f"eq.{engine_id}",
                "order": "created_at.desc",
                "limit": limit,
            },
        )
