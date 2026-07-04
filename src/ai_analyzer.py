import json
import re
import os

from google import genai
from google.genai import types
from src.models import Job, MatchedJob, CVAnalysis


# How many jobs to send to the AI for scoring (avoid hitting context limits)
MAX_JOBS_TO_SCORE = 30

# Minimum score to include in results
MIN_SCORE_THRESHOLD = 30

GEMINI_MODEL = "gemini-2.5-flash"


def _build_scoring_prompt(cv_text: str, job: Job) -> str:
    """Build the prompt sent to Gemini for a single job vs. the CV."""
    return f"""You are a professional career advisor and HR specialist.

Analyze how well this candidate's CV matches this job offer.

## Candidate CV:
{cv_text[:3000]}

## Job Offer:
Title: {job.title}
Company: {job.company_name}
Location: {job.location}
Tags: {", ".join(job.tags)}
Description:
{job.description[:2000]}

## Task:
Respond ONLY with a valid JSON object (no markdown, no explanation) in this exact format:
{{
  "match_score": <integer 0-100>,
  "match_reasons": [<string>, <string>, <string>],
  "missing_skills": [<string>, <string>, <string>]
}}

Rules:
- match_score: 0=totally unrelated, 100=perfect match
- match_reasons: 2-4 specific reasons why this job fits the candidate
- missing_skills: 2-4 specific skills/experience the job requires that the candidate lacks
- Be honest and specific. Focus on technical skills, domain, seniority level.
"""


def _build_summary_prompt(cv_text: str) -> str:
    """Build the prompt to generate a CV summary and global suggestions."""
    return f"""You are a professional career advisor.

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


def _parse_json_response(text: str) -> dict:
    """Extract and parse a JSON object from a model response string."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from model response: {text[:300]}")


def _score_job(client: genai.Client, cv_text: str, job: Job) -> MatchedJob | None:
    """
    Ask Gemini to score a single job against the CV.

    Returns a MatchedJob or None if scoring fails.
    """
    try:
        prompt = _build_scoring_prompt(cv_text, job)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        raw = response.text
        data = _parse_json_response(raw)

        return MatchedJob(
            slug=job.slug,
            company_name=job.company_name,
            title=job.title,
            url=job.url,
            location=job.location,
            remote=job.remote,
            tags=job.tags,
            job_types=job.job_types,
            match_score=int(data.get("match_score", 0)),
            match_reasons=data.get("match_reasons", []),
            missing_skills=data.get("missing_skills", []),
        )
    except Exception as exc:
        print(f"[ai_analyzer] Warning: Failed to score job '{job.title}': {exc}")
        return None


def analyze_cv_against_jobs(cv_text: str, jobs: list[Job]) -> CVAnalysis:
    """
    Main entry point: analyze the CV against a list of jobs using Gemini.

    Steps:
      1. Generate a CV summary and global improvement suggestions.
      2. Score each job against the CV (limited to MAX_JOBS_TO_SCORE).
      3. Filter by MIN_SCORE_THRESHOLD, sort by score descending.
      4. Return a CVAnalysis object.

    Args:
        cv_text: Plain text extracted from the CV PDF.
        jobs: List of Job objects.

    Returns:
        A CVAnalysis object ready to be serialized and sent to the frontend.
    """
    print(f"[ai_analyzer] Starting analysis with Gemini model '{GEMINI_MODEL}'...")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)

    # Step 1: Generate CV summary & global suggestions
    print("[ai_analyzer] Generating CV summary...")
    cv_summary = "CV analysis complete."
    global_suggestions: list[str] = []
    top_missing_skills: list[str] = []

    try:
        summary_prompt = _build_summary_prompt(cv_text)
        summary_response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=summary_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        summary_data = _parse_json_response(summary_response.text)
        cv_summary = summary_data.get("cv_summary", cv_summary)
        global_suggestions = summary_data.get("global_suggestions", [])
        top_missing_skills = summary_data.get("top_missing_skills", [])
    except Exception as exc:
        print(f"[ai_analyzer] Warning: CV summary failed: {exc}")

    # Step 2: Score jobs (limit to avoid long waits)
    jobs_to_score = jobs[:MAX_JOBS_TO_SCORE]
    print(f"[ai_analyzer] Scoring {len(jobs_to_score)} jobs...")

    matched_jobs: list[MatchedJob] = []
    for i, job in enumerate(jobs_to_score):
        print(f"[ai_analyzer] Scoring job {i + 1}/{len(jobs_to_score)}: {job.title}")
        result = _score_job(client, cv_text, job)
        if result and result.match_score >= MIN_SCORE_THRESHOLD:
            matched_jobs.append(result)

    # Step 3: Sort by score descending
    matched_jobs.sort(key=lambda j: j.match_score, reverse=True)

    print(f"[ai_analyzer] Done. {len(matched_jobs)} jobs matched above threshold.")

    return CVAnalysis(
        cv_summary=cv_summary,
        matched_jobs=matched_jobs,
        global_suggestions=global_suggestions,
        top_missing_skills=top_missing_skills,
    )
