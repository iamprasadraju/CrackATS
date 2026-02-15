"""FastAPI web interface for job scraper."""

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from scraper import scrape_job as scraper_scrape_job
from concurrent.futures import ThreadPoolExecutor
import asyncio

app = FastAPI(title="Job Scraper")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Thread pool for running sync scraper
executor = ThreadPoolExecutor(max_workers=3)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page."""
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text()


@app.post("/scrape")
async def scrape_job_endpoint(url: str = Form(...)):
    """Scrape a job posting from URL."""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        # Run sync scraper in thread pool
        loop = asyncio.get_event_loop()
        job = await loop.run_in_executor(executor, scraper_scrape_job, url)
        if not job:
            raise HTTPException(status_code=404, detail="Could not extract job data")
        return {
            "success": True,
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "description": job.get("description", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
