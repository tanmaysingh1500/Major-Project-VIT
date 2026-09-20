"""
RAG-lite Policy Q&A service.

Per the synopsis, the full system calls for sentence-transformers embeddings
+ a Chroma vector store. In THIS environment there is no network access to
download a sentence-transformers model from Hugging Face, so this MVP swaps
in a scikit-learn TfidfVectorizer + cosine similarity over locally-stored
chunks — same retrieval interface (embed corpus once, embed query, rank by
similarity), zero external downloads, fully local. Swapping back to
sentence-transformers + Chroma later only touches this file: build_index()
and retrieve() are the seam.

Design choice consistent with the project's core principle ("numbers are
computed, not hallucinated"): there is NO LLM call here. The "answer" to a
policy question is the most relevant retrieved chunk(s) themselves, returned
verbatim with their source document and last-verified date — never a
model-generated paraphrase that could invent unsupported claims. A real LLM
answer-generation step grounded in these chunks is a natural "Later"
upgrade (see ARCHITECTURE.md) once an API key is available.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import POLICY_CORPUS_DIR


@dataclass
class Chunk:
    doc_title: str
    doc_filename: str
    last_verified: str
    disclaimer: str
    text: str


def _parse_markdown_with_frontmatter(path) -> tuple[dict, str]:
    raw = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not match:
        return {}, raw
    frontmatter_text, body = match.groups()
    meta = yaml.safe_load(frontmatter_text) or {}
    return meta, body


def _chunk_body(body: str) -> list[str]:
    """Split a markdown doc into paragraph-level chunks (blank-line separated),
    dropping empty/whitespace-only chunks and standalone headings-only lines
    shorter than a sentence, so retrieval matches on substantive content."""
    raw_chunks = [c.strip() for c in body.split("\n\n")]
    return [c for c in raw_chunks if len(c) > 40]


def _load_corpus() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(POLICY_CORPUS_DIR.glob("*.md")):
        meta, body = _parse_markdown_with_frontmatter(path)
        for text in _chunk_body(body):
            chunks.append(
                Chunk(
                    doc_title=meta.get("title", path.stem),
                    doc_filename=path.name,
                    last_verified=str(meta.get("last_verified", "unknown")),
                    disclaimer=meta.get("disclaimer", "").strip(),
                    text=text,
                )
            )
    return chunks


@lru_cache(maxsize=1)
def build_index():
    """Builds (and caches) the TF-IDF index over the local policy corpus.
    Cheap enough (a handful of documents) to build lazily on first use."""
    chunks = _load_corpus()
    corpus_texts = [c.text for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus_texts) if corpus_texts else None
    return {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    index = build_index()
    chunks = index["chunks"]
    if not chunks:
        return []

    vectorizer: TfidfVectorizer = index["vectorizer"]
    matrix = index["matrix"]

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix)[0]

    ranked_idx = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in ranked_idx:
        if scores[idx] <= 0:
            continue
        chunk = chunks[idx]
        results.append(
            {
                "text": chunk.text,
                "source_document": chunk.doc_title,
                "source_filename": chunk.doc_filename,
                "last_verified": chunk.last_verified,
                "disclaimer": chunk.disclaimer,
                "relevance_score": round(float(scores[idx]), 4),
            }
        )
    return results


def answer_question(query: str, top_k: int = 3) -> dict:
    """RAG-lite 'answer': the top retrieved chunk(s), returned verbatim with
    citations — no LLM paraphrase, so nothing here can be hallucinated beyond
    what's literally in the sample corpus."""
    results = retrieve(query, top_k=top_k)
    if not results:
        return {
            "query": query,
            "answer_found": False,
            "answer": (
                "No relevant information was found in the sample policy corpus "
                "for this question. Try rephrasing, or note that this MVP's "
                "corpus only covers FAME-II basics, a few state EV policies, "
                "public charging norms, and registration/road tax treatment."
            ),
            "sources": [],
        }

    return {
        "query": query,
        "answer_found": True,
        "answer": results[0]["text"],
        "sources": results,
    }
