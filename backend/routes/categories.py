from flask import Blueprint, jsonify, request

from database import SessionLocal
from models import ArCategory, ArDetailCode

categories_bp = Blueprint("categories", __name__)


@categories_bp.get("")
def list_categories():
    active_only = request.args.get("active") == "Y"
    db = SessionLocal()
    try:
        query = db.query(ArCategory)
        if active_only:
            query = query.filter_by(active_ind="Y")
        rows = query.order_by(ArCategory.category_code).all()
        return jsonify([r.to_dict() for r in rows])
    finally:
        db.close()


@categories_bp.post("")
def create_category():
    data = request.get_json(silent=True) or {}
    code = (data.get("category_code") or "").strip().upper()
    description = (data.get("description") or "").strip()
    system_required_ind = data.get("system_required_ind") or "N"

    if not code or not (1 <= len(code) <= 4) or " " in code:
        return jsonify({"error": "Code is required, 1-4 characters, and cannot contain spaces."}), 400
    if not description or len(description) > 60:
        return jsonify({"error": "Description is required (1-60 characters)."}), 400

    db = SessionLocal()
    try:
        if db.query(ArCategory).filter_by(category_code=code).first():
            return jsonify({"error": "Category code already exists or is not uppercase."}), 409

        row = ArCategory(
            category_code=code,
            description=description,
            system_required_ind="Y" if system_required_ind == "Y" else "N",
        )
        db.add(row)
        db.commit()
        return jsonify(row.to_dict()), 201
    finally:
        db.close()


@categories_bp.delete("/<code>")
def delete_category(code):
    code = code.strip().upper()
    db = SessionLocal()
    try:
        row = db.query(ArCategory).filter_by(category_code=code).first()
        if not row:
            return jsonify({"error": "Category not found."}), 404
        if row.system_required_ind == "Y":
            return jsonify({"error": "System-required category codes cannot be deleted."}), 409
        if db.query(ArDetailCode).filter_by(category_code=code).first():
            return jsonify(
                {"error": "Category is used by one or more detail codes; deactivate it instead."}
            ), 409

        db.delete(row)
        db.commit()
        return jsonify({"status": "deleted"})
    finally:
        db.close()


@categories_bp.patch("/<code>/deactivate")
def deactivate_category(code):
    code = code.strip().upper()
    db = SessionLocal()
    try:
        row = db.query(ArCategory).filter_by(category_code=code).first()
        if not row:
            return jsonify({"error": "Category not found."}), 404
        row.active_ind = "N"
        db.commit()
        return jsonify(row.to_dict())
    finally:
        db.close()
