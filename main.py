"""FastAPI web interface for job scraper."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import processor
from database import Application, ApplicationDB
from scraper import scrape_job as scraper_scrape_job

app = FastAPI(title="CrackATS")
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

            # Auto-create application entry
            from datetime import datetime
            import json

            app = Application(
                company=job.get("company", ""),
                title=job.get("title", ""),
                url=url,
                status="applied",
                date_applied=datetime.now().strftime("%Y-%m-%d"),
                resume_path=str(Path(result["folder_path"]) / "Resume.tex"),
                cover_letter_path=str(Path(result["folder_path"]) / "Cover_Letter.txt"),
                tags=json.dumps(["ai-generated"]),
            )
            app_id = ApplicationDB.create(app)

            return {
                "success": True,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "description": job.get("description", ""),
                "folder": result["folder_name"],
                "resume_tex": gen_result["tailored_resume"],
                "cover_letter": gen_result["cover_letter"],
                "application_id": app_id,
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


@app.post("/api/save-document")
async def save_document(content: str = Form(...), path: str = Form(...)):
    """Save edited resume or cover letter document."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Security: Ensure path is within current working directory
        cwd = Path.cwd()
        try:
            file_path.relative_to(cwd)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid file path")

        file_path.write_text(content, encoding="utf-8")
        return {"success": True, "message": "Document saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


# ========== Job Application Tracking Endpoints ==========


def cleanup_orphaned_applications():
    """Remove database entries for applications whose folders no longer exist."""
    applications = ApplicationDB.get_all()
    deleted_count = 0

    for app in applications:
        # Check if the resume file exists
        resume_path = app.get("resume_path")
        if resume_path:
            if not Path(resume_path).exists():
                # Resume file doesn't exist, delete this application
                ApplicationDB.delete(app["id"])
                deleted_count += 1
                continue

        # Also check cover letter if no resume path
        cover_path = app.get("cover_letter_path")
        if cover_path and not Path(cover_path).exists():
            ApplicationDB.delete(app["id"])
            deleted_count += 1

    return deleted_count


@app.get("/api/applications")
async def get_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    cleanup: bool = Query(True, description="Remove orphaned entries"),
):
    """Get all job applications, optionally filtered by status."""
    if status and status not in Application.STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(Application.STATUSES)}"
        )

    # Clean up orphaned entries by default
    if cleanup:
        cleanup_orphaned_applications()

    applications = ApplicationDB.get_all(status=status)
    return applications


@app.post("/api/applications/cleanup")
async def cleanup_applications():
    """Manually trigger cleanup of orphaned applications."""
    deleted_count = cleanup_orphaned_applications()
    return {"message": f"Cleaned up {deleted_count} orphaned applications", "deleted_count": deleted_count}


@app.get("/api/applications/{app_id}")
async def get_application(app_id: int):
    """Get a specific application by ID."""
    app = ApplicationDB.get_by_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app.to_dict()


@app.post("/api/applications")
async def create_application(
    company: str = Form(...),
    title: str = Form(...),
    url: str = Form(""),
    status: str = Form("saved"),
    notes: str = Form(""),
    date_applied: str = Form(""),
    salary: str = Form(""),
    location: str = Form(""),
    tags: str = Form("[]"),
):
    """Create a new job application."""
    if status not in Application.STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(Application.STATUSES)}"
        )

    import json

    app = Application(
        company=company,
        title=title,
        url=url,
        status=status,
        notes=notes,
        date_applied=date_applied if date_applied else None,
        salary=salary,
        location=location,
        tags=json.loads(tags) if tags else [],
    )

    app_id = ApplicationDB.create(app)
    return {"id": app_id, "message": "Application created successfully"}


@app.put("/api/applications/{app_id}")
async def update_application(
    app_id: int,
    company: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    date_applied: Optional[str] = Form(None),
    salary: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
):
    """Update an existing application."""
    existing = ApplicationDB.get_by_id(app_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")

    if status and status not in Application.STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(Application.STATUSES)}"
        )

    import json

    updates = {}
    if company is not None:
        updates["company"] = company
    if title is not None:
        updates["title"] = title
    if url is not None:
        updates["url"] = url
    if status is not None:
        updates["status"] = status
    if notes is not None:
        updates["notes"] = notes
    if date_applied is not None:
        updates["date_applied"] = date_applied if date_applied else None
    if salary is not None:
        updates["salary"] = salary
    if location is not None:
        updates["location"] = location
    if tags is not None:
        updates["tags"] = json.loads(tags) if tags else []

    ApplicationDB.update(app_id, **updates)
    return {"message": "Application updated successfully"}


@app.delete("/api/applications/{app_id}")
async def delete_application(app_id: int):
    """Delete an application."""
    existing = ApplicationDB.get_by_id(app_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")

    ApplicationDB.delete(app_id)
    return {"message": "Application deleted successfully"}


@app.get("/api/applications/stats/overview")
async def get_application_stats():
    """Get application statistics."""
    stats = ApplicationDB.get_stats()
    total = sum(stats.values())
    return {
        "total": total,
        "by_status": stats,
        "response_rate": round(
            (stats.get("phone_screen", 0) + stats.get("interview", 0) + stats.get("offer", 0)) / total * 100, 1
        )
        if total > 0
        else 0,
    }


@app.post("/api/applications/{app_id}/status")
async def update_application_status(app_id: int, status: str = Form(...)):
    """Quick endpoint to update just the status."""
    if status not in Application.STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(Application.STATUSES)}"
        )

    existing = ApplicationDB.get_by_id(app_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application not found")

    ApplicationDB.update(app_id, status=status)
    return {"message": f"Status updated to {status}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
