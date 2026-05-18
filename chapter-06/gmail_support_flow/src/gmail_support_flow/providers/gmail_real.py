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
    def list_unread(self, label: str, max_results: int = 20) -> list[dict]:
        query = "is:unread"
        if label:
            query += f" label:{label}"
        resp = self._service.users().messages().list(
            userId=self._user, q=query, maxResults=max_results
        ).execute()
        out: list[dict] = []
        for hit in resp.get("messages", []):
            msg = self._service.users().messages().get(
                userId=self._user, id=hit["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = self._fetch_body(msg["threadId"])
            out.append({
                "thread_id": msg["threadId"],
                "from_email": self._parse_email(headers.get("From", "")),
                "from_name": self._parse_name(headers.get("From", "")),
                "subject": headers.get("Subject", ""),
                "body": body,
                "received_at": headers.get("Date", ""),
                "labels": msg.get("labelIds", []),
            })
        return out

    def thread_by_id(self, thread_id: str) -> dict | None:
        try:
            thread = self._service.users().threads().get(
                userId=self._user, id=thread_id, format="full"
            ).execute()
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
        resp = self._service.users().labels().list(userId=self._user).execute()
        for lbl in resp.get("labels", []):
            if lbl["name"] == name:
                return lbl["id"]
        created = self._service.users().labels().create(
            userId=self._user, body={"name": name}
        ).execute()
        return created["id"]

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
