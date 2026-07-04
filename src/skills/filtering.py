from src.models import Job, UserPreferences
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def filter_jobs(jobs: list[Job], prefs: UserPreferences) -> list[Job]:
    """
    Filter jobs based on user preferences.
    """
    logger.info(f"Filtering {len(jobs)} jobs with preferences: {prefs}")
    filtered = []
    for job in jobs:
        # Check remote only
        if prefs.remote_only and not job.remote:
            continue
            
        # Check locations
        if prefs.locations:
            job_loc = job.location.lower() if job.location else ""
            match_loc = any(loc.lower() in job_loc for loc in prefs.locations)
            if not match_loc and not job.remote:
                continue # If not match loc and not remote, drop it
                
        # Check keywords
        if prefs.keywords:
            text_to_search = (job.title + " " + job.description + " " + " ".join(job.tags)).lower()
            match_kw = any(kw.lower() in text_to_search for kw in prefs.keywords)
            if not match_kw:
                continue

        filtered.append(job)
        
    logger.info(f"{len(filtered)} jobs remaining after filtering.")
    return filtered
