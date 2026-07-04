# CV Job Matcher

CV Job Matcher is an AI-powered agent that analyzes a candidate's CV and finds matching jobs using external APIs, grading the matches with Google's Gemini models.

## Features
- **Job Searching**: Fetches remote and local jobs from multiple APIs (Arbeitnow, The Muse, Upwork).
- **Skill Filtering**: Filters jobs based on user preferences.
- **AI Ranking**: Uses Google Gemini to score each job against the uploaded CV, providing detailed match reasons and identifying missing skills.
- **CV Summarization**: Generates an AI summary of the CV and actionable improvement suggestions.
- **User Preferences**: Remembers your basic settings (e.g., remote only, desired role) via a simple file-backed memory (`preferences.json`).

## Project Structure
The project has been refactored to follow Google AI Agents best practices:
- `src/skills/`: Modular agent skills (`search.py`, `filtering.py`, `ranking.py`, `summarization.py`).
- `src/utils/`: Shared utilities like `logger.py` and `cv_parser.py`.
- `src/memory.py`: User preferences management.
- `main.py`: The FastAPI orchestrator.

## Installation

1. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   *Note: `GEMINI_API_KEY` is required. `UPWORK_ACCESS_TOKEN` is optional.*

## Usage

1. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

2. Open your browser and navigate to:
   http://127.0.0.1:8000

3. Upload a PDF CV and the agent will fetch jobs, rank them, and return a comprehensive analysis.
