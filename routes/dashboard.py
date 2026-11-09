"""
Routes for the HTML dashboard (serves frontend pages).
"""

from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    return render_template("index.html")


@dashboard_bp.route("/submit")
def submit_page():
    return render_template("submit.html")


@dashboard_bp.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@dashboard_bp.route("/report/<int:submission_id>")
def report_page(submission_id: int):
    return render_template("report.html", submission_id=submission_id)
