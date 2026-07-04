import os
import re
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from src.models import Job
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"
THEMUSE_API_URL = "https://www.themuse.com/api/public/jobs"
UPWORK_API_URL = "https://api.upwork.com/graphql"


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common HTML entities from a string."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#x26;", "&").replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _fetch_with_retry(url: str, params: dict, headers: dict) -> requests.Response:
    response = requests.get(url, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    return response


def fetch_arbeitnow_jobs(pages: int) -> list[Job]:
    """Fetch job listings from the Arbeitnow public API."""
    jobs: list[Job] = []
    logger.info(f"Fetching Arbeitnow jobs for {pages} pages...")
    for page in range(1, pages + 1):
        try:
            response = _fetch_with_retry(
                ARBEITNOW_API_URL,
                params={"page": page},
                headers={"Accept": "application/json"}
            )
            data = response.json()
            raw_jobs = data.get("data", [])

            for item in raw_jobs:
                try:
                    job = Job(
                        slug=item.get("slug", ""),
                        company_name=item.get("company_name", "Unknown"),
                        title=item.get("title", "Untitled"),
                        description=_strip_html(item.get("description", "")),
                        remote=item.get("remote", False),
                        url=item.get("url", ""),
                        tags=item.get("tags", []),
                        job_types=item.get("job_types", []),
                        location=item.get("location", ""),
                        created_at=item.get("created_at", 0),
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing Arbeitnow job: {e}")
                    continue
        except Exception as exc:
            logger.error(f"Failed to fetch Arbeitnow page {page}: {exc}")
            break
    logger.info(f"Fetched {len(jobs)} jobs from Arbeitnow.")
    return jobs


def fetch_themuse_jobs(pages: int) -> list[Job]:
    """Fetch job listings from The Muse API."""
    jobs: list[Job] = []
    logger.info(f"Fetching The Muse jobs for {pages} pages...")
    for page in range(1, pages + 1):
        try:
            response = _fetch_with_retry(
                THEMUSE_API_URL,
                params={"page": page},
                headers={"Accept": "application/json"}
            )
            data = response.json()
            raw_jobs = data.get("results", [])

            for item in raw_jobs:
                try:
                    company = item.get("company", {})
                    company_name = company.get("name", "Unknown") if isinstance(company, dict) else "Unknown"
                    
                    refs = item.get("refs", {})
                    url = refs.get("landing_page", "") if isinstance(refs, dict) else ""
                    
                    locations = [loc.get("name") for loc in item.get("locations", []) if isinstance(loc, dict)]
                    location = locations[0] if locations else ""
                    
                    job = Job(
                        slug=str(item.get("id", "")),
                        company_name=company_name,
                        title=item.get("name", "Untitled"),
                        description=_strip_html(item.get("contents", "")),
                        remote="Flexible / Remote" in locations,
                        url=url,
                        tags=[c.get("name", "") for c in item.get("categories", []) if isinstance(c, dict)],
                        job_types=[lvl.get("name", "") for lvl in item.get("levels", []) if isinstance(lvl, dict)],
                        location=location,
                        created_at=0,
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing The Muse job: {e}")
                    continue
        except Exception as exc:
            logger.error(f"Failed to fetch The Muse page {page}: {exc}")
            break
    logger.info(f"Fetched {len(jobs)} jobs from The Muse.")
    return jobs


def fetch_upwork_jobs() -> list[Job]:
    """Fetch job listings from Upwork GraphQL API if token is provided."""
    token = os.environ.get("UPWORK_ACCESS_TOKEN")
    if not token or token == "your_upwork_graphql_token_here":
        logger.info("Skipping Upwork: No valid UPWORK_ACCESS_TOKEN provided.")
        return []
        
    jobs: list[Job] = []
    logger.info("Fetching Upwork jobs...")
    query = '''
    query {
      marketplaceJobPostings(searchType: USER_JOBS_SEARCH, sortAttributes: { field: RECENCY }) {
        edges {
          node {
            id
            title
            createdDateTime
            description
          }
        }
      }
    }
    '''
    try:
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def _post_with_retry():
            resp = requests.post(
                UPWORK_API_URL,
                json={"query": query},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp

        response = _post_with_retry()
        data = response.json()
        
        edges = data.get("data", {}).get("marketplaceJobPostings", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            try:
                job = Job(
                    slug=node.get("id", ""),
                    company_name="Upwork Client",
                    title=node.get("title", "Untitled"),
                    description=_strip_html(node.get("description", "")),
                    remote=True,
                    url=f"https://www.upwork.com/jobs/{node.get('id', '')}",
                    tags=[],
                    job_types=["Freelance"],
                    location="Remote",
                    created_at=0,
                )
                jobs.append(job)
            except Exception as e:
                logger.debug(f"Error parsing Upwork job: {e}")
                continue
        logger.info(f"Fetched {len(jobs)} jobs from Upwork.")
    except Exception as exc:
        logger.error(f"Failed to fetch Upwork jobs: {exc}")
        
    return jobs


def search_jobs(pages: int = 3) -> list[Job]:
    """
    Fetch job listings from available APIs using retries.

    Args:
        pages: Number of pages to fetch per API.

    Returns:
        A combined list of Job objects.
    """
    jobs: list[Job] = []
    
    jobs.extend(fetch_arbeitnow_jobs(pages))
    jobs.extend(fetch_themuse_jobs(pages))
    jobs.extend(fetch_upwork_jobs())
    
    logger.info(f"Total jobs fetched: {len(jobs)}")
    return jobs
