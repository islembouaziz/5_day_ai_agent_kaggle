from pydantic import BaseModel, Field
from typing import Optional


class Job(BaseModel):
    """Represents a single job listing from the APIs."""
    slug: str
    company_name: str
    title: str
    description: str
    remote: bool
    url: str
    tags: list[str]
    job_types: list[str]
    location: str
    created_at: int


class MatchedJob(BaseModel):
    """A job enriched with AI-generated match score and analysis."""
    slug: str
    company_name: str
    title: str
    url: str
    location: str
    remote: bool
    tags: list[str]
    job_types: list[str]
    match_score: int          # 0–100
    match_reasons: list[str]  # Why it's a good match
    missing_skills: list[str] # Skills in the job that are missing from the CV
    job_summary: Optional[str] = None # Quick summary of the job description


class CVAnalysis(BaseModel):
    """Top-level analysis result returned to the frontend."""
    cv_summary: str             # Short summary of what the CV shows
    matched_jobs: list[MatchedJob]
    global_suggestions: list[str]  # Global CV improvements
    top_missing_skills: list[str]  # Consolidated skills to learn/add


class UserPreferences(BaseModel):
    """User preferences for filtering jobs."""
    remote_only: bool = Field(default=False)
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
