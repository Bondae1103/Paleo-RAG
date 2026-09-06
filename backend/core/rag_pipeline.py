"""
End-to-end RAG orchestration: query expansion -> hybrid retrieval (dense +
BM25 via RRF) -> prompt construction -> LLM generation -> post-hoc citation
faithfulness check.

The BM25 sparse index here uses `rank_bm25` (in-process), matching the
`sparse_retrieval_backend = "rank_bm25"` default in config.py. See
DECISIONS.md for why this was chosen over Qdrant-native sparse vectors for
the initial build (simpler to stand up without extra Qdrant sparse-vector
config; swappable later behind the same interface).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from backend.core.embeddings import EmbeddingModel
from backend.core.llm_client import LLMClient
from backend.core.query_expansion import ExpandedQuery, expand_query
from backend.core.vector_store import SearchFilters, SearchResult, VectorStore
from backend.utils.taxonomy_client import TaxonomyClient

CITATION_MARKER_RE = re.compile(r"\[([\w\-.]+):(\d+)\]")

PROMPT_TEMPLATE = """You are a scientific research assistant answering questions about paleogenomics using ONLY the context provided below.

Rules:
1. Answer only using facts present in the context. Do not use outside knowledge.
2. Every factual claim must be followed by an inline citation marker in the exact form [doc_id:chunk_index], referencing the chunk it came from.
3. If the context does not contain enough information to answer, say exactly: "The provided literature does not address this." Do not guess or fabricate an answer.

Context:
{context}

Question: {question}

Answer:"""


@dataclass
class CitationWarning:
    cited_marker: str
    reason: str


@dataclass
class RagAnswer:
    text: str
    retrieved_chunks: list[SearchResult]
    citation_warnings: list[CitationWarning] = field(default_factory=list)


class BM25SparseIndex:
    """Thin wrapper around rank_bm25 so it can be rebuilt per-corpus-snapshot
    and queried with the same (doc_id, chunk_index) key shape the vector
    store's hybrid_search expects."""

    def __init__(self) -> None:
        self._bm25 = None
        self._keys: list[tuple[str, int]] = []

    def build(self, corpus: list[tuple[tuple[str, int], str]]) -> None:
        from rank_bm25 import BM25Okapi

        self._keys = [key for key, _ in corpus]
        tokenized = [text.lower().split() for _, text in corpus]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def sync_from_vector_store(self, vector_store: VectorStore) -> None:
        """Fetch all chunks from the vector store and build the BM25 index."""
        corpus = vector_store.scroll_all_chunks()
        self.build(corpus)

    def rank(self, query_terms: list[str], top_k: int) -> list[tuple[str, int]]:
        if self._bm25 is None or not self._keys:
            return []
        scores = self._bm25.get_scores([t.lower() for t in query_terms])
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self._keys[i] for i in ranked_indices]


def build_prompt(question: str, chunks: list[SearchResult]) -> str:
    context_parts = [f"[{c.doc_id}:{c.chunk_index}] ({c.section}) {c.text}" for c in chunks]
    return PROMPT_TEMPLATE.format(context="\n\n".join(context_parts), question=question)


def check_citations(answer_text: str, retrieved_chunks: list[SearchResult]) -> list[CitationWarning]:
    valid_keys = {(c.doc_id, c.chunk_index) for c in retrieved_chunks}
    warnings: list[CitationWarning] = []
    for match in CITATION_MARKER_RE.finditer(answer_text):
        doc_id, chunk_index_str = match.group(1), match.group(2)
        key = (doc_id, int(chunk_index_str))
        if key not in valid_keys:
            warnings.append(
                CitationWarning(
                    cited_marker=match.group(0),
                    reason="Citation does not correspond to any chunk retrieved for this query "
                    "(possible hallucination).",
                )
            )
    return warnings


class RagPipeline:
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        llm_client: LLMClient,
        taxonomy_client: TaxonomyClient,
        sparse_index: BM25SparseIndex,
        top_k: int = 8,
    ) -> None:
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.taxonomy_client = taxonomy_client
        self.sparse_index = sparse_index
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        known_taxa: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> tuple[ExpandedQuery, list[SearchResult]]:
        k = top_k or self.top_k
        if self.sparse_index._bm25 is None:
            try:
                self.sparse_index.sync_from_vector_store(self.vector_store)
            except Exception:
                pass
        expanded = expand_query(query, self.taxonomy_client, known_taxa=known_taxa)
        dense_vector = self.embedding_model.embed([expanded.dense_query_text])[0]
        sparse_ranked = self.sparse_index.rank(expanded.sparse_query_terms, top_k=max(k * 3, 20))
        results = self.vector_store.hybrid_search(
            query_vector=dense_vector,
            sparse_ranked_doc_keys=sparse_ranked,
            top_k=k,
            filters=filters,
        )
        return expanded, results

    async def answer_stream(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        known_taxa: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Streams answer text chunks; caller is responsible for collecting
        the full text if it needs to run check_citations() afterward (see
        api/routes.py for the SSE wiring that does exactly this)."""
        _, chunks = self.retrieve(query, filters=filters, known_taxa=known_taxa, top_k=top_k)
        prompt = build_prompt(query, chunks)
        async for piece in self.llm_client.stream(prompt):
            yield piece

    async def answer(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        known_taxa: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> RagAnswer:
        """Non-streaming convenience wrapper (used by eval/run_eval.py)."""
        _, chunks = self.retrieve(query, filters=filters, known_taxa=known_taxa, top_k=top_k)
        prompt = build_prompt(query, chunks)
        full_text = ""
        async for piece in self.llm_client.stream(prompt):
            full_text += piece
        warnings = check_citations(full_text, chunks)
        return RagAnswer(text=full_text, retrieved_chunks=chunks, citation_warnings=warnings)
