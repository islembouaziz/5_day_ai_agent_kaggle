# CV Job Matcher (Kaggle 5-Day AI Agents Capstone)

CV Job Matcher is an AI-powered agent that analyzes a candidate's CV and finds matching jobs using external APIs, grading the matches with Google's Gemini models.

## 🎥 Project Demo Video
https://github.com/islembouaziz/5_day_ai_agent_kaggle/blob/main/Video%20Project.mp4

*(If the embedded player above doesn't load, you can [click here to watch the video](https://github.com/islembouaziz/5_day_ai_agent_kaggle/blob/main/Video%20Project.mp4))*

## 🧠 Course Concepts Applied
This project was built as the capstone for the Kaggle **5-Day AI Agents Intensive Course** with Google. Here is how the course concepts are applied in this agent:

- **Day 1: Intro to Agents & Vibe Coding:** The project was built using vibe coding workflows to architect an autonomous agent that takes a natural language document (CV) and orchestrates a multi-step workflow.
- **Day 2: Agent Tools & Interoperability:** The agent seamlessly connects to external APIs (Arbeitnow, The Muse, Upwork) to fetch live data, demonstrating powerful external tool use.
- **Day 3: Agent Skills:** The agent uses modular, discrete skills (`search`, `filtering`, `ranking`, `summarization`) to break down complex reasoning tasks. It also features long-term memory for user preferences (`preferences.json`).
- **Day 4: Security & Evaluation:** The agent implements guardrails by parsing the PDF strictly, filtering API results locally *before* sending them to the LLM, and generating predictable, structured JSON output.
- **Day 5: Production Grade Development:** Built as a scalable, modular FastAPI web service with a clean UI, the agent is structured for production and ready for cloud deployment.

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
