"""
AI-Driven Plagiarism Intelligence for Assignments
Main Flask Application Entry Point
IBM Granite (watsonx.ai) powered backend
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from database import db
from routes.assignments import assignments_bp
from routes.analysis import analysis_bp
from routes.dashboard import dashboard_bp

# ── Load environment variables ────────────────────────────────
load_dotenv()

# ── Logging setup ─────────────────────────────────────────────
log_level = getattr(logging, os.getenv("LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)
log_file  = os.getenv("LOG_FILE", "logs/app.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True
    app.config["SECRET_KEY"]           = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///plagiarism_db.sqlite3")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"]   = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    app.config["UPLOAD_FOLDER"]        = os.getenv("UPLOAD_FOLDER", "uploads")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Extensions ────────────────────────────────────────────
    CORS(app)
    db.init_app(app)

    # ── Blueprints ────────────────────────────────────────────
    app.register_blueprint(assignments_bp, url_prefix="/api/assignments")
    app.register_blueprint(analysis_bp,   url_prefix="/api/analysis")
    app.register_blueprint(dashboard_bp,  url_prefix="/")

    # ── DB initialisation ─────────────────────────────────────
    with app.app_context():
        db.create_all()
        logger.info("Database tables created / verified.")

    logger.info("Plagiarism Intelligence app started OK")
    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "True").lower() == "true",
    )
