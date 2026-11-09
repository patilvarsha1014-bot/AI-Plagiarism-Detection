"""
IBM Granite (watsonx.ai) client wrapper.
Handles authentication, prompt construction, and response parsing
for plagiarism analysis tasks.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False
    logger.warning("ibm-watsonx-ai not installed – running in mock mode.")


class GraniteClient:
    """Thin wrapper around IBM Granite via watsonx.ai."""

    def __init__(self):
        self.api_key    = os.getenv("IBM_CLOUD_API_KEY", "")
        self.url        = os.getenv("IBM_WATSONX_URL",   "https://us-south.ml.cloud.ibm.com")
        self.project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "")
        self.model_id   = os.getenv("IBM_GRANITE_MODEL_ID",   "ibm/granite-13b-instruct-v2")
        self._model: Optional[object] = None

        if WATSONX_AVAILABLE and self.api_key and self.project_id:
            try:
                credentials = Credentials(url=self.url, api_key=self.api_key)
                client      = APIClient(credentials)
                self._model = ModelInference(
                    model_id   = self.model_id,
                    api_client = client,
                    project_id = self.project_id,
                    params={
                        GenParams.MAX_NEW_TOKENS: 1024,
                        GenParams.TEMPERATURE:    0.2,
                        GenParams.TOP_P:          0.9,
                        GenParams.REPETITION_PENALTY: 1.1,
                    },
                )
                logger.info("IBM Granite model '%s' initialised ✓", self.model_id)
            except Exception as exc:
                logger.error("Failed to initialise IBM Granite: %s", exc)
                self._model = None
        else:
            logger.info("IBM Granite running in MOCK mode (credentials not set).")

    # ── Public methods ─────────────────────────────────────────

    def analyze_plagiarism(self, submission_text: str, reference_texts: list[str]) -> dict:
        """
        Ask Granite to evaluate a submission for plagiarism, AI generation,
        paraphrasing, and produce a structured JSON-like explanation.
        """
        prompt = self._build_plagiarism_prompt(submission_text, reference_texts)
        raw    = self._generate(prompt)
        return self._parse_plagiarism_response(raw)

    def detect_ai_content(self, text: str) -> dict:
        """Ask Granite whether the text looks AI-generated."""
        prompt = self._build_ai_detection_prompt(text)
        raw    = self._generate(prompt)
        return self._parse_ai_response(raw)

    def explain_similarity(self, text_a: str, text_b: str) -> str:
        """Ask Granite to explain why two texts are similar."""
        prompt = (
            "You are an academic integrity expert.\n"
            "Compare the two texts below and explain in 3-5 sentences "
            "why they may be similar or constitute plagiarism. "
            "Be specific about sentence structures, vocabulary, and ideas.\n\n"
            f"TEXT A:\n{text_a[:1500]}\n\n"
            f"TEXT B:\n{text_b[:1500]}\n\n"
            "Explanation:"
        )
        return self._generate(prompt)

    # ── Prompt builders ────────────────────────────────────────

    @staticmethod
    def _build_plagiarism_prompt(submission: str, references: list[str]) -> str:
        refs_block = "\n\n".join(
            f"[Reference {i+1}]:\n{r[:800]}" for i, r in enumerate(references[:5])
        )
        return (
            "You are an AI academic integrity analyzer powered by IBM Granite.\n"
            "Analyze the SUBMISSION against the REFERENCE texts.\n"
            "Respond with a JSON object containing:\n"
            "  - similarity_score: float 0-1\n"
            "  - ai_generated_score: float 0-1\n"
            "  - paraphrase_score: float 0-1\n"
            "  - verdict: one of [clean, suspicious, flagged]\n"
            "  - flagged_passages: list of short quoted strings from submission\n"
            "  - explanation: 3-5 sentence explanation\n\n"
            f"SUBMISSION:\n{submission[:2000]}\n\n"
            f"REFERENCES:\n{refs_block}\n\n"
            "JSON Response:"
        )

    @staticmethod
    def _build_ai_detection_prompt(text: str) -> str:
        return (
            "You are an expert at detecting AI-generated academic text.\n"
            "Analyze the following text and respond with JSON:\n"
            "  - ai_generated_score: float 0-1 (1 = almost certainly AI)\n"
            "  - reasoning: one sentence\n"
            "  - indicators: list of up to 5 short phrases from the text that suggest AI generation\n\n"
            f"TEXT:\n{text[:2000]}\n\n"
            "JSON Response:"
        )

    # ── Response parsers ───────────────────────────────────────

    @staticmethod
    def _parse_plagiarism_response(raw: str) -> dict:
        import json, re
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        # Fallback – extract scores heuristically
        return {
            "similarity_score":   0.0,
            "ai_generated_score": 0.0,
            "paraphrase_score":   0.0,
            "verdict":            "clean",
            "flagged_passages":   [],
            "explanation":        raw[:500] if raw else "Analysis unavailable.",
        }

    @staticmethod
    def _parse_ai_response(raw: str) -> dict:
        import json, re
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"ai_generated_score": 0.0, "reasoning": raw[:200], "indicators": []}

    # ── Core generation ────────────────────────────────────────

    def _generate(self, prompt: str) -> str:
        if self._model is not None:
            try:
                result = self._model.generate_text(prompt=prompt)
                return result if isinstance(result, str) else str(result)
            except Exception as exc:
                logger.error("Granite generation error: %s", exc)
                return ""
        # Mock response for development without credentials
        return self._mock_response(prompt)

    @staticmethod
    def _mock_response(prompt: str) -> str:
        """Return a plausible mock JSON response when Granite is not available."""
        if "ai_generated_score" in prompt and "ai_generated" not in prompt:
            return ('{"ai_generated_score": 0.12, "reasoning": "Text shows natural variation '
                    'consistent with human writing.", "indicators": []}')
        return (
            '{"similarity_score": 0.18, "ai_generated_score": 0.10, '
            '"paraphrase_score": 0.15, "verdict": "clean", '
            '"flagged_passages": [], '
            '"explanation": "The submission appears to be original work with no significant '
            'matches to reference texts. Minor stylistic similarities are within acceptable '
            'academic norms. No AI-generation patterns detected."}'
        )


# Singleton
granite_client = GraniteClient()
