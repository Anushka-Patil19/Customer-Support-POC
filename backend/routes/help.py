import json
import re

from flask import Blueprint, jsonify, request
from groq import APIError, Groq, RateLimitError
from sqlalchemy import func

from config import Config
from database import SessionLocal
from models import ArCategory, ArDetailCode, ArTransaction, Person
from utils.entity_detect import detect_entities
from utils.help_kb import hybrid_search

_groq = Groq(api_key=Config.GROQ_API_KEY)
_MODEL = "openai/gpt-oss-120b"
help_bp = Blueprint("help", __name__)

_RATE_LIMIT_MESSAGE = "The Deep Dive assistant has hit its usage limit for the next few minutes -- please try again shortly."
_UPSTREAM_ERROR_MESSAGE = "The Deep Dive assistant is temporarily unavailable -- please try again."
_OUT_OF_SCOPE_MESSAGE = (
    "I can only answer questions about the Banner AR simulation pages (TTVDCAT, TSADETC, TSADETL) "
    "and student account activity -- that's outside what I can help with here."
)


def _call_groq(system_instruction, input_text, json_mode=False):
    kwargs = {
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": input_text},
        ],
        "model": _MODEL,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        completion = _groq.chat.completions.create(**kwargs)
        return completion.choices[0].message.content, None
    except RateLimitError as e:
        print(
            f"\n[GROQ RATE LIMIT] Groq API quota/rate limit exhausted -- "
            f"status={getattr(e, 'status_code', '?')} message={getattr(e, 'message', str(e))}\n",
            flush=True,
        )
        return None, _RATE_LIMIT_MESSAGE
    except APIError as e:
        print(
            f"\n[GROQ API ERROR] status={getattr(e, 'status_code', '?')} message={getattr(e, 'message', str(e))}\n",
            flush=True,
        )
        return None, _UPSTREAM_ERROR_MESSAGE


