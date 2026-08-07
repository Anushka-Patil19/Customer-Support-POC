import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from database import create_tables
from routes.categories import categories_bp
from routes.detail_codes import detail_codes_bp
from routes.help import help_bp
from routes.transactions import transactions_bp
import seed

app = Flask(__name__)
CORS(app)

create_tables()
seed.run()

app.register_blueprint(categories_bp, url_prefix="/api/categories")
app.register_blueprint(detail_codes_bp, url_prefix="/api/detail-codes")
app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
app.register_blueprint(help_bp, url_prefix="/api/help")

_DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


@app.get("/docs/<path:filename>")
def serve_doc_asset(filename):
    """Serves the design-doc screenshots referenced by Deep Dive responses
    (reference material only -- never sent to the LLM, just linked for the
    frontend to display)."""
    return send_from_directory(_DOCS_DIR, filename)


@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "banner-ar-poc"})


@app.errorhandler(Exception)
def handle_exception(err):
    from werkzeug.exceptions import HTTPException

    if isinstance(err, HTTPException):
        raise err
    return jsonify({"error": str(err)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5050)), debug=True)
