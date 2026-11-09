"""
Core plagiarism analysis engine.
Combines TF-IDF cosine similarity with IBM Granite LLM analysis.
"""

import os
import logging
import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import db, Submission, PlagiarismReport
from granite_client import granite_client

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD  = float(os.getenv("SIMILARITY_THRESHOLD",  0.75))
AI_THRESHOLD          = float(os.getenv("AI_GENERATED_THRESHOLD", 0.65))
FLAG_THRESHOLD        = float(os.getenv("FLAG_THRESHOLD",         0.80))


# ── Text utilities ─────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _extract_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]


# ── Similarity engine ──────────────────────────────────────────

def compute_tfidf_similarity(text_a: str, texts: list[str]) -> list[float]:
    """Return cosine similarity scores between text_a and each text in `texts`."""
    if not texts:
        return []
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        corpus  = [_clean_text(text_a)] + [_clean_text(t) for t in texts]
        matrix  = vectorizer.fit_transform(corpus)
        sims    = cosine_similarity(matrix[0:1], matrix[1:])[0]
        return sims.tolist()
    except Exception as exc:
        logger.error("TF-IDF similarity error: %s", exc)
        return [0.0] * len(texts)


def find_matched_passages(submission: str, reference: str, threshold: float = 0.6) -> list[dict]:
    """Find sentence-level matches between submission and a reference text."""
    sub_sentences = _extract_sentences(submission)
    ref_sentences = _extract_sentences(reference)
    if not sub_sentences or not ref_sentences:
        return []

    matches = []
    for sub_sent in sub_sentences:
        sims = compute_tfidf_similarity(sub_sent, ref_sentences)
        if sims:
            best_idx   = int(np.argmax(sims))
            best_score = sims[best_idx]
            if best_score >= threshold:
                matches.append({
                    "submission_sentence": sub_sent,
                    "reference_sentence":  ref_sentences[best_idx],
                    "similarity":          round(best_score, 4),
                })
    return matches[:10]   # cap at 10 passages


# ── Main analysis orchestrator ─────────────────────────────────

def analyze_submission(submission_id: int) -> Optional[PlagiarismReport]:
    """
    Full analysis pipeline for a submission:
    1. TF-IDF similarity against all other submissions in the same assignment
    2. IBM Granite deep analysis (plagiarism + AI detection)
    3. Persist PlagiarismReport
    """
    submission: Optional[Submission] = db.session.get(Submission, submission_id)
    if not submission:
        logger.error("Submission %d not found.", submission_id)
        return None

    # ── 1. Gather peer submissions ─────────────────────────────
    peers: list[Submission] = (
        Submission.query
        .filter(
            Submission.assignment_id == submission.assignment_id,
            Submission.id != submission.id,
        )
        .all()
    )
    peer_texts = [p.content for p in peers]

    # ── 2. TF-IDF similarity ───────────────────────────────────
    tfidf_scores = compute_tfidf_similarity(submission.content, peer_texts)
    max_similarity = max(tfidf_scores, default=0.0)

    # Build matched sources list
    matched_sources = []
    for peer, score in zip(peers, tfidf_scores):
        if score >= SIMILARITY_THRESHOLD * 0.6:   # include borderline hits too
            passages = find_matched_passages(submission.content, peer.content)
            matched_sources.append({
                "student_id":   peer.student_id,
                "student_name": peer.student_name,
                "similarity":   round(score, 4),
                "passages":     passages,
            })
    matched_sources.sort(key=lambda x: x["similarity"], reverse=True)

    # ── 3. IBM Granite analysis ────────────────────────────────
    granite_result = granite_client.analyze_plagiarism(
        submission_text = submission.content,
        reference_texts = peer_texts[:5],   # send top-5 peers
    )
    ai_result = granite_client.detect_ai_content(submission.content)

    # ── 4. Aggregate scores ────────────────────────────────────
    granite_sim  = float(granite_result.get("similarity_score",   0.0))
    granite_ai   = float(granite_result.get("ai_generated_score", 0.0))
    granite_para = float(granite_result.get("paraphrase_score",   0.0))
    ai_score     = float(ai_result.get("ai_generated_score",      0.0))

    # Weighted combination: TF-IDF (40%) + Granite similarity (35%) + AI (25%)
    final_similarity   = 0.40 * max_similarity + 0.35 * granite_sim + 0.25 * granite_para
    final_ai_score     = 0.5 * granite_ai + 0.5 * ai_score
    overall_risk       = max(final_similarity, final_ai_score,
                             float(granite_result.get("paraphrase_score", 0.0)))

    # ── 5. Verdict ─────────────────────────────────────────────
    if overall_risk >= FLAG_THRESHOLD:
        verdict = "flagged"
    elif overall_risk >= SIMILARITY_THRESHOLD:
        verdict = "suspicious"
    else:
        verdict = "clean"

    # Use Granite's verdict if stronger
    granite_verdict = granite_result.get("verdict", "clean")
    if granite_verdict == "flagged":
        verdict = "flagged"
    elif granite_verdict == "suspicious" and verdict == "clean":
        verdict = "suspicious"

    # ── 6. Persist report ─────────────────────────────────────
    explanation = (
        granite_result.get("explanation", "") or
        f"Overall risk score: {overall_risk:.2%}. "
        f"Similarity to peers: {final_similarity:.2%}. "
        f"AI-generated probability: {final_ai_score:.2%}."
    )

    flagged_passages = granite_result.get("flagged_passages", [])

    # Remove existing report if re-analysing
    existing = PlagiarismReport.query.filter_by(submission_id=submission_id).first()
    if existing:
        db.session.delete(existing)
        db.session.flush()

    report = PlagiarismReport(
        submission_id       = submission_id,
        similarity_score    = round(final_similarity,   4),
        ai_generated_score  = round(final_ai_score,     4),
        paraphrase_score    = round(granite_para,       4),
        overall_risk_score  = round(overall_risk,       4),
        verdict             = verdict,
        granite_explanation = explanation,
        matched_sources     = matched_sources,
        flagged_passages    = flagged_passages,
    )
    db.session.add(report)
    db.session.commit()

    logger.info(
        "Submission %d analysed | verdict=%s  risk=%.2f",
        submission_id, verdict, overall_risk,
    )
    return report
