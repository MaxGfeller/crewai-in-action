"""Flow persistence wiring.

CrewAI ships :class:`crewai.flow.persistence.SQLiteFlowPersistence`; we
wrap it so the target path is driven by ``FLOW_PERSIST_DB_PATH`` and so
readers have a single :func:`resume_flow` entry point.

The resume helper demonstrates the idempotency contract the Flow is
expected to honour: posting the Slack escalation, in particular, reads
``state.slack_message_ts`` before acting.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from crewai.flow.persistence import SQLiteFlowPersistence

if TYPE_CHECKING:  # pragma: no cover - import cycle avoidance
    from gmail_support_flow.flow import SupportInboxFlow


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_persist_db_path() -> Path:
    raw = os.getenv("FLOW_PERSIST_DB_PATH", "artifacts/flow_state.sqlite")
    path = Path(raw)
    if not path.is_absolute():
        path = _project_root() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def default_persistence() -> SQLiteFlowPersistence:
    return SQLiteFlowPersistence(str(resolve_persist_db_path()))


def resume_flow(flow_id: str) -> "SupportInboxFlow":
    """Resume a previously kicked-off Flow by its id.

    ``@persist`` rehydrates prior state from the database when the Flow is
    instantiated with the matching id.
    """
    from gmail_support_flow.flow import SupportInboxFlow

    flow = SupportInboxFlow()
    flow.kickoff(inputs={"id": flow_id})
    return flow
