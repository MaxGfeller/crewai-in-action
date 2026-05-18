"""Observability listener.

Writes a compact JSONL trace of every flow/method/LLM/crew event to
``artifacts/runs/<run_id>/events.jsonl`` and a terminal ``state.json``
snapshot when the Flow finishes.

The chapter uses this module to explain how CrewAI's event bus graduates
earlier chapters' ``print`` debugging into something you can actually
hand to a support engineer on call.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from crewai.events import (
    BaseEventListener,
    CrewKickoffCompletedEvent,
    CrewKickoffStartedEvent,
    FlowFinishedEvent,
    FlowStartedEvent,
    LLMCallCompletedEvent,
    LLMCallStartedEvent,
    MethodExecutionFailedEvent,
    MethodExecutionFinishedEvent,
    MethodExecutionStartedEvent,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class SupportFlowObservability(BaseEventListener):
    """Records every interesting event to disk.

    One listener instance covers a single run; :func:`register_listeners`
    creates it and keeps a reference alive. Events without an obvious
    run anchor still get logged as best-effort (the listener always has
    an open file because the ``FlowStartedEvent`` fires first).
    """

    def __init__(self, run_id: str, artifacts_root: Optional[Path] = None) -> None:
        self._run_id = run_id
        self._artifacts_root = artifacts_root or (_project_root() / "artifacts")
        self._run_dir = self._artifacts_root / "runs" / run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._run_dir / "events.jsonl"
        self._state_path = self._run_dir / "state.json"
        # Track per-method timing so we can emit duration_ms.
        self._method_start_ns: dict[str, int] = {}
        self._llm_start_ns: dict[str, int] = {}
        super().__init__()

    # ------------------------------------------------------------------
    # File writing
    # ------------------------------------------------------------------
    def _emit(self, payload: dict[str, Any]) -> None:
        payload.setdefault("ts", _now_iso())
        payload.setdefault("run_id", self._run_id)
        try:
            with self._events_path.open("a") as fh:
                fh.write(json.dumps(payload, default=str) + "\n")
        except Exception as exc:  # pragma: no cover
            print(f"[events] failed to write event: {exc}", file=sys.stderr)

    # ------------------------------------------------------------------
    # setup_listeners - called by BaseEventListener.__init__
    # ------------------------------------------------------------------
    def setup_listeners(self, crewai_event_bus: Any) -> None:  # type: ignore[override]
        @crewai_event_bus.on(FlowStartedEvent)
        def _flow_started(_src: Any, event: FlowStartedEvent) -> None:
            self._emit({
                "event": "flow_started",
                "flow_name": getattr(event, "flow_name", None),
                "flow_id": getattr(event, "flow_id", None),
            })

        @crewai_event_bus.on(FlowFinishedEvent)
        def _flow_finished(_src: Any, event: FlowFinishedEvent) -> None:
            self._emit({
                "event": "flow_finished",
                "flow_name": getattr(event, "flow_name", None),
                "flow_id": getattr(event, "flow_id", None),
            })
            # Try to snapshot the final state from the event source.
            state = getattr(event, "result", None)
            if state is None:
                state = getattr(_src, "state", None)
            if state is not None:
                self._dump_state(state)

        @crewai_event_bus.on(MethodExecutionStartedEvent)
        def _method_start(_src: Any, event: MethodExecutionStartedEvent) -> None:
            name = getattr(event, "method_name", None) or getattr(event, "name", "?")
            self._method_start_ns[name] = time.monotonic_ns()
            self._emit({"event": "method_started", "method": name})

        @crewai_event_bus.on(MethodExecutionFinishedEvent)
        def _method_finished(_src: Any, event: MethodExecutionFinishedEvent) -> None:
            name = getattr(event, "method_name", None) or getattr(event, "name", "?")
            duration_ms = self._duration_ms(self._method_start_ns.pop(name, None))
            self._emit({"event": "method_finished", "method": name, "duration_ms": duration_ms})

        @crewai_event_bus.on(MethodExecutionFailedEvent)
        def _method_failed(_src: Any, event: MethodExecutionFailedEvent) -> None:
            name = getattr(event, "method_name", None) or getattr(event, "name", "?")
            error = getattr(event, "error", None) or getattr(event, "exception", None)
            self._emit({"event": "method_failed", "method": name, "error": str(error)})
            print(f"[flow] method failed: {name}: {error}", file=sys.stderr)

        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def _crew_start(_src: Any, event: CrewKickoffStartedEvent) -> None:
            self._emit({
                "event": "crew_kickoff_started",
                "crew_name": getattr(event, "crew_name", None),
            })

        @crewai_event_bus.on(CrewKickoffCompletedEvent)
        def _crew_end(_src: Any, event: CrewKickoffCompletedEvent) -> None:
            self._emit({
                "event": "crew_kickoff_completed",
                "crew_name": getattr(event, "crew_name", None),
            })

        @crewai_event_bus.on(LLMCallStartedEvent)
        def _llm_start(_src: Any, event: LLMCallStartedEvent) -> None:
            key = str(getattr(event, "id", id(event)))
            self._llm_start_ns[key] = time.monotonic_ns()
            self._emit({
                "event": "llm_call_started",
                "model": getattr(event, "model", None),
                "id": key,
            })

        @crewai_event_bus.on(LLMCallCompletedEvent)
        def _llm_end(_src: Any, event: LLMCallCompletedEvent) -> None:
            key = str(getattr(event, "id", id(event)))
            duration_ms = self._duration_ms(self._llm_start_ns.pop(key, None))
            self._emit({
                "event": "llm_call_completed",
                "model": getattr(event, "model", None),
                "id": key,
                "duration_ms": duration_ms,
            })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _duration_ms(start_ns: Optional[int]) -> Optional[int]:
        if start_ns is None:
            return None
        return int((time.monotonic_ns() - start_ns) / 1_000_000)

    def _dump_state(self, state: Any) -> None:
        try:
            if hasattr(state, "model_dump_json"):
                self._state_path.write_text(state.model_dump_json(indent=2))
            else:
                self._state_path.write_text(json.dumps(state, default=str, indent=2))
        except Exception as exc:  # pragma: no cover
            print(f"[events] failed to dump state: {exc}", file=sys.stderr)


# Module-level reference so listeners aren't garbage-collected mid-run.
_ACTIVE_LISTENERS: list[SupportFlowObservability] = []


def register_listeners(run_id: str, artifacts_root: Optional[Path] = None) -> SupportFlowObservability:
    """Instantiate and register a single observability listener for ``run_id``."""
    listener = SupportFlowObservability(run_id=run_id, artifacts_root=artifacts_root)
    _ACTIVE_LISTENERS.append(listener)
    return listener
