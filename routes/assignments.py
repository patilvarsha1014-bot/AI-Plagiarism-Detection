"""
Routes for Assignment and Submission management.
"""

import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from database import db, Course, Assignment, Submission
from analyzer import analyze_submission

logger = logging.getLogger(__name__)
assignments_bp = Blueprint("assignments", __name__)

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _extract_text(filepath: str) -> str:
    """Extract plain text from txt, pdf, or docx files."""
    ext = filepath.rsplit(".", 1)[-1].lower()
    try:
        if ext == "txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == "pdf":
            import PyPDF2
            text = []
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text() or "")
            return "\n".join(text)
        elif ext == "docx":
            import docx
            doc = docx.Document(filepath)
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        logger.error("Text extraction failed for %s: %s", filepath, exc)
    return ""


# ── Courses ─────────────────────────────────────────────────────

@assignments_bp.route("/courses", methods=["GET"])
def list_courses():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return jsonify([c.to_dict() for c in courses])


@assignments_bp.route("/courses", methods=["POST"])
def create_course():
    data = request.get_json(force=True)
    required = ("name", "code", "instructor")
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {required}"}), 400

    if Course.query.filter_by(code=data["code"]).first():
        return jsonify({"error": "Course code already exists."}), 409

    course = Course(name=data["name"], code=data["code"], instructor=data["instructor"])
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201


# ── Assignments ──────────────────────────────────────────────────

@assignments_bp.route("", methods=["GET"])
def list_assignments():
    course_id = request.args.get("course_id", type=int)
    q = Assignment.query
    if course_id:
        q = q.filter_by(course_id=course_id)
    assignments = q.order_by(Assignment.created_at.desc()).all()
    return jsonify([a.to_dict() for a in assignments])


@assignments_bp.route("", methods=["POST"])
def create_assignment():
    data = request.get_json(force=True)
    if not data.get("title") or not data.get("course_id"):
        return jsonify({"error": "title and course_id are required."}), 400

    assignment = Assignment(
        course_id   = data["course_id"],
        title       = data["title"],
        description = data.get("description", ""),
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify(assignment.to_dict()), 201


@assignments_bp.route("/<int:assignment_id>", methods=["GET"])
def get_assignment(assignment_id: int):
    a = db.session.get(Assignment, assignment_id)
    if not a:
        return jsonify({"error": "Not found"}), 404
    return jsonify(a.to_dict())


# ── Submissions ──────────────────────────────────────────────────

@assignments_bp.route("/<int:assignment_id>/submissions", methods=["GET"])
def list_submissions(assignment_id: int):
    subs = Submission.query.filter_by(assignment_id=assignment_id).all()
    result = []
    for s in subs:
        d = s.to_dict()
        if s.analysis:
            d["report"] = s.analysis.to_dict()
        result.append(d)
    return jsonify(result)


@assignments_bp.route("/<int:assignment_id>/submissions", methods=["POST"])
def submit_assignment(assignment_id: int):
    """Accept text or file upload, store submission, trigger analysis."""
    student_name = request.form.get("student_name") or (
        request.get_json(silent=True) or {}
    ).get("student_name")
    student_id   = request.form.get("student_id") or (
        request.get_json(silent=True) or {}
    ).get("student_id")
    content      = request.form.get("content") or (
        request.get_json(silent=True) or {}
    ).get("content", "")

    if not student_name or not student_id:
        return jsonify({"error": "student_name and student_id are required."}), 400

    # Handle optional file upload
    file = request.files.get("file")
    file_path = None
    if file and file.filename and _allowed_file(file.filename):
        filename  = secure_filename(file.filename)
        upload_dir = os.path.join(
            os.getenv("UPLOAD_FOLDER", "uploads"),
            str(assignment_id),
        )
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        extracted = _extract_text(file_path)
        if extracted:
            content = extracted

    if not content:
        return jsonify({"error": "Submission content is required (text or file)."}), 400

    submission = Submission(
        assignment_id = assignment_id,
        student_name  = student_name,
        student_id    = student_id,
        content       = content,
        file_path     = file_path,
    )
    db.session.add(submission)
    db.session.commit()

    # Run analysis immediately (synchronous for simplicity)
    report = analyze_submission(submission.id)

    response = submission.to_dict()
    response["report"] = report.to_dict() if report else None
    return jsonify(response), 201


# ── Instructor feedback ──────────────────────────────────────────

@assignments_bp.route("/submissions/<int:submission_id>/feedback", methods=["POST"])
def submit_feedback(submission_id: int):
    from database import InstructorFeedback, PlagiarismReport
    data = request.get_json(force=True)
    report = PlagiarismReport.query.filter_by(submission_id=submission_id).first()
    if not report:
        return jsonify({"error": "No report found for this submission."}), 404

    feedback = InstructorFeedback(
        report_id  = report.id,
        instructor = data.get("instructor", "unknown"),
        confirmed  = bool(data.get("confirmed", False)),
        notes      = data.get("notes", ""),
    )
    db.session.add(feedback)
    db.session.commit()
    logger.info(
        "Instructor feedback recorded: report=%d confirmed=%s",
        report.id, feedback.confirmed,
    )
    return jsonify(feedback.to_dict()), 201
