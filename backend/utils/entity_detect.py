"""Whitelist-driven entity detection for the Deep Dive assistant.

Deliberately NOT an NLP/LLM classification step: a free-text selection or
question is tokenized and intersected against the *actual* codes currently
in the DB, fetched fresh per request. A token only ever "hits" if it is a
real category/detail/term code or a real Banner ID, so this can't
false-positive on a code that doesn't exist, and it never goes stale as
seed/admin data changes.
"""
import re

from database import SessionLocal
from models import ArCategory, ArDetailCode, Person, Term

_BANNER_ID_RE = re.compile(r"\b[A-Za-z]\d{8}\b")
_TERM_RE = re.compile(r"\b\d{6}\b")
_TOKEN_RE = re.compile(r"\b[A-Z0-9]{2,6}\b")


def detect_entities(text: str, page_context: dict = None) -> dict:
    """`page_context` (optional) is whatever the frontend says is currently on
    screen -- e.g. {"banner_id": "D00010001"} when the user is looking at that
    student's TSADETL page. It's only ever used as a FALLBACK for a code type
    the text itself didn't name explicitly, so an explicit mention in the text
    always wins, and a bogus/stale context value can't inject a fake entity
    (still checked against the live known-code set below)."""
    page_context = page_context or {}
    if not text or not text.strip():
        text = ""

    upper = text.upper()
    tokens = set(_TOKEN_RE.findall(upper))

    db = SessionLocal()
    try:
        known_categories = {c[0] for c in db.query(ArCategory.category_code).all()}
        known_detail_codes = {d[0] for d in db.query(ArDetailCode.detail_code).all()}
        known_terms = {t[0] for t in db.query(Term.term_code).all()}
        known_banner_ids = {p[0] for p in db.query(Person.banner_id).all()}
    finally:
        db.close()

    banner_ids = [b for b in _BANNER_ID_RE.findall(upper) if b in known_banner_ids]
    term_codes = [t for t in _TERM_RE.findall(upper) if t in known_terms]

    context_banner_id = (page_context.get("banner_id") or "").strip().upper()
    if not banner_ids and context_banner_id in known_banner_ids:
        banner_ids = [context_banner_id]

    context_term_code = (page_context.get("term_code") or "").strip()
    if not term_codes and context_term_code in known_terms:
        term_codes = [context_term_code]

    return {
        "category_codes": sorted(tokens & known_categories),
        "detail_codes": sorted(tokens & known_detail_codes),
        "banner_ids": banner_ids,
        "term_codes": term_codes,
    }
