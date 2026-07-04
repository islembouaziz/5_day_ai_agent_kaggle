import re
import os
import requests
from src.models import Job


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


def fetch_arbeitnow_jobs(pages: int) -> list[Job]:
    """Fetch job listings from the Arbeitnow public API."""
    jobs: list[Job] = []
    for page in range(1, pages + 1):
        try:
            response = requests.get(
                ARBEITNOW_API_URL,
                params={"page": page},
                timeout=15,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
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
                except Exception:
                    continue
        except requests.RequestException as exc:
            print(f"[job_fetcher] Warning: Failed to fetch Arbeitnow page {page}: {exc}")
            break
    return jobs


def fetch_themuse_jobs(pages: int) -> list[Job]:
    """Fetch job listings from The Muse API."""
    jobs: list[Job] = []
    for page in range(1, pages + 1):
        try:
            response = requests.get(
                THEMUSE_API_URL,
                params={"page": page},
                timeout=15,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
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
                        created_at=0, # The Muse API provides publication_date but requires parsing
                    )
                    jobs.append(job)
                except Exception:
                    continue
        except requests.RequestException as exc:
            print(f"[job_fetcher] Warning: Failed to fetch The Muse page {page}: {exc}")
            break
    return jobs


def fetch_upwork_jobs() -> list[Job]:
    """Fetch job listings from Upwork GraphQL API if token is provided."""
    token = os.environ.get("UPWORK_ACCESS_TOKEN")
    if not token or token == "your_upwork_graphql_token_here":
        print("[job_fetcher] Skipping Upwork: No UPWORK_ACCESS_TOKEN provided.")
        return []
        
    jobs: list[Job] = []
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
        response = requests.post(
            UPWORK_API_URL,
            json={"query": query},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=15,
        )
        response.raise_for_status()
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
            except Exception:
                continue
    except requests.RequestException as exc:
        print(f"[job_fetcher] Warning: Failed to fetch Upwork jobs: {exc}")
        
    return jobs


def fetch_jobs(pages: int = 3) -> list[Job]:
    """
    Fetch job listings from available APIs.

    Args:
        pages: Number of pages to fetch per API.

    Returns:
        A combined list of Job objects.
    """
    jobs: list[Job] = []
    
    print("[job_fetcher] Fetching jobs from Arbeitnow...")
    jobs.extend(fetch_arbeitnow_jobs(pages))
    
    print("[job_fetcher] Fetching jobs from The Muse...")
    jobs.extend(fetch_themuse_jobs(pages))
    
    print("[job_fetcher] Fetching jobs from Upwork...")
    jobs.extend(fetch_upwork_jobs())
    
    return jobs
