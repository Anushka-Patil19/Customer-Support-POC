from datetime import date

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from database import SessionLocal
from models import ArDetailCode, ArTransaction, Person, Term

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.get("/person/<banner_id>")
def get_person(banner_id):
    db = SessionLocal()
    try:
        person = db.query(Person).filter_by(banner_id=banner_id.strip().upper()).first()
        if not person:
            return jsonify({"error": "Enter a valid active student ID."}), 404
        if person.active_ind != "Y":
            return jsonify({"error": "Enter a valid active student ID."}), 404
        return jsonify(person.to_dict())
    finally:
        db.close()


@transactions_bp.get("/terms")
def list_terms():
    db = SessionLocal()
    try:
        rows = db.query(Term).filter_by(active_ind="Y").order_by(Term.term_code.desc()).all()
        return jsonify([r.to_dict() for r in rows])
    finally:
        db.close()


@transactions_bp.get("")
def list_transactions():
    banner_id = request.args.get("banner_id")
    term_code = request.args.get("term_code")
    if not banner_id:
        return jsonify({"error": "banner_id is required."}), 400

    db = SessionLocal()
    try:
        person = db.query(Person).filter_by(banner_id=banner_id.strip().upper()).first()
        if not person:
            return jsonify({"error": "Enter a valid active student ID."}), 404

        query = db.query(ArTransaction).filter_by(person_key=person.person_key, status_code="A")
        if term_code:
            query = query.filter_by(term_code=term_code)

        rows = query.order_by(ArTransaction.transaction_no).all()
        result = []
        for r in rows:
            d = r.to_dict()
            detail = db.query(ArDetailCode).filter_by(detail_code=r.detail_code).first()
            d["detail_code_description"] = detail.description if detail else None
            result.append(d)
        return jsonify(result)
    finally:
        db.close()


@transactions_bp.post("")
def create_transaction():
    data = request.get_json(silent=True) or {}
    banner_id = (data.get("banner_id") or "").strip().upper()
    detail_code = (data.get("detail_code") or "").strip().upper()
    term_code = (data.get("term_code") or "").strip()
    entry_amount = data.get("amount")
    original_charge_ind = data.get("original_charge_ind") or "N"

    if not banner_id:
        return jsonify({"error": "Enter a valid active student ID."}), 400
    if not entry_amount or entry_amount <= 0:
        return jsonify({"error": "Amount must be greater than zero."}), 400

    db = SessionLocal()
    try:
        person = db.query(Person).filter_by(banner_id=banner_id, active_ind="Y").first()
        if not person:
            return jsonify({"error": "Enter a valid active student ID."}), 400
        if person.hold_ind == "Y":
            return jsonify({"error": "Account has an AR hold; transaction entry is not permitted."}), 400

        detail = db.query(ArDetailCode).filter_by(detail_code=detail_code, active_ind="Y").first()
        if not detail:
            return jsonify({"error": "Invalid or inactive detail code."}), 400

        term = db.query(Term).filter_by(term_code=term_code, active_ind="Y").first()
        if not term:
            return jsonify({"error": "Enter a valid active term code."}), 400

        signed_amount = entry_amount if detail.type_code == "C" else -entry_amount
        next_no = (
            db.query(func.max(ArTransaction.transaction_no))
            .filter_by(person_key=person.person_key)
            .scalar()
            or 0
        ) + 1

        row = ArTransaction(
            person_key=person.person_key,
            transaction_no=next_no,
            detail_code=detail_code,
            term_code=term_code,
            entry_amount=entry_amount,
            signed_amount=signed_amount,
            open_balance=signed_amount,
            original_charge_ind="Y" if original_charge_ind == "Y" else "N",
            transaction_date=date.today(),
        )
        db.add(row)
        db.commit()

        result = row.to_dict()
        result["detail_code_description"] = detail.description
        return jsonify(result), 201
    finally:
        db.close()


@transactions_bp.delete("/<int:transaction_id>")
def void_transaction(transaction_id):
    """Void rather than physically delete, per doc sec 7.3 ("prefer void status")."""
    db = SessionLocal()
    try:
        row = db.query(ArTransaction).filter_by(transaction_id=transaction_id).first()
        if not row:
            return jsonify({"error": "Transaction not found."}), 404
        row.status_code = "V"
        db.commit()
        return jsonify({"status": "voided"})
    finally:
        db.close()


@transactions_bp.get("/balance")
def get_balance():
    banner_id = request.args.get("banner_id")
    term_code = request.args.get("term_code")
    detail_code = request.args.get("detail_code")
    if not banner_id:
        return jsonify({"error": "banner_id is required."}), 400

    db = SessionLocal()
    try:
        person = db.query(Person).filter_by(banner_id=banner_id.strip().upper()).first()
        if not person:
            return jsonify({"error": "Enter a valid active student ID."}), 404

        query = db.query(func.coalesce(func.sum(ArTransaction.open_balance), 0)).filter(
            ArTransaction.person_key == person.person_key, ArTransaction.status_code == "A"
        )
        if term_code:
            query = query.filter(ArTransaction.term_code == term_code)
        if detail_code:
            query = query.filter(ArTransaction.detail_code == detail_code.upper())

        balance = query.scalar() or 0
        return jsonify(
            {
                "banner_id": person.banner_id,
                "display_name": person.display_name,
                "term_code": term_code,
                "detail_code": detail_code,
                "balance": float(balance),
            }
        )
    finally:
        db.close()
