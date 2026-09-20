"""
RAG-lite Policy Q&A service.

Embeds the local policy corpus with a sentence-transformers model and
stores/queries the vectors in a local Chroma vector database. The corpus is
tiny (7 markdown files), so build_index() clears and rebuilds the Chroma
collection on every process start -- this guarantees the index always
reflects whatever is currently in data/policy_corpus/, with no separate
"reindex" step to remember to run after editing a doc.

Design choice consistent with the project's core principle ("numbers are
computed, not hallucinated"): there is NO LLM call here. The "answer" to a
policy question is the most relevant retrieved chunk(s) themselves, returned
verbatim with their source document and last-verified date -- never a
model-generated paraphrase that could invent unsupported claims. A real LLM
answer-generation step grounded in these chunks is a natural "Later"
upgrade (see ARCHITECTURE.md) once an API key is available.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import chromadb
import yaml
from chromadb.utils import embedding_functions

from app.config import POLICY_CHROMA_DIR, POLICY_CORPUS_DIR

COLLECTION_NAME = "policy_corpus"
# Small (~80MB), fast, well-established general-purpose sentence embedding
# model. Downloaded from Hugging Face on first run, then cached locally
# (~/.cache/huggingface) for every run after that.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


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
def _get_embedding_function():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def build_index():
    """Builds (and caches) the Chroma vector index over the local policy
    corpus. Rebuilds from scratch every process start so the index can never
    go stale relative to the markdown files on disk."""
    chunks = _load_corpus()

    client = chromadb.PersistentClient(path=str(POLICY_CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # nothing to delete on a fresh DB directory

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=_get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )

    if chunks:
        collection.add(
            ids=[f"chunk-{i}" for i in range(len(chunks))],
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_title": c.doc_title,
                    "doc_filename": c.doc_filename,
                    "last_verified": c.last_verified,
                    "disclaimer": c.disclaimer,
                }
                for c in chunks
            ],
        )

    return {"collection": collection, "chunk_count": len(chunks), "chunks": chunks}


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    index = build_index()
    if index["chunk_count"] == 0:
        return []

    result = index["collection"].query(query_texts=[query], n_results=top_k)

    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    results = []
    for text, meta, distance in zip(documents, metadatas, distances):
        # hnsw:space="cosine" => Chroma distance = 1 - cosine_similarity,
        # so similarity = 1 - distance (clamped to [0, 1] for display).
        similarity = max(0.0, min(1.0, 1 - distance))
        results.append(
            {
                "text": text,
                "source_document": meta["doc_title"],
                "source_filename": meta["doc_filename"],
                "last_verified": meta["last_verified"],
                "disclaimer": meta["disclaimer"],
                "relevance_score": round(similarity, 4),
            }
        )
    return results


def answer_question(query: str, top_k: int = 3) -> dict:
    """RAG-lite 'answer': the top retrieved chunk(s), returned verbatim with
    citations -- no LLM paraphrase, so nothing here can be hallucinated beyond
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