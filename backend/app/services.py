"""Engine workflows shared by the API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool

from app import replay
from app.config import Settings
from app.db import Repository, User
from app.ingest import UploadError
from app.ml.model import RulModel

TOP_CONTRIBUTIONS_STORED = 8


class NotFound(Exception):
    pass


async def load_engine(repo: Repository, user: User, engine_id: str) -> dict:
    engine = await repo.get_engine(user, engine_id)
    if engine is None:
        raise NotFound("Engine not found")
    return engine


def replay_info(engine: dict) -> dict | None:
    return (engine.get("metadata") or {}).get("replay")


async def analyze(repo: Repository, model: RulModel, user: User, engine: dict) -> dict:
    """Engine, live analysis of its full history, and stored assessment history."""
    history = await repo.get_telemetry(user, engine["id"])
    assessments = await repo.list_assessments(user, engine["id"])
    analysis = None
    if not history.empty:
        analysis = await run_in_threadpool(model.assess, history)
        info = replay_info(engine)
        if info:
            source = replay.ReplaySource(info["dataset"], info["unit"], info["length"], info["final_rul"])
            for point in analysis["trajectory"]:
                point["true_rul"] = source.true_rul(point["cycle"])
    return {"engine": engine, "analysis": analysis, "assessments": assessments}


async def assess_and_store(repo: Repository, model: RulModel, user: User, engine: dict) -> dict:
    """Assess the engine, save the result, and update its fleet summary."""
    result = await analyze(repo, model, user, engine)
    a = result["analysis"]
    if a is None:
        return result
    record = {
        "engine_id": engine["id"],
        "cycle": a["cycle"],
        "status": a["status"],
        "rul": a["rul"],
        "rul_low": a["rul_low"],
        "rul_high": a["rul_high"],
        "failure_probability": a["failure_probability"],
        "summary": a["explanation"]["summary"],
        "contributions": a["explanation"]["contributions"][:TOP_CONTRIBUTIONS_STORED],
        "model_version": a["model_version"],
    }
    saved = await repo.insert_assessment(user, record)
    health = {k: record[k] for k in ("status", "rul", "rul_low", "rul_high", "failure_probability", "cycle", "model_version")}
    health["assessed_at"] = saved.get("created_at") or datetime.now(timezone.utc).isoformat()
    result["engine"] = await repo.update_engine(user, engine["id"], {"health": health})
    result["assessments"] = [saved, *result["assessments"]]
    return result


async def append_history(
    repo: Repository, settings: Settings, user: User, engine: dict, rows: list[dict], source: str, replace: bool
) -> None:
    if replay_info(engine):
        raise UploadError("This engine replays a NASA test engine. Create a new engine to upload your own data.")
    if replace:
        await repo.delete_telemetry(user, engine["id"])
        existing = 0
        last_cycle = 0
    else:
        history = await repo.get_telemetry(user, engine["id"])
        existing = len(history)
        last_cycle = int(history["cycle"].max()) if existing else 0
    if rows[0]["cycle"] <= last_cycle:
        raise UploadError(
            f"New readings must start after the last recorded cycle ({last_cycle}). "
            "Choose 'replace' to overwrite the history."
        )
    if existing + len(rows) > settings.max_history_cycles:
        raise UploadError(f"An engine can hold at most {settings.max_history_cycles} cycles.")
    await repo.insert_telemetry(user, engine["id"], rows, source)


async def step_replay(repo: Repository, model: RulModel, settings: Settings, user: User, engine: dict, steps: int) -> dict:
    info = replay_info(engine)
    if not info:
        raise UploadError("Only replay engines can be advanced.")
    source = replay.ReplaySource(info["dataset"], info["unit"], info["length"], info["final_rul"])
    cursor = int(info["cursor"])
    target = min(source.length, cursor + steps)
    if target > cursor:
        rows = replay.cycles(settings.data_dir, source, cursor, target)
        await repo.insert_telemetry(user, engine["id"], rows, "replay")
        metadata = {**(engine.get("metadata") or {}), "replay": {**info, "cursor": target}}
        engine = await repo.update_engine(user, engine["id"], {"metadata": metadata})
    return await assess_and_store(repo, model, user, engine)


async def create_demo_fleet(repo: Repository, model: RulModel, settings: Settings, user: User, size: int) -> list[dict]:
    existing = await repo.list_engines(user)
    names = {e["engine_id"] for e in existing}
    created = []
    for source, start in replay.pick_demo_fleet(settings.data_dir, size + len(existing)):
        name = f"{source.dataset}-{source.unit:03d}"
        if name in names:
            continue
        engine = await repo.create_engine(
            user,
            {
                "engine_id": name,
                "model": f"C-MAPSS {source.dataset} replay",
                "serial_number": f"NASA-{source.dataset}-U{source.unit}",
                "metadata": {
                    "replay": {
                        "dataset": source.dataset,
                        "unit": source.unit,
                        "length": source.length,
                        "final_rul": source.final_rul,
                        "cursor": start,
                    }
                },
            },
        )
        await repo.insert_telemetry(user, engine["id"], replay.cycles(settings.data_dir, source, 0, start), "replay")
        result = await assess_and_store(repo, model, user, engine)
        created.append(result["engine"])
        names.add(name)
        if len(created) == size:
            break
    return created
