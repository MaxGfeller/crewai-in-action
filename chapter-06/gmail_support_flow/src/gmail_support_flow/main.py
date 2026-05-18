"""CLI entry points for the chapter 6 Gmail support Flow.

These are exposed via ``[project.scripts]`` in ``pyproject.toml`` and map
to the verification plan at the bottom of the chapter:

- ``uv run gmail_support_flow``       → :func:`run` (whole inbox)
- ``uv run run-one -- --thread-id T`` → :func:`run_one`
- ``uv run plot``                     → :func:`plot`
- ``uv run replay -- --flow-id ID``   → :func:`replay`
- ``uv run test``                     → :func:`test`

Seeding the Customer 360 database is the support-service's job - see
``../support-service/README.md``. Start that service first, then run the
Flow here.

Every command that kicks a Flow sets ``GMAIL_FAKE_RUN_ID`` so the fake
Gmail provider writes drafts under ``artifacts/runs/<run_id>/``, matching
where :class:`SupportFlowObservability` writes ``events.jsonl`` and
``state.json``. One run, one directory.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from uuid import uuid4

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a declared dep
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _artifacts_root() -> Path:
    root = _project_root() / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _new_run_id() -> str:
    return uuid4().hex


def _bind_run_id(run_id: str) -> None:
    """Make the run id visible to the fake Gmail provider."""
    os.environ["GMAIL_FAKE_RUN_ID"] = run_id


def _register_obs(run_id: str):
    # Imported lazily so ``uv run seed`` doesn't need crewai installed.
    from gmail_support_flow.events import register_listeners

    return register_listeners(run_id=run_id)


def _new_flow():
    from gmail_support_flow.flow import SupportInboxFlow

    return SupportInboxFlow()


def _fixture_threads() -> list[dict]:
    path = _project_root() / "data" / "fixtures" / "inbox_tickets.json"
    with path.open() as fh:
        return json.load(fh)


def _load_thread_payload(thread_id: str) -> dict:
    """Look up one thread by id using whichever provider is live."""
    from gmail_support_flow.providers import get_gmail_provider

    provider = get_gmail_provider()
    thread_by_id = getattr(provider, "thread_by_id", None)
    if thread_by_id is None:
        raise RuntimeError(
            "The active Gmail provider does not expose thread_by_id(); "
            "either switch PROVIDERS_MODE=fake or pre-fetch the thread."
        )
    payload = thread_by_id(thread_id)
    if payload is None:
        raise KeyError(f"thread not found: {thread_id}")
    return payload


# ---------------------------------------------------------------------------
# support-service liveness check
# ---------------------------------------------------------------------------


def _check_support_service() -> None:
    """Fail fast with a helpful message if the support service is down.

    The Flow will also fail on the first tool call, but the error there
    is opaque (an ``httpx.ConnectError`` buried inside a Crew log). Doing
    the check up front points readers at ``../support-service``.
    """
    import httpx

    url = os.getenv("SUPPORT_SERVICE_URL", "http://127.0.0.1:8077").rstrip("/")
    try:
        resp = httpx.get(f"{url}/health", timeout=2.0)
        resp.raise_for_status()
    except Exception as exc:
        print(
            f"[main] support-service is not reachable at {url} ({exc}).\n"
            f"       In another terminal:\n"
            f"         cd ../support-service\n"
            f"         uv run seed          # first time only\n"
            f"         uv run support-service",
            file=sys.stderr,
        )
        sys.exit(2)


# ---------------------------------------------------------------------------
# plot
# ---------------------------------------------------------------------------


def plot() -> None:
    """Render ``artifacts/flow_diagram.html`` via ``Flow.plot``.

    CrewAI's ``Flow.plot()`` writes the HTML (and sibling CSS/JS) to a
    fresh ``tempfile.mkdtemp`` directory and returns that path. We copy
    the three files into ``artifacts/`` so the chapter's figure and the
    verification script point at a stable location.
    """
    import shutil

    out_dir = _artifacts_root()
    tmp_html = Path(_new_flow().plot("flow_diagram.html", show=False))
    tmp_dir = tmp_html.parent
    for src in tmp_dir.iterdir():
        shutil.copy2(src, out_dir / src.name)
    final = out_dir / "flow_diagram.html"
    print(f"[plot] wrote {final}")


# ---------------------------------------------------------------------------
# run-one
# ---------------------------------------------------------------------------


def run_one() -> None:
    """Process exactly one thread; used for the chapter's happy-path demo."""
    parser = argparse.ArgumentParser(description="Run the support Flow for one thread.")
    parser.add_argument(
        "--thread-id",
        required=True,
        help="Thread id from data/fixtures/inbox_tickets.json (fake mode) or real inbox.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Override the generated run id (advanced; normally leave unset).",
    )
    args = parser.parse_args()

    _check_support_service()

    run_id = args.run_id or _new_run_id()
    _bind_run_id(run_id)
    _register_obs(run_id)

    payload = _load_thread_payload(args.thread_id)
    print(f"[main] run_id={run_id} thread_id={args.thread_id}")

    flow = _new_flow()
    flow.kickoff(inputs={"thread_payload": payload, "run_id": run_id})
    _print_run_tail(run_id, flow)


