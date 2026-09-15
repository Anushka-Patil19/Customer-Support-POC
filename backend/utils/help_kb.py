"""Hybrid (keyword + semantic) search over two supplementary knowledge-base
sources: the curated POC_HELP_METADATA rows (concise, hand-tuned per-field
facts) and the full technical design document, chunked by its own Heading-1
sections (broader coverage -- e.g. acceptance criteria, the full validation
rules tables -- that the curated rows don't spell out individually).

Retrieval runs entirely inside Qdrant: each chunk is indexed with a dense
vector (MiniLM) and a sparse vector (TF-IDF terms/weights) as two named
vectors on the same point, and a query fuses both via Qdrant's native
Reciprocal Rank Fusion (RRF) instead of a hand-rolled normalize+blend. The
fused candidates are then reranked with a cross-encoder -- a slower but far
more precise (query, passage) relevance model -- so the excerpts hitting the
LLM are the ones that actually answer the question, not just ones that
share vocabulary or an embedding neighborhood with it. Tighter grounding
here directly narrows the model's room to hallucinate past what the
excerpts say.

Qdrant runs in embedded local mode (a file-backed collection under
qdrant_data/, no server/Docker) since this KB is small and single-process.
Lazily builds the index on first use; caches it for the life of the process
since both sources are static after seeding/startup.
"""
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import CrossEncoder, SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Fusion,
    FusionQuery,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from database import SessionLocal
from models import HelpMetadata
from utils.design_doc_kb import load_design_doc_chunks

_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_EMBED_DIM = 384
_RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_QDRANT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "qdrant_data")
_COLLECTION_NAME = "help_kb"
_DENSE_VECTOR = "dense"
_SPARSE_VECTOR = "sparse"

_kb = None


def _load_kb() -> dict:
    global _kb
    if _kb is not None:
        return _kb

    db = SessionLocal()
    try:
        rows = db.query(HelpMetadata).filter_by(active_ind="Y").all()
        chunks = [
            {
                "heading": f"{r.page_code}.{r.field_name or r.topic}",
                "text": r.help_text,
                "page_code": r.page_code,
                "source": "help_metadata",
                "images": [],
            }
            for r in rows
        ]
    finally:
        db.close()

    chunks += [
        {
            "heading": c["heading"],
            "text": c["text"],
            "page_code": None,
            "source": c["source"],
            "images": c["images"],
        }
        for c in load_design_doc_chunks()
    ]

    texts = [c["text"] for c in chunks]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(texts)

    embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
    embeddings = embed_model.encode(texts, normalize_embeddings=True)

    reranker = CrossEncoder(_RERANK_MODEL_NAME)

    qdrant = QdrantClient(path=_QDRANT_PATH)
    qdrant.recreate_collection(
        collection_name=_COLLECTION_NAME,
        vectors_config={_DENSE_VECTOR: VectorParams(size=_EMBED_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={_SPARSE_VECTOR: SparseVectorParams()},
    )
    points = []
    for i in range(len(chunks)):
        row = tfidf_matrix.getrow(i)
        points.append(
            PointStruct(
                id=i,
                vector={
                    _DENSE_VECTOR: embeddings[i].tolist(),
                    _SPARSE_VECTOR: SparseVector(indices=row.indices.tolist(), values=row.data.tolist()),
                },
            )
        )
    qdrant.upsert(collection_name=_COLLECTION_NAME, points=points)

    _kb = {
        "chunks": chunks,
        "vectorizer": vectorizer,
        "embed_model": embed_model,
        "reranker": reranker,
        "qdrant": qdrant,
    }
    return _kb


def reset_kb():
    """Call after any admin edit to help_metadata so the next search rebuilds."""
    global _kb
    if _kb is not None:
        _kb["qdrant"].close()  # release the local Qdrant file lock before rebuilding
    _kb = None


# Chunk rank alone isn't a relevance signal: whichever chunk wins a query's
# batch can still be a poor match overall (e.g. an off-topic question against
# a small KB). Images are reference material shown directly to the user, so
# leaking one in on a coincidental top rank -- like "what is the capital of
# France?" weakly matching the sparse "Screenshot of pages" chunk -- would be
# misleading. Gate on raw dense cosine similarity instead, which stays low
# for genuinely unrelated text regardless of how fusion/reranking reorder it.
_IMAGE_RELEVANCE_FLOOR = 0.35


def hybrid_search(query: str, top_k: int = 4) -> list:
    """Returns up to top_k chunks as [{heading, text, page_code, source,
    images, score}]. Qdrant fuses dense (MiniLM) and sparse (TF-IDF)
    candidates via Reciprocal Rank Fusion, then a cross-encoder reranks the
    fused set for final relevance ordering."""
    if not query or not query.strip():
        return []

    kb = _load_kb()
    n = len(kb["chunks"])
    if n == 0:
        return []

    dense_query = kb["embed_model"].encode([query], normalize_embeddings=True)[0].tolist()
    sparse_row = kb["vectorizer"].transform([query])
    sparse_query = SparseVector(indices=sparse_row.indices.tolist(), values=sparse_row.data.tolist())

    dense_hits = kb["qdrant"].query_points(
        collection_name=_COLLECTION_NAME, using=_DENSE_VECTOR, query=dense_query, limit=n,
    ).points
    semantic_scores = np.zeros(n)
    for hit in dense_hits:
        semantic_scores[hit.id] = hit.score

    candidate_limit = min(n, max(top_k * 3, 10))
    fused_hits = kb["qdrant"].query_points(
        collection_name=_COLLECTION_NAME,
        prefetch=[
            Prefetch(query=dense_query, using=_DENSE_VECTOR, limit=candidate_limit),
            Prefetch(query=sparse_query, using=_SPARSE_VECTOR, limit=candidate_limit),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=candidate_limit,
    ).points
    candidate_idx = [hit.id for hit in fused_hits]
    if not candidate_idx:
        return []

    pairs = [(query, kb["chunks"][i]["text"]) for i in candidate_idx]
    rerank_scores = kb["reranker"].predict(pairs)
    ranked = sorted(zip(candidate_idx, rerank_scores), key=lambda pair: -pair[1])[:top_k]

    return [
        {
            "heading": kb["chunks"][i]["heading"],
            "text": kb["chunks"][i]["text"],
            "page_code": kb["chunks"][i]["page_code"],
            "source": kb["chunks"][i]["source"],
            "images": kb["chunks"][i]["images"] if semantic_scores[i] >= _IMAGE_RELEVANCE_FLOOR else [],
            "score": float(score),
        }
        for i, score in ranked
    ]
