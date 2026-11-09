#!/usr/bin/env python3
"""
Seed script – creates a demo course, assignment, and sample submissions
to immediately see the system in action.

Usage:
    python seed_data.py
"""

from app import create_app
from database import db, Course, Assignment, Submission
from analyzer import analyze_submission

SAMPLE_ORIGINAL = """
Machine learning is a subset of artificial intelligence that enables systems to learn
and improve from experience without being explicitly programmed. It focuses on developing
computer programs that can access data and use it to learn for themselves. The process
begins with observations or data such as examples, direct experience, or instruction.
Machine learning algorithms use computational methods to learn information directly
from data without relying on a predetermined equation as a model.
"""

SAMPLE_PARAPHRASE = """
Machine learning is an area within artificial intelligence that allows computers to
learn and get better from experience without direct programming. The main focus is
building programs that can access information and use it to teach themselves. This process
starts with examples, direct experience, or directions. ML algorithms employ computational
techniques to extract knowledge directly from data rather than using a fixed equation.
"""

SAMPLE_AI_GENERATED = """
Machine learning represents a transformative paradigm in the realm of artificial intelligence,
wherein computational systems are endowed with the remarkable capacity to assimilate knowledge
and enhance their performance iteratively through experiential interaction with data, thereby
obviating the necessity for explicit algorithmic instruction. This sophisticated discipline
concentrates on the development of sophisticated algorithmic frameworks that possess the
inherent capability to access, process, and derive meaningful insights from structured datasets.
"""

SAMPLE_ORIGINAL_2 = """
The water cycle describes how water evaporates from the surface of the earth, rises into the
atmosphere, cools and condenses into rain or snow in clouds, and falls again to the surface
as precipitation. The water falling on land collects in rivers and lakes, soil, and porous layers
of rock, and much of it eventually flows back into the ocean, where it will once more evaporate.
"""


def seed():
    app = create_app()
    with app.app_context():
        # Clean slate
        db.drop_all()
        db.create_all()

        course = Course(
            name="Introduction to Computer Science",
            code="CS101",
            instructor="Prof. Sarah Johnson",
        )
        db.session.add(course)
        db.session.flush()

        assignment = Assignment(
            course_id=course.id,
            title="Essay: Foundations of Machine Learning",
            description="Write a 500-word essay explaining the core concepts of machine learning.",
        )
        db.session.add(assignment)
        db.session.flush()

        submissions = [
            Submission(assignment_id=assignment.id, student_id="STU001",
                       student_name="Alice Chen",    content=SAMPLE_ORIGINAL.strip()),
            Submission(assignment_id=assignment.id, student_id="STU002",
                       student_name="Bob Williams",  content=SAMPLE_PARAPHRASE.strip()),
            Submission(assignment_id=assignment.id, student_id="STU003",
                       student_name="Charlie Davis", content=SAMPLE_AI_GENERATED.strip()),
            Submission(assignment_id=assignment.id, student_id="STU004",
                       student_name="Diana Park",    content=SAMPLE_ORIGINAL_2.strip()),
        ]
        for s in submissions:
            db.session.add(s)
        db.session.commit()

        print("Seeding complete. Running analysis on all submissions…\n")
        for s in submissions:
            report = analyze_submission(s.id)
            if report:
                print(
                    f"  {s.student_name:20s}  verdict={report.verdict:12s}  "
                    f"risk={report.overall_risk_score:.2f}  "
                    f"ai={report.ai_generated_score:.2f}"
                )

        print("\nDatabase seeded OK. Run `flask run` and open http://localhost:5000")


if __name__ == "__main__":
    seed()
