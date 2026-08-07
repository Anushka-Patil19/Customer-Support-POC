from flask import Blueprint, jsonify, request

from database import SessionLocal
from models import ArCategory, ArDetailCode, ArTransaction

detail_codes_bp = Blueprint("detail_codes", __name__)


@detail_codes_bp.get("")
def list_detail_codes():
    active_only = request.args.get("active") == "Y"
    db = SessionLocal()
    try:
        query = db.query(ArDetailCode)
        if active_only:
            query = query.filter_by(active_ind="Y")
        rows = query.order_by(ArDetailCode.detail_code).all()
        return jsonify([r.to_dict() for r in rows])
    finally:
        db.close()


@detail_codes_bp.post("")
def create_detail_code():
    data = request.get_json(silent=True) or {}
    code = (data.get("detail_code") or "").strip().upper()
    description = (data.get("description") or "").strip()
    type_code = (data.get("type_code") or "").strip().upper()
    category_code = (data.get("category_code") or "").strip().upper()
    priority_no = data.get("priority_no", 0)
    term_based_ind = data.get("term_based_ind") or "Y"
    aid_year_based_ind = data.get("aid_year_based_ind") or "N"
    refundable_ind = data.get("refundable_ind") or "N"
    receipt_ind = data.get("receipt_ind") or "N"

    if not code or not (1 <= len(code) <= 4):
        return jsonify({"error": "Detail code is required (1-4 characters)."}), 400
    if not description or len(description) > 60:
        return jsonify({"error": "Detail code description is required (1-60 characters)."}), 400
    if type_code not in ("C", "P"):
        return jsonify({"error": "Type must be C (charge) or P (payment)."}), 400
    if not isinstance(priority_no, int) or not (0 <= priority_no <= 999):
        return jsonify({"error": "Priority must be between 000 and 999."}), 400
    if term_based_ind == "Y" and aid_year_based_ind == "Y":
        return jsonify({"error": "Choose either Term Based or Aid Year Based."}), 400

    db = SessionLocal()
    try:
        if db.query(ArDetailCode).filter_by(detail_code=code).first():
            return jsonify({"error": "Detail code already exists."}), 409

        category = db.query(ArCategory).filter_by(category_code=category_code, active_ind="Y").first()
        if not category:
            return jsonify({"error": "Enter a valid active category code maintained on TTVDCAT."}), 400

        row = ArDetailCode(
            detail_code=code,
            description=description,
            type_code=type_code,
            category_code=category_code,
            priority_no=priority_no,
            term_based_ind=term_based_ind,
            aid_year_based_ind=aid_year_based_ind,
            refundable_ind=refundable_ind,
            receipt_ind=receipt_ind,
        )
        db.add(row)
        db.commit()
        return jsonify(row.to_dict()), 201
    finally:
        db.close()


@detail_codes_bp.patch("/<code>/deactivate")
def deactivate_detail_code(code):
    code = code.strip().upper()
    db = SessionLocal()
    try:
        row = db.query(ArDetailCode).filter_by(detail_code=code).first()
        if not row:
            return jsonify({"error": "Detail code not found."}), 404
        row.active_ind = "N"
        db.commit()
        return jsonify(row.to_dict())
    finally:
        db.close()


@detail_codes_bp.delete("/<code>")
def delete_detail_code(code):
    code = code.strip().upper()
    db = SessionLocal()
    try:
        row = db.query(ArDetailCode).filter_by(detail_code=code).first()
        if not row:
            return jsonify({"error": "Detail code not found."}), 404
        if db.query(ArTransaction).filter_by(detail_code=code).first():
            return jsonify({"error": "Detail code has account activity and cannot be deleted."}), 409

        db.delete(row)
        db.commit()
        return jsonify({"status": "deleted"})
    finally:
        db.close()
