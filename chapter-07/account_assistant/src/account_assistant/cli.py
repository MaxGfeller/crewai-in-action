"""CLI entry points for the account assistant conversation flow."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import httpx

from account_assistant.conversation import get_conversation_service
from account_assistant.flow import AccountAssistantFlow
from account_assistant.flow_figure import patch_png_export_button, render_flow_png
from account_assistant.settings import account_service_url, require_openai_api_key


def _check_account_service() -> None:
    url = account_service_url()
    try:
        resp = httpx.get(f"{url}/health", timeout=2.0)
        resp.raise_for_status()
    except Exception as exc:
        print(
            f"[account-assistant] account-service is not reachable at {url} ({exc}).\n"
            "In another terminal:\n"
            "  cd ../account-service\n"
            "  uv run account-service",
            file=sys.stderr,
        )
        raise SystemExit(2)


def _artifacts_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def chat_once() -> None:
    parser = argparse.ArgumentParser(description="Run one assistant chat turn.")
    parser.add_argument("message", help="User message to send.")
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--account", default=None, help="Optional active account id.")
    args = parser.parse_args()

    require_openai_api_key()
    _check_account_service()
    result = get_conversation_service().run_turn(
        message=args.message,
        thread_id=args.thread_id,
        active_account_id=args.account,
    )
    print(f"[thread] {result.thread_id}")
    print(result.reply)
    if result.state.ui_surfaces:
        print(f"\n[ui surfaces] {len(result.state.ui_surfaces)}")
    if result.state.pending_actions:
        print(f"[pending actions] {len(result.state.pending_actions)}")


def chat() -> None:
    parser = argparse.ArgumentParser(description="Interactive account assistant chat.")
    parser.add_argument("--thread-id", default=f"thread_{uuid4().hex[:8]}")
    parser.add_argument("--account", default=None, help="Optional active account id.")
    args = parser.parse_args()

    require_openai_api_key()
    _check_account_service()
    service = get_conversation_service()
    print(f"[thread] {args.thread_id}")
    print("Type Ctrl-D or 'exit' to quit.")
    while True:
        try:
            message = input("\nYou: ").strip()
        except EOFError:
            print()
            break
        if message.lower() in {"exit", "quit"}:
            break
        if not message:
            continue
        result = service.run_turn(
            message=message,
            thread_id=args.thread_id,
            active_account_id=args.account,
        )
        args.account = result.state.active_account_id or args.account
        print(f"\nAssistant: {result.reply}")


def plot() -> None:
    out_dir = _artifacts_root()
    flow = AccountAssistantFlow()
    tmp_html = Path(flow.plot("conversation_flow.html", show=False))
    for src in tmp_html.parent.iterdir():
        shutil.copy2(src, out_dir / src.name)
    final = out_dir / "conversation_flow.html"
    final_png = render_flow_png(flow, out_dir / "conversation_flow.png")
    patch_png_export_button(out_dir / "conversation_flow_script.js", final_png.name)
    print(f"[plot] wrote {final}")
    print(f"[plot] wrote {final_png}")


def test() -> None:
    require_openai_api_key()
    _check_account_service()
    print("ok")