# ---------------------------------------------------------------------------
# run (batch)
# ---------------------------------------------------------------------------


def run() -> None:
    """Process every unread thread in the fake inbox (chapter default)."""
    parser = argparse.ArgumentParser(description="Run the support Flow for the whole inbox.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of threads to process.",
    )
    args, _ = parser.parse_known_args()

    _check_support_service()

    from gmail_support_flow.providers import get_gmail_provider

    provider = get_gmail_provider()
    label = os.getenv("GMAIL_LABEL", "book-support-demo")
    threads = provider.list_unread(label=label, max_results=args.limit or 100)
    if args.limit is not None:
        threads = threads[: args.limit]
    if not threads:
        print(
            "[main] no threads to process - check data/fixtures/inbox_tickets.json"
        )
        return

    processed = 0
    drafted = 0
    escalated = 0
    spam = 0

    for payload in threads:
        run_id = _new_run_id()
        _bind_run_id(run_id)
        _register_obs(run_id)

        print(f"\n[main] ---- run_id={run_id} thread_id={payload['thread_id']} ----")
        flow = _new_flow()
        flow.kickoff(inputs={"thread_payload": payload, "run_id": run_id})
        state = flow.state
        processed += 1
        if state.draft_id:
            drafted += 1
        if state.escalated:
            escalated += 1
        if "spam" in (state.applied_labels or []):
            spam += 1

    print(
        f"\n[main] processed={processed} drafted={drafted} "
        f"escalated={escalated} spam={spam}"
    )


# ---------------------------------------------------------------------------
# replay
# ---------------------------------------------------------------------------


def replay() -> None:
    """Resume a previously kicked-off Flow from its persisted state."""
    parser = argparse.ArgumentParser(description="Resume a Flow by id.")
    parser.add_argument("--flow-id", required=True, help="Flow id (the state.id hex).")
    args = parser.parse_args()

    _bind_run_id(args.flow_id)
    _register_obs(args.flow_id)

    from gmail_support_flow.persistence.store import resume_flow

    flow = resume_flow(args.flow_id)
    _print_run_tail(args.flow_id, flow)


# ---------------------------------------------------------------------------
# test (smoke)
# ---------------------------------------------------------------------------


def test() -> None:
    """Run the full batch and assert Flow-level invariants.

    The chapter uses this to give readers a one-liner they can copy-paste
    to check that their edits didn't break anything material.
    """
    outbox = _artifacts_root() / "slack_outbox.jsonl"
    before = outbox.read_text().splitlines() if outbox.exists() else []
    before_count = len(before)

    run()

    after = outbox.read_text().splitlines() if outbox.exists() else []
    new_escalations = len(after) - before_count

    fixture_count = len(_fixture_threads())

    # The seed fixtures include exactly one poison thread (t_011) that
    # deterministically escalates after two retries. If the chapter adds
    # another poison row, update this expectation.
    expected_escalations = 1

    problems: list[str] = []
    if new_escalations != expected_escalations:
        problems.append(
            f"expected exactly {expected_escalations} new escalation(s), got {new_escalations}"
        )

    # Double-check: no one called GmailReal.send() either directly or via
    # a leaking fake. If the fake ever learns a send() method, revisit.
    from gmail_support_flow.providers.gmail_fake import GmailFake

    if hasattr(GmailFake, "send"):
        problems.append("GmailFake unexpectedly grew a send() method")

    if problems:
        for p in problems:
            print(f"[test] FAIL: {p}", file=sys.stderr)
        sys.exit(1)

    print(
        f"[test] OK: {fixture_count} threads processed, "
        f"{new_escalations} escalation(s), 0 sends"
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _print_run_tail(run_id: str, flow) -> None:
    """Print a tidy end-of-run summary pointing at the artifact files."""
    run_dir = _artifacts_root() / "runs" / run_id
    state = getattr(flow, "state", None)
    terminal = getattr(state, "terminal", None) if state is not None else None
    escalated = getattr(state, "escalated", None) if state is not None else None
    draft_id: Optional[str] = getattr(state, "draft_id", None) if state is not None else None
    print(
        f"[main] done: terminal={terminal} escalated={escalated} "
        f"draft_id={draft_id}"
    )
    print(f"[main] artifacts: {run_dir}")


if __name__ == "__main__":
    # Allow ``python -m gmail_support_flow.main run`` style invocation too.
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    {
        "run": run,
        "run_crew": run,
        "run-one": run_one,
        "plot": plot,
        "replay": replay,
        "test": test,
    }.get(cmd, run)()
