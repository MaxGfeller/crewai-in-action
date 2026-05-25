"""CLI entry points for the mocked account service."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def serve() -> None:
    import uvicorn

    host = os.getenv("ACCOUNT_SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("ACCOUNT_SERVICE_PORT", "8087"))
    print(f"[account-service] starting on http://{host}:{port}")
    uvicorn.run("account_service.app:app", host=host, port=port, reload=False)


def list_accounts() -> None:
    from account_service import store

    for account in store.list_accounts():
        print(
            f"{account.account_id:12} {account.name:22} "
            f"health={account.health:8} renewal={account.renewal_date}"
        )


def reset_artifacts() -> None:
    path = _package_root() / "artifacts"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    print(f"reset {path}")
