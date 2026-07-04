import json
import re
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import Job, MatchedJob
from src.utils.logger import setup_logger
from src.skills.summarization import summarize_job

logger = setup_logger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
MIN_SCORE_THRESHOLD = 30


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
def _score_job(client: genai.Client, cv_text: str, job: Job) -> dict:
    """Ask Gemini to score a single job against the CV."""
    prompt = f"""You are a professional career advisor and HR specialist.

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
  "match_reasons": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "missing_skills": ["<skill 1>", "<skill 2>"]
}}

Rules:
- match_score: 0=totally unrelated, 100=perfect match
- match_reasons: 2-4 specific reasons why this job fits the candidate
- missing_skills: 2-4 specific skills/experience the job requires that the candidate lacks
- Be honest and specific. Focus on technical skills, domain, seniority level.
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    return _parse_json_response(response.text)


def rank_jobs(client: genai.Client, cv_text: str, jobs: list[Job], limit: int = 10) -> list[MatchedJob]:
    """
    Score a list of jobs against the CV and return the top matches.
    We limit the number of jobs scored to avoid API limits.
    """
    jobs_to_score = jobs[:limit]
    logger.info(f"Scoring {len(jobs_to_score)} jobs against the CV...")
    
    matched_jobs: list[MatchedJob] = []
    
    for i, job in enumerate(jobs_to_score):
        logger.info(f"Scoring job {i + 1}/{len(jobs_to_score)}: {job.title}")
        try:
            # Generate Match Score
            data = _score_job(client, cv_text, job)
            score = int(data.get("match_score", 0))
            
            if score >= MIN_SCORE_THRESHOLD:
                # Generate a quick summary of the job description
                try:
                    job_summary = summarize_job(client, job)
                except Exception as e:
                    logger.warning(f"Failed to summarize job {job.title}: {e}")
                    job_summary = "Summary unavailable."
                    
                matched_jobs.append(
                    MatchedJob(
                        slug=job.slug,
                        company_name=job.company_name,
                        title=job.title,
                        url=job.url,
                        location=job.location,
                        remote=job.remote,
                        tags=job.tags,
                        job_types=job.job_types,
                        match_score=score,
                        match_reasons=data.get("match_reasons", []),
                        missing_skills=data.get("missing_skills", []),
                        job_summary=job_summary,
                    )
                )
        except Exception as exc:
            logger.error(f"Failed to score job '{job.title}': {exc}")

    # Sort by score descending
    matched_jobs.sort(key=lambda j: j.match_score, reverse=True)
    logger.info(f"Done ranking. {len(matched_jobs)} jobs matched above threshold.")
    
    return matched_jobs
