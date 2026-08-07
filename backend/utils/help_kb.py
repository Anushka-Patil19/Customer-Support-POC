"""Hybrid (keyword + semantic) search over two supplementary knowledge-base
sources: the curated POC_HELP_METADATA rows (concise, hand-tuned per-field
facts) and the full technical design document, chunked by its own Heading-1
sections (broader coverage -- e.g. acceptance criteria, the full validation
rules tables -- that the curated rows don't spell out individually).

Same retrieval shape as the sibling interview project's kt_kb.py (TF-IDF +
MiniLM hybrid search); the difference is the source content is two DB/file
origins merged into one index rather than a single PDF. Lazily builds an
in-memory index on first use; caches it for the life of the process since
both sources are static after seeding/startup.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from database import SessionLocal
from models import HelpMetadata
from utils.design_doc_kb import load_design_doc_chunks

_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

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

    _kb = {
        "chunks": chunks,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "embed_model": embed_model,
        "embeddings": embeddings,
    }
    return _kb


def reset_kb():
    """Call after any admin edit to help_metadata so the next search rebuilds."""
    global _kb
    _kb = None


def _normalize(scores: np.ndarray) -> np.ndarray:
    lo, hi = scores.min(), scores.max()
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)



# Chunk rank alone isn't a relevance signal: the blended `combined` score is
# min-max normalized *within this one query's batch*, so whichever chunk wins
# always ends up near 1.0 even when every chunk is a poor match (e.g. an
# off-topic question against a small KB). Images are reference material shown
# directly to the user, so leaking one in on a coincidental top rank -- like
# "what is the capital of France?" weakly matching the sparse "Screenshot of
# pages" chunk -- would be misleading. Gate on the *raw* (pre-normalization)
# semantic similarity instead, which stays low for genuinely unrelated text.
_IMAGE_RELEVANCE_FLOOR = 0.35


def hybrid_search(query: str, top_k: int = 4) -> list:
    """Returns up to top_k chunks as [{heading, text, page_code, source, images,
    score}], ranked by 0.4 * keyword similarity + 0.6 * semantic similarity,
    across both the help_metadata rows and the design-doc sections."""
    if not query or not query.strip():
        return []

    kb = _load_kb()
    if not kb["chunks"]:
        return []

    keyword_vec = kb["vectorizer"].transform([query])
    keyword_scores = cosine_similarity(keyword_vec, kb["tfidf_matrix"])[0]

    query_embedding = kb["embed_model"].encode([query], normalize_embeddings=True)
    semantic_scores = cosine_similarity(query_embedding, kb["embeddings"])[0]

    combined = 0.4 * _normalize(keyword_scores) + 0.6 * _normalize(semantic_scores)
    ranked_idx = np.argsort(-combined)[:top_k]

    return [
        {
            "heading": kb["chunks"][i]["heading"],
            "text": kb["chunks"][i]["text"],
            "page_code": kb["chunks"][i]["page_code"],
            "source": kb["chunks"][i]["source"],
            "images": kb["chunks"][i]["images"] if semantic_scores[i] >= _IMAGE_RELEVANCE_FLOOR else [],
            "score": float(combined[i]),
        }
        for i in ranked_idx
    ]
