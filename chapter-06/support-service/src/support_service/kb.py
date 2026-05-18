"""BM25 knowledge-base search over ``data/fixtures/kb_articles.json``.

Kept deliberately minimal. The chapter is about Flows, not retrieval -
readers who want real RAG would swap this for a proper vector store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from support_service.models import KbArticle


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fixture_path() -> Path:
    return _package_root() / "data" / "fixtures" / "kb_articles.json"


def _tokenise(text: str) -> list[str]:
    return [tok for tok in text.lower().split() if tok]


class _Index:
    """Lazily-built BM25 index over the KB fixture.

    Loaded once per process on first search call - subsequent searches
    reuse the cached corpus and BM25 matrix.
    """

    def __init__(self) -> None:
        self._articles: list[KbArticle] = []
        self._bm25: Optional[BM25Okapi] = None

    def _load(self) -> None:
        with _fixture_path().open() as fh:
            raw = json.load(fh)
        self._articles = [KbArticle.model_validate(a) for a in raw]
        corpus = [_tokenise(f"{a.title} {a.body}") for a in self._articles]
        self._bm25 = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 3) -> list[KbArticle]:
        if self._bm25 is None:
            self._load()
        assert self._bm25 is not None
        tokens = _tokenise(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(self._articles, scores), key=lambda pair: pair[1], reverse=True
        )
        return [a for a, score in ranked[:top_k] if score > 0.0]


INDEX = _Index()
