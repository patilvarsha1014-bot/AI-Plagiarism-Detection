"""
Routes for on-demand analysis and re-analysis.
"""

import logging
from flask import Blueprint, request, jsonify

from database import db, Submission, PlagiarismReport
from analyzer import analyze_submission
from granite_client import granite_client

logger = logging.getLogger(__name__)
analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/submission/<int:submission_id>", methods=["POST"])
def run_analysis(submission_id: int):
    """Trigger (or re-trigger) full analysis for a submission."""
    submission = db.session.get(Submission, submission_id)
    if not submission:
        return jsonify({"error": "Submission not found."}), 404

    report = analyze_submission(submission_id)
    if not report:
        return jsonify({"error": "Analysis failed."}), 500

    return jsonify(report.to_dict()), 200


@analysis_bp.route("/report/<int:report_id>", methods=["GET"])
def get_report(report_id: int):
    """Fetch a specific plagiarism report."""
    report = db.session.get(PlagiarismReport, report_id)
    if not report:
        return jsonify({"error": "Report not found."}), 404
    return jsonify(report.to_dict())


@analysis_bp.route("/compare", methods=["POST"])
def compare_texts():
    """Compare two text snippets using Granite and return similarity explanation."""
    data = request.get_json(force=True)
    text_a = data.get("text_a", "")
    text_b = data.get("text_b", "")

    if not text_a or not text_b:
        return jsonify({"error": "Both text_a and text_b are required."}), 400

    from analyzer import compute_tfidf_similarity
    sims = compute_tfidf_similarity(text_a, [text_b])
    tfidf_score = sims[0] if sims else 0.0

    explanation = granite_client.explain_similarity(text_a, text_b)

    return jsonify({
        "tfidf_similarity": round(tfidf_score, 4),
        "explanation":      explanation,
    })


@analysis_bp.route("/stats", methods=["GET"])
def global_stats():
    """Aggregate statistics across all reports."""
    from sqlalchemy import func
    total      = PlagiarismReport.query.count()
    flagged    = PlagiarismReport.query.filter_by(verdict="flagged").count()
    suspicious = PlagiarismReport.query.filter_by(verdict="suspicious").count()
    clean      = PlagiarismReport.query.filter_by(verdict="clean").count()

    avg_risk = db.session.query(
        func.avg(PlagiarismReport.overall_risk_score)
    ).scalar() or 0.0

    avg_ai = db.session.query(
        func.avg(PlagiarismReport.ai_generated_score)
    ).scalar() or 0.0

    return jsonify({
        "total_analyses":     total,
        "flagged":            flagged,
        "suspicious":         suspicious,
        "clean":              clean,
        "avg_risk_score":     round(float(avg_risk), 4),
        "avg_ai_score":       round(float(avg_ai),   4),
        "flag_rate_pct":      round(flagged / total * 100, 2) if total else 0,
    })
