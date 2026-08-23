"""Action routes: run, pull, tune.

Each wraps the same core objects (LauncherService, TuningEngine) the CLI
uses — this route layer is deliberately thin. It should never re-implement
decision logic that already lives in llm_max.launcher/llm_max.autotune.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from llm_max.adapters.base import RuntimeAdapter
from llm_max.autotune import RuntimeUnavailableError as TuneRuntimeUnavailableError
from llm_max.autotune import TuningEngine, TuningSession
from llm_max.catalog import load_catalog
from llm_max.launcher import LauncherService, RuntimeUnavailableError
from llm_max.storage.base import Storage

from app.dependencies import get_adapter, get_storage
from app.schemas.requests import RunRequest, TuneRequest

router = APIRouter(tags=["actions"])


def _find_model_spec(model_id: str):
    return next((m for m in load_catalog() if m.id == model_id), None)


@router.post("/models/{model_id}/pull")
def pull(model_id: str, adapter: RuntimeAdapter = Depends(get_adapter), storage: Storage = Depends(get_storage)):
    """Stream pull progress as newline-delimited JSON (one event per
    line) so a web client can render a live progress bar the same way the
    CLI does, without polling."""
    service = LauncherService(adapter=adapter, storage=storage)

    def event_stream():
        try:
            for event in service.pull(model_id):
                yield json.dumps(event) + "\n"
        except RuntimeUnavailableError as exc:
            yield json.dumps({"error": str(exc)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/models/{model_id}/run")
def run(
    model_id: str,
    body: RunRequest,
    adapter: RuntimeAdapter = Depends(get_adapter),
    storage: Storage = Depends(get_storage),
) -> dict:
    """Run a prompt against a model, hardware-tuned if it's in the
    catalog, and persist the result — same behavior as `llm-max run`."""
    service = LauncherService(adapter=adapter, storage=storage)
    model_spec = _find_model_spec(model_id)

    try:
        result = service.run(model_id, body.prompt, model_spec=model_spec)
    except RuntimeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {**{k: v for k, v in result.items() if k != "run_record"}, "run_record": result["run_record"].model_dump()}


@router.post("/models/{model_id}/tune", response_model=TuningSession)
def tune(
    model_id: str,
    body: TuneRequest,
    adapter: RuntimeAdapter = Depends(get_adapter),
    storage: Storage = Depends(get_storage),
) -> TuningSession:
    """One-shot benchmark-and-tune, same as `llm-max tune`. Set
    dry_run=true to benchmark and see the recommendation without applying
    it."""
    engine = TuningEngine(adapter=adapter, storage=storage)
    model_spec = _find_model_spec(model_id)

    try:
        session = engine.tune_once(model_id, model_spec=model_spec)
    except TuneRuntimeUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if session.outcome.value == "accepted_new" and not body.dry_run:
        engine.apply(session)

    return session