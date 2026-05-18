"""Real Gmail provider (``google-api-python-client``).

This module is only imported when ``PROVIDERS_MODE=real``. We never call
``users.messages.send`` - drafts and labels only. Human approval of the
draft is chapter 9's responsibility.
"""

from __future__ import annotations

import base64
import json
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception as exc:  # pragma: no cover - only raised in real mode
    build = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = exc
else:
    _IMPORT_ERROR = None


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    # `gmail.modify` is enough to list, label, and create drafts.
    # We intentionally do NOT request `gmail.send` - see chapter 9 (HITL).
]

SYSTEM_LABEL_IDS = {
    "inbox": "INBOX",
    "spam": "SPAM",
    "trash": "TRASH",
    "unread": "UNREAD",
    "starred": "STARRED",
    "important": "IMPORTANT",
    "sent": "SENT",
    "draft": "DRAFT",
    "drafts": "DRAFT",
    "category_personal": "CATEGORY_PERSONAL",
    "category_social": "CATEGORY_SOCIAL",
    "category_promotions": "CATEGORY_PROMOTIONS",
    "category_updates": "CATEGORY_UPDATES",
    "category_forums": "CATEGORY_FORUMS",
}


class GmailReal:
    def __init__(self) -> None:
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "Real Gmail provider requires google-api-python-client. "
                "Install deps or set PROVIDERS_MODE=fake."
            ) from _IMPORT_ERROR
        self._user = os.environ.get("GMAIL_USER_EMAIL") or "me"
        self._service = self._build_service()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    def _build_service(self) -> Any:
        creds_path = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if not creds_path:
            raise RuntimeError(
                "GOOGLE_CREDENTIALS_JSON not set. Point it to an OAuth "
                "client_secret JSON file or switch PROVIDERS_MODE=fake."
            )
        token_path = Path("artifacts") / "gmail_token.json"
        creds: Optional[Credentials] = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    # ------------------------------------------------------------------
    # GmailProvider surface
    # ------------------------------------------------------------------
    def list_threads(
        self, label: str, max_results: int = 20, unread_only: bool = False
    ) -> list[dict]:
        query = "is:unread" if unread_only else ""
        if label:
            query = f"{query} {self._label_query(label)}".strip()
        resp = self._service.users().messages().list(
            userId=self._user, q=query, maxResults=max_results
        ).execute()
        out: list[dict] = []
        seen_thread_ids: set[str] = set()
        for hit in resp.get("messages", []):
            msg = self._service.users().messages().get(
                userId=self._user, id=hit["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            thread_id = msg["threadId"]
            if thread_id in seen_thread_ids:
                continue
            seen_thread_ids.add(thread_id)
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = self._fetch_body(thread_id)
            out.append({
                "thread_id": thread_id,
                "from_email": self._parse_email(headers.get("From", "")),
                "from_name": self._parse_name(headers.get("From", "")),
                "subject": headers.get("Subject", ""),
                "body": body,
                "received_at": headers.get("Date", ""),
                "labels": msg.get("labelIds", []),
            })
        return out

    def list_unread(self, label: str, max_results: int = 20) -> list[dict]:
        return self.list_threads(label=label, max_results=max_results, unread_only=True)

    def thread_by_id(self, thread_id: str) -> dict | None:
        try:
            thread = self._service.users().threads().get(
                userId=self._user, id=thread_id, format="full"
            ).execute()
        except HttpError as exc:
            status = getattr(exc.resp, "status", "?")
            reason = getattr(exc.resp, "reason", "unknown error")
            if status == 404:
                return None
            raise RuntimeError(
                f"Gmail API rejected thread id {thread_id!r} ({status} {reason}). "
                "Use the API thread id shown by `uv run list-gmail-threads`, "
                "not the Gmail web URL id."
            ) from exc
        except Exception:
            return None
        first = thread["messages"][0]
        headers = {h["name"]: h["value"] for h in first["payload"]["headers"]}
        return {
            "thread_id": thread_id,
            "from_email": self._parse_email(headers.get("From", "")),
            "from_name": self._parse_name(headers.get("From", "")),
            "subject": headers.get("Subject", ""),
            "body": self._fetch_body(thread_id),
            "received_at": headers.get("Date", ""),
            "labels": first.get("labelIds", []),
        }

    def create_draft(
        self,
        thread_id: str,
        body_markdown: str,
        subject_prefix: str = "Re: ",
    ) -> str:
        thread = self._service.users().threads().get(
            userId=self._user, id=thread_id, format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        first = thread["messages"][0]
        headers = {h["name"]: h["value"] for h in first["payload"]["headers"]}
        to_addr = headers.get("From", "")
        subject = f"{subject_prefix}{headers.get('Subject', '')}"

        msg = EmailMessage()
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body_markdown)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

        draft = self._service.users().drafts().create(
            userId=self._user,
            body={"message": {"raw": raw, "threadId": thread_id}},
        ).execute()
        return draft["id"]

    def apply_labels(self, thread_id: str, labels: list[str]) -> None:
        label_ids = [self._ensure_label(l) for l in labels]
        self._service.users().threads().modify(
            userId=self._user,
            id=thread_id,
            body={"addLabelIds": label_ids},
        ).execute()

    def send(self, *args: Any, **kwargs: Any) -> None:
        # Forward-reference to chapter 9 (HITL). Never send from this chapter.
        raise NotImplementedError(
            "Auto-send is intentionally disabled. Human approval of drafts "
            "is covered in chapter 9 (human-in-the-loop)."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_label(self, name: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Gmail label name cannot be empty")
        resp = self._service.users().labels().list(userId=self._user).execute()
        for lbl in resp.get("labels", []):
            if lbl["id"] == cleaned or lbl["name"] == cleaned:
                return lbl["id"]
            if lbl["name"].casefold() == cleaned.casefold():
                return lbl["id"]
        system_label_id = SYSTEM_LABEL_IDS.get(cleaned.casefold())
        if system_label_id:
            return system_label_id
        created = self._service.users().labels().create(
            userId=self._user, body={"name": cleaned}
        ).execute()
        return created["id"]

    @staticmethod
    def _label_query(label: str) -> str:
        if any(ch.isspace() for ch in label):
            escaped = label.replace("\\", "\\\\").replace('"', '\\"')
            return f'label:"{escaped}"'
        return f"label:{label}"

    def _fetch_body(self, thread_id: str) -> str:
        thread = self._service.users().threads().get(
            userId=self._user, id=thread_id, format="full"
        ).execute()
        first = thread["messages"][0]
        payload = first.get("payload", {})
        return self._extract_text(payload) or ""

    def _extract_text(self, payload: dict[str, Any]) -> str:
        if payload.get("mimeType", "").startswith("text/plain"):
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []) or []:
            text = self._extract_text(part)
            if text:
                return text
        return ""

    @staticmethod
    def _parse_email(from_header: str) -> str:
        if "<" in from_header and ">" in from_header:
            return from_header.split("<", 1)[1].split(">", 1)[0].strip()
        return from_header.strip()

    @staticmethod
    def _parse_name(from_header: str) -> str | None:
        if "<" in from_header:
            return from_header.split("<", 1)[0].strip().strip('"') or None
        return None

    # Keeps json in module namespace (silences unused-import warnings).
    _json = json
