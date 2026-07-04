"""
CV Job Matcher — FastAPI Application
=====================================
Upload your CV as a PDF to get AI-powered job matches and improvement tips.
"""
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from dotenv import load_dotenv
from google import genai

# Load environment variables (e.g., GEMINI_API_KEY, UPWORK_ACCESS_TOKEN)
load_dotenv()

from src.utils.logger import setup_logger
from src.utils.cv_parser import extract_text_from_pdf
from src.skills.search import search_jobs
from src.skills.filtering import filter_jobs
from src.skills.ranking import rank_jobs
from src.skills.summarization import generate_cv_summary
from src.models import CVAnalysis, UserPreferences
from src.memory import memory

logger = setup_logger(__name__)

app = FastAPI(
    title="CV Job Matcher",
    description="Upload your CV to find matching jobs and get AI-powered improvement tips.",
    version="1.0.0",
)

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY is not set in the environment!")

@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the main frontend HTML page."""
    return FileResponse("static/index.html")

@app.get("/preferences", response_model=UserPreferences)
async def get_preferences():
    """Get the current user preferences."""
    prefs_dict = memory.get_preferences()
    return UserPreferences(**prefs_dict)

@app.post("/preferences", response_model=UserPreferences)
async def update_preferences(prefs: UserPreferences):
    """Update user preferences for job filtering."""
    updated = memory.update_preferences(prefs.model_dump())
    logger.info(f"Updated preferences: {updated}")
    return UserPreferences(**updated)

@app.get("/jobs")
async def get_jobs(pages: int = 2):
    """
    Fetch raw job listings from APIs (no AI ranking).
    """
    try:
        jobs = search_jobs(pages=pages)
        prefs = UserPreferences(**memory.get_preferences())
        filtered_jobs = filter_jobs(jobs, prefs)
        return {"count": len(filtered_jobs), "jobs": [j.model_dump() for j in filtered_jobs]}
    except Exception as exc:
        logger.error(f"Failed to fetch jobs: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/analyze", response_model=CVAnalysis)
async def analyze_cv(file: UploadFile = File(...)) -> JSONResponse:
    """
    Upload a CV PDF and get AI-powered job matches with a gap analysis.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured on the server.")
        
    client = genai.Client(api_key=api_key)

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        cv_text = extract_text_from_pdf(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 1. Search for jobs
    try:
        jobs = search_jobs(pages=3)
    except Exception as exc:
        logger.error(f"Search skill failed: {exc}")
        raise HTTPException(status_code=503, detail="Failed to fetch jobs.") from exc

    if not jobs:
        raise HTTPException(status_code=503, detail="No jobs could be fetched.")

    # 2. Filter jobs based on preferences
    prefs = UserPreferences(**memory.get_preferences())
    filtered_jobs = filter_jobs(jobs, prefs)
    
    if not filtered_jobs:
        raise HTTPException(
            status_code=404, 
            detail="No jobs matched your current preferences. Try broadening your settings."
        )

    # 3. Summarize CV
    try:
        summary_data = generate_cv_summary(client, cv_text)
    except Exception as exc:
        logger.error(f"CV Summarization failed: {exc}")
        summary_data = {
            "cv_summary": "Summary could not be generated.",
            "global_suggestions": [],
            "top_missing_skills": []
        }

    # 4. Rank Jobs (includes job summarization per job)
    try:
        matched_jobs = rank_jobs(client, cv_text, filtered_jobs, limit=20)
    except Exception as exc:
        logger.error(f"Job Ranking failed: {exc}")
        raise HTTPException(status_code=500, detail="AI ranking failed.") from exc

    analysis = CVAnalysis(
        cv_summary=summary_data.get("cv_summary", "Summary not available."),
        matched_jobs=matched_jobs,
        global_suggestions=summary_data.get("global_suggestions", []),
        top_missing_skills=summary_data.get("top_missing_skills", []),
    )

    return JSONResponse(content=analysis.model_dump())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
