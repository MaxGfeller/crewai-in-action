"""Knowledge-base search tool - thin wrapper around the HTTP service.

The BM25 index itself lives server-side in ``../support-service``; this
tool just forwards the query. It deliberately surfaces ``httpx`` errors
rather than swallowing them, so the chapter's retry-via-router pattern
can observe HTTP failures in ``MethodExecutionFailedEvent``.
"""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from gmail_support_flow.services import get_support_service


class _KbArg(BaseModel):
    query: str = Field(description="Free-text search query.")
    top_k: int = Field(default=3, ge=1, le=10, description="Max articles to return.")


class SearchKbTool(BaseTool):
    name: str = "search_kb"
    description: str = (
        "Search the internal knowledge base for articles relevant to a query. "
        "Returns a JSON array of {id, theme, title, body} objects."
    )
    args_schema: type[BaseModel] = _KbArg

    def _run(self, query: str, top_k: int = 3) -> str:  # type: ignore[override]
        articles = get_support_service().search_kb(query, top_k=top_k)
        return json.dumps(articles)
