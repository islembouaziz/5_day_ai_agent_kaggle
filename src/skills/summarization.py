import json
import re
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import Job
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"


def _parse_json_response(text: str) -> dict:
    """Extract and parse a JSON object from a model response string."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from model response: {text[:300]}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_cv_summary(client: genai.Client, cv_text: str) -> dict:
    """Generate a CV summary and global improvement suggestions."""
    logger.info("Generating CV summary...")
    prompt = f"""You are a professional career advisor.

Analyze this candidate's CV and provide actionable improvement advice.

## Candidate CV:
{cv_text[:4000]}

## Task:
Respond ONLY with a valid JSON object (no markdown, no explanation) in this exact format:
{{
  "cv_summary": "<2-3 sentence professional summary of the candidate>",
  "global_suggestions": [
    "<specific actionable suggestion 1>",
    "<specific actionable suggestion 2>",
    "<specific actionable suggestion 3>",
    "<specific actionable suggestion 4>"
  ],
  "top_missing_skills": [
    "<skill or area to develop 1>",
    "<skill or area to develop 2>",
    "<skill or area to develop 3>"
  ]
}}
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    return _parse_json_response(response.text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def summarize_job(client: genai.Client, job: Job) -> str:
    """Generate a concise 1-2 sentence summary of a job description."""
    prompt = f"""Summarize this job description in 1 or 2 concise sentences, focusing on the core responsibilities and key requirements.

## Job Title: {job.title}
## Job Description:
{job.description[:2000]}

Respond with ONLY the summary text."""
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="text/plain"
        )
    )
    return response.text.strip()
