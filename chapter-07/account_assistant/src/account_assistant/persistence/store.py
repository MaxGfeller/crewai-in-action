"""Flow persistence wiring for the conversation workflow."""

from __future__ import annotations

import os
from pathlib import Path

from crewai.flow.persistence import SQLiteFlowPersistence

from account_assistant.settings import project_root


def resolve_persist_db_path() -> Path:
    raw = os.getenv("FLOW_PERSIST_DB_PATH", "artifacts/flow_state.sqlite")
    path = Path(raw)
    if not path.is_absolute():
        path = project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def default_persistence() -> SQLiteFlowPersistence:
    return SQLiteFlowPersistence(str(resolve_persist_db_path()))