def _safe_json_loads(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        sanitized = re.sub(r"[\x00-\x1f\x7f]", " ", text)
        try:
            return json.loads(sanitized)
        except json.JSONDecodeError:
            return {}


# ── Live SQL dispatch (doc sec 8) -- bound parameters only, never string-interpolated ──


def _log_query(label: str, query, sink: list) -> None:
    """Compiles the literal SQL (real values substituted in, not `?`
    placeholders) for a Deep Dive live-data query, prints it (best-effort --
    terminal visibility depends on how the process is launched) and, more
    reliably, appends it to `sink` so it can be returned in the API response
    itself and shown in the frontend's "View backend log" panel."""
    compiled = str(query.statement.compile(compile_kwargs={"literal_binds": True})).strip()
    sink.append(f"-- {label}\n{compiled}")
    print(f"\n[DEEP DIVE SQL] {label}\n{compiled}\n", flush=True)


def _balance_context(db, banner_id, term_codes, detail_codes, queries: list):
    person = db.query(Person).filter_by(banner_id=banner_id).first()
    if not person:
        return None

    query = db.query(func.coalesce(func.sum(ArTransaction.open_balance), 0)).filter(
        ArTransaction.person_key == person.person_key, ArTransaction.status_code == "A"
    )
    term_code = term_codes[0] if term_codes else None
    detail_code = detail_codes[0] if detail_codes else None
    if term_code:
        query = query.filter(ArTransaction.term_code == term_code)
    if detail_code:
        query = query.filter(ArTransaction.detail_code == detail_code)
    _log_query(f"balance for {banner_id}", query, queries)
    balance = float(query.scalar() or 0)

    rows = (
        db.query(ArTransaction)
        .filter(ArTransaction.person_key == person.person_key, ArTransaction.status_code == "A")
        .all()
    )
    transactions = [
        {
            "detail_code": r.detail_code,
            "term_code": r.term_code,
            "entry_amount": float(r.entry_amount),
            "open_balance": float(r.open_balance),
        }
        for r in rows
    ]

    return {
        "banner_id": person.banner_id,
        "display_name": person.display_name,
        "hold_ind": person.hold_ind,
        "filtered_by": {"term_code": term_code, "detail_code": detail_code},
        "balance": balance,
        "transaction_count": len(transactions),
        "contributing_transactions": transactions,
    }


def _category_usage_context(db, category_code, queries: list):
    category = db.query(ArCategory).filter_by(category_code=category_code).first()
    if not category:
        return None
    detail_codes_query = db.query(ArDetailCode).filter_by(category_code=category_code)
    _log_query(f"detail codes using category {category_code}", detail_codes_query, queries)
    detail_codes = detail_codes_query.all()
    return {
        "category_code": category.category_code,
        "description": category.description,
        "system_required_ind": category.system_required_ind,
        "active_ind": category.active_ind,
        "detail_codes_using_this_category": [
            {
                "detail_code": d.detail_code,
                "description": d.description,
                "type_code": d.type_code,
                "active_ind": d.active_ind,
            }
            for d in detail_codes
        ],
    }


def _detail_code_usage_context(db, detail_code, queries: list):
    detail = db.query(ArDetailCode).filter_by(detail_code=detail_code).first()
    if not detail:
        return None

    agg_query = db.query(
        func.count(ArTransaction.transaction_id),
        func.count(func.distinct(ArTransaction.person_key)),
        func.coalesce(func.sum(ArTransaction.open_balance), 0),
    ).filter(ArTransaction.detail_code == detail_code, ArTransaction.status_code == "A")
    _log_query(f"usage stats for detail code {detail_code}", agg_query, queries)
    transaction_count, account_count, total_open_balance = agg_query.first()

    return {
        "detail_code": detail.detail_code,
        "description": detail.description,
        "type_code": detail.type_code,
        "category_code": detail.category_code,
        "active_ind": detail.active_ind,
        "transaction_count": transaction_count,
        "account_count": account_count,
        "total_open_balance": float(total_open_balance),
    }


def _live_context(entities: dict) -> tuple:
    ctx = []
    queries = []
    db = SessionLocal()
    try:
        for bid in entities["banner_ids"]:
            result = _balance_context(db, bid, entities["term_codes"], entities["detail_codes"], queries)
            if result:
                ctx.append(f"LIVE DATA -- account balance for {bid}: {json.dumps(result)}")

        for cat in entities["category_codes"]:
            result = _category_usage_context(db, cat, queries)
            if result:
                ctx.append(f"LIVE DATA -- category {cat} and what uses it: {json.dumps(result)}")

        for dc in entities["detail_codes"]:
            result = _detail_code_usage_context(db, dc, queries)
            if result:
                ctx.append(f"LIVE DATA -- detail code {dc} record and usage: {json.dumps(result)}")
    finally:
        db.close()
    return ctx, queries


_LIVE_DATA_RULE = (
    "- When a LIVE DATA block is present, treat it as ground truth about this specific record and "
    "answer using its actual values (e.g. the real active_ind, balance, or code) rather than a generic "
    "description of the concept."
    "\n- When a LIVE DATA block includes a balance and its contributing_transactions, always state the "
    "transaction_count explicitly (e.g. \"across 2 transactions: a $2000.00 TUIT charge and a $500.00 "
    "CASH payment\") -- never describe the balance without naming how many transactions make it up."
)

_EXPLAIN_SYSTEM_PROMPT = f"""\
You are a Deep Dive help assistant for the Banner AR Interactive Help POC, covering the TTVDCAT \
(category validation), TSADETC (detail code control), and TSADETL (student account detail) simulation \
pages. You explain what a selected piece of the screen does, using ONLY the help excerpts and any LIVE \
DATA provided below as ground truth.

Rules:
- The selected screen content is always something the user picked from one of these pages, so it is \
always in scope -- explain it.
- Base your explanation strictly on the provided excerpts and live data. Do not invent behavior that \
isn't in them.
{_LIVE_DATA_RULE}
- Describe behavior in plain, functional terms only -- never mention API endpoints, route paths, backend \
table/column names, or other implementation-level details, even if they appear in the excerpts.
- If the excerpts and live data don't clearly cover what was selected, say plainly that this area isn't \
covered in the help documentation instead of guessing.
- Never mention a screenshot or reference image unless the exact literal text \
"[SCREENSHOT_AVAILABLE]" appears below in this request's context -- if it does, briefly say (in your own \
words) that a reference screenshot is shown below; if it does not appear, do not bring up screenshots at all.
- Be concise (2-5 sentences) and concrete -- describe what it does and why, not generic advice.
- Also propose exactly 4 short follow-up questions (each under 8 words) a curious user might ask next \
about this same area. Each must be answerable from the excerpts/live data.

Respond with ONLY a JSON object in this exact shape (no markdown, no extra text):
{{"explanation": "...", "follow_up_questions": ["...", "...", "...", "..."]}}
"""

_FOLLOWUP_SYSTEM_PROMPT = f"""\
You are a Deep Dive help assistant for the Banner AR Interactive Help POC, covering the TTVDCAT, \
TSADETC, and TSADETL simulation pages. Answer the user's follow-up question using ONLY the help \
excerpts and any LIVE DATA provided below as ground truth.

Rules:
- First, judge whether the question is actually about these AR simulation pages or student account \
activity (the excerpts below are a sample of that functionality, not the full scope -- a question can \
be in-scope even if these particular excerpts don't cover it). If the question is about something else \
entirely (general knowledge, personal requests, creative writing, unrelated coding help, etc.), respond \
with EXACTLY this sentence and nothing else: "{_OUT_OF_SCOPE_MESSAGE}"
- Short or loosely-worded questions (e.g. "what is a category?", "why is it inactive?") are almost \
always about a concept that appears in the excerpts, even if the wording doesn't match closely -- read \
the excerpts for the underlying concept before deciding a question is off-topic.
- Otherwise, base your answer strictly on the provided excerpts and live data. Do not invent behavior \
that isn't in them.
{_LIVE_DATA_RULE}
- Describe behavior in plain, functional terms only -- never mention API endpoints, route paths, backend \
table/column names, or other implementation-level details, even if they appear in the excerpts.
- If the question is on-topic but the excerpts/live data don't clearly cover it, say plainly that this \
isn't covered instead of guessing.
- If the exact literal text "[SCREENSHOT_AVAILABLE]" appears below in this request's context, a question \
asking to see or describe what a page looks like IS in scope -- don't refuse it, and briefly say (in your \
own words, never quoting that text) that a reference screenshot is shown below. If that text does NOT \
appear below, never mention screenshots or reference images at all, even if the question asks for one.
- Be concise (2-4 sentences) and concrete.
"""

_IMAGES_AVAILABLE_NOTE = "[SCREENSHOT_AVAILABLE]"


def _build_context(text: str, page_context: dict = None) -> tuple:
    entities = detect_entities(text, page_context)
    live_blocks, queries = _live_context(entities)
    chunks = hybrid_search(text, top_k=4)

    parts = []
    if chunks:
        parts.append(
            "Static help excerpts:\n"
            + "\n\n".join(f"### {c['heading']}\n{c['text']}" for c in chunks)
        )
    if live_blocks:
        parts.append("\n\n".join(live_blocks))
    if _collect_images(chunks):
        parts.append(_IMAGES_AVAILABLE_NOTE)

    debug = {
        "entities_detected": entities,
        "sql_queries": queries,
        "kb_chunks_retrieved": [
            {"heading": c["heading"], "source": c["source"], "score": round(c["score"], 3)}
            for c in chunks
        ],
    }

    return "\n\n".join(parts), chunks, debug


def _collect_images(chunks: list) -> list:
    """Reference-only images from the design doc (e.g. its TSADETL screenshot)
    for whichever chunks were actually retrieved -- never sent to the LLM,
    just surfaced to the frontend alongside the answer. Deduped, order kept."""
    seen = set()
    images = []
    for c in chunks:
        for img in c.get("images") or []:
            if img not in seen:
                seen.add(img)
                images.append(img)
    return images


@help_bp.post("/explain")
def explain():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    page_context = data.get("context") or {}
    if not text:
        return jsonify({"error": "Missing text"}), 400

    context, chunks, debug = _build_context(text, page_context)
    if not context:
        return jsonify({
            "explanation": _OUT_OF_SCOPE_MESSAGE,
            "sections": [],
            "images": [],
            "follow_up_questions": [],
            "debug": debug,
        }), 200

    user_prompt = f"Selected screen content:\n\"\"\"\n{text[:2000]}\n\"\"\"\n\n{context}"

    raw, err = _call_groq(_EXPLAIN_SYSTEM_PROMPT, user_prompt, json_mode=True)
    if err:
        return jsonify({"error": err}), 503
    result = _safe_json_loads(raw)

    return jsonify({
        "explanation": result.get("explanation", ""),
        "sections": [c["heading"] for c in chunks],
        "images": _collect_images(chunks),
        "follow_up_questions": (result.get("follow_up_questions") or [])[:4],
        "debug": debug,
    }), 200


@help_bp.post("/followup")
def followup():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    page_context = data.get("context") or {}
    if not question:
        return jsonify({"error": "Missing question"}), 400

    context, chunks, debug = _build_context(question, page_context)
    if not context:
        return jsonify({
            "answer": _OUT_OF_SCOPE_MESSAGE,
            "sections": [],
            "images": [],
            "debug": debug,
        }), 200

    user_prompt = f"Question: {question}\n\n{context}"

    answer, err = _call_groq(_FOLLOWUP_SYSTEM_PROMPT, user_prompt)
    if err:
        return jsonify({"error": err}), 503

    return jsonify({
        "answer": answer,
        "sections": [c["heading"] for c in chunks],
        "images": _collect_images(chunks),
        "debug": debug,
    }), 200
