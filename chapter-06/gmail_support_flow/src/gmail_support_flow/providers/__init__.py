"""Provider factories.

``PROVIDERS_MODE`` (``fake`` by default) picks between the local-only fake
implementations and the real Gmail/Slack SDK-backed ones. The Flow itself is
oblivious to which is live - everything goes through the Protocols defined
in :mod:`providers.base`.
"""

from __future__ import annotations

import os

from gmail_support_flow.providers.base import GmailProvider, SlackProvider


def _mode() -> str:
    return os.getenv("PROVIDERS_MODE", "fake").lower()


def get_gmail_provider() -> GmailProvider:
    mode = _mode()
    if mode == "real":
        from gmail_support_flow.providers.gmail_real import GmailReal
        return GmailReal()
    from gmail_support_flow.providers.gmail_fake import GmailFake
    return GmailFake()


def get_slack_provider() -> SlackProvider:
    mode = _mode()
    if mode == "real":
        from gmail_support_flow.providers.slack_real import SlackReal
        return SlackReal()
    from gmail_support_flow.providers.slack_fake import SlackFake
    return SlackFake()


__all__ = ["GmailProvider", "SlackProvider", "get_gmail_provider", "get_slack_provider"]
