"""FastAPI web interface for job scraper."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import processor
from scraper import scrape_job as scraper_scrape_job

app = FastAPI(title="Job Scraper")
app.mount("/static", StaticFiles(directory="static"), name="static")
executor = ThreadPoolExecutor(max_workers=3)


def _generate_ai_content(job_data, folder_path):
    """Generate tailored resume and cover letter using Groq API."""
    try:
        import groq_client
    except ImportError:
        raise RuntimeError("groq_client module not found.")

    folder = Path(folder_path)
    master_resume_path = folder / "resume-template.tex"

    if not master_resume_path.exists():
        raise FileNotFoundError(f"Master resume not found: {master_resume_path}")

    master_resume = master_resume_path.read_text(encoding="utf-8")

    tailored_resume = groq_client.generate_tailored_resume(
        job_description=job_data["description"],
        master_resume=master_resume,
    )

    if tailored_resume.startswith("```latex"):
        tailored_resume = tailored_resume[8:]
    if tailored_resume.startswith("```"):
        tailored_resume = tailored_resume[3:]
    if tailored_resume.endswith("```"):
        tailored_resume = tailored_resume[:-3]
    tailored_resume = tailored_resume.strip()

    tailored_resume_path = folder / "Resume.tex"
    tailored_resume_path.write_text(tailored_resume, encoding="utf-8")

    cover_letter = groq_client.generate_cover_letter(
        job_description=job_data["description"],
        tailored_resume=tailored_resume,
        company_name=job_data["company"],
        job_title=job_data["title"],
    )

    if cover_letter.startswith("```"):
        cover_letter = cover_letter[3:]
    if cover_letter.endswith("```"):
        cover_letter = cover_letter[:-3]
    cover_letter = cover_letter.strip()

    cover_letter_path = folder / "Cover_Letter.txt"
    cover_letter_path.write_text(cover_letter, encoding="utf-8")

    for filename in ["prompt.txt", "prompt-cover.txt", "resume-template.tex"]:
        file_path = folder / filename
        if file_path.exists():
            file_path.unlink()

    return {
        "tailored_resume": tailored_resume,
        "cover_letter": cover_letter,
        "folder": folder.name,
    }


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text()


@app.post("/scrape-and-generate")
async def scrape_and_generate(url: str = Form(...)):
    """Scrape job and auto-generate AI content."""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        loop = asyncio.get_event_loop()
        job = await loop.run_in_executor(executor, scraper_scrape_job, url)

        if not job:
            raise HTTPException(status_code=404, detail="Could not extract job data")

        result = processor.process_job(job, Path.cwd(), url)

        try:
            gen_result = _generate_ai_content(job, result["folder_path"])
            return {
                "success": True,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "description": job.get("description", ""),
                "folder": result["folder_name"],
                "resume_tex": gen_result["tailored_resume"],
                "cover_letter": gen_result["cover_letter"],
            }
        except ValueError as e:
            if "GROQ_API_KEY" in str(e):
                raise HTTPException(status_code=400, detail="GROQ_API_KEY not found. Please set it in .env file.")
            raise HTTPException(status_code=500, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-resumes")
async def list_resumes():
    """List all generated Resume.tex files."""
    resumes = []
    cwd = Path.cwd()

    for item in cwd.iterdir():
        if item.is_dir() and not item.name.startswith((".", "_", "venv", "__")):
            resume_file = item / "Resume.tex"
            if resume_file.exists():
                resumes.append(
                    {
                        "folder": item.name,
                        "path": str(resume_file),
                    }
                )

    return sorted(resumes, key=lambda x: x["folder"], reverse=True)


@app.get("/resume/{folder}")
async def get_resume(folder: str):
    """Get a specific Resume.tex content."""
    resume_path = Path.cwd() / folder / "Resume.tex"

    if not resume_path.exists():
        raise HTTPException(status_code=404, detail="Resume not found")

    content = resume_path.read_text(encoding="utf-8")
    return {"content": content, "folder": folder}


@app.get("/cover-letter/{folder}")
async def get_cover_letter(folder: str):
    """Get a specific Cover_Letter.txt content."""
    cover_path = Path.cwd() / folder / "Cover_Letter.txt"

    if not cover_path.exists():
        raise HTTPException(status_code=404, detail="Cover letter not found")

    content = cover_path.read_text(encoding="utf-8")
    return {"content": content, "folder": folder}


@app.get("/template")
async def get_template():
    """Get the master resume template content."""
    template_path = Path(__file__).parent / "templates" / "resume-template.tex"

    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    content = template_path.read_text(encoding="utf-8")
    return {"content": content}


@app.post("/template")
async def save_template(content: str = Form(...)):
    """Save the master resume template."""
    template_path = Path(__file__).parent / "templates" / "resume-template.tex"

    try:
        template_path.write_text(content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
