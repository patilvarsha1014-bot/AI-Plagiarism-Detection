"""
Database models for the Plagiarism Intelligence system.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Course(db.Model):
    __tablename__ = "courses"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    code        = db.Column(db.String(20),  nullable=False, unique=True)
    instructor  = db.Column(db.String(150), nullable=False)
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)

    assignments = db.relationship("Assignment", backref="course", lazy=True)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "code":       self.code,
            "instructor": self.instructor,
            "created_at": self.created_at.isoformat(),
        }


class Assignment(db.Model):
    __tablename__ = "assignments"

    id          = db.Column(db.Integer, primary_key=True)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title       = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text,        nullable=True)
    due_date    = db.Column(db.DateTime,    nullable=True)
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)

    submissions = db.relationship("Submission", backref="assignment", lazy=True)

    def to_dict(self):
        return {
            "id":          self.id,
            "course_id":   self.course_id,
            "title":       self.title,
            "description": self.description,
            "due_date":    self.due_date.isoformat() if self.due_date else None,
            "created_at":  self.created_at.isoformat(),
        }


class Submission(db.Model):
    __tablename__ = "submissions"

    id              = db.Column(db.Integer, primary_key=True)
    assignment_id   = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    student_name    = db.Column(db.String(150), nullable=False)
    student_id      = db.Column(db.String(50),  nullable=False)
    content         = db.Column(db.Text,         nullable=False)
    file_path       = db.Column(db.String(300),  nullable=True)
    submitted_at    = db.Column(db.DateTime,     default=datetime.utcnow)

    analysis        = db.relationship("PlagiarismReport", backref="submission",
                                      uselist=False, lazy=True)

    def to_dict(self):
        return {
            "id":            self.id,
            "assignment_id": self.assignment_id,
            "student_name":  self.student_name,
            "student_id":    self.student_id,
            "submitted_at":  self.submitted_at.isoformat(),
        }


class PlagiarismReport(db.Model):
    __tablename__ = "plagiarism_reports"

    id                   = db.Column(db.Integer, primary_key=True)
    submission_id        = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)

    # Scores (0.0 – 1.0)
    similarity_score     = db.Column(db.Float, default=0.0)
    ai_generated_score   = db.Column(db.Float, default=0.0)
    paraphrase_score     = db.Column(db.Float, default=0.0)
    overall_risk_score   = db.Column(db.Float, default=0.0)

    # Verdict
    verdict              = db.Column(db.String(50),  default="clean")   # clean / suspicious / flagged
    granite_explanation  = db.Column(db.Text,         nullable=True)
    matched_sources      = db.Column(db.JSON,          default=list)
    flagged_passages     = db.Column(db.JSON,          default=list)

    analyzed_at          = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":                  self.id,
            "submission_id":       self.submission_id,
            "similarity_score":    round(self.similarity_score,   4),
            "ai_generated_score":  round(self.ai_generated_score, 4),
            "paraphrase_score":    round(self.paraphrase_score,   4),
            "overall_risk_score":  round(self.overall_risk_score, 4),
            "verdict":             self.verdict,
            "granite_explanation": self.granite_explanation,
            "matched_sources":     self.matched_sources   or [],
            "flagged_passages":    self.flagged_passages  or [],
            "analyzed_at":         self.analyzed_at.isoformat(),
        }


class InstructorFeedback(db.Model):
    __tablename__ = "instructor_feedback"

    id            = db.Column(db.Integer, primary_key=True)
    report_id     = db.Column(db.Integer, db.ForeignKey("plagiarism_reports.id"), nullable=False)
    instructor    = db.Column(db.String(150), nullable=False)
    confirmed     = db.Column(db.Boolean,     default=False)   # True = plagiarism confirmed
    notes         = db.Column(db.Text,         nullable=True)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "report_id":  self.report_id,
            "instructor": self.instructor,
            "confirmed":  self.confirmed,
            "notes":      self.notes,
            "created_at": self.created_at.isoformat(),
        }
