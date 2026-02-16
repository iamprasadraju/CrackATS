"""Process job data into folder structure with templates."""

import logging
import os
import re
from pathlib import Path
from typing import Any

import file_ops
import prompt_creator
from exceptions import ValidationError

logger = logging.getLogger(__name__)

_TEMPLATES = Path(__file__).parent / "templates"

_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}

_NOISE = {
    "webkit",
    "inline",
    "block",
    "flex",
    "display",
    "margin",
    "padding",
    "color",
    "inherit",
    "auto",
    "rem",
    "em",
    "px",
}


def _words(text: str | None) -> list[str]:
    """Extract words from text."""
    return [w for w in re.sub(r"[^A-Za-z0-9]+", " ", text or "").split() if w]


def _is_noise(w: str) -> bool:
    """Check if a word is noise/CSS-related."""
    lo = w.lower()
    if lo in ("true", "false") or lo.startswith("css") or lo in _NOISE:
        return True
    if len(w) > 24:
        return True
    if len(w) > 4 and any(c.isdigit() for c in w) and any(c.isalpha() for c in w):
        return True
    return False


def _abbrev(title: str, max_len: int = 4) -> str:
    """Abbreviate title to short form."""
    return "-".join(w[:max_len] if len(w) > max_len else w for w in _words(title))


def _company_slug(company: str) -> str:
    """Create URL-safe slug from company name."""
    words = _words(company)
    result: list[str] = []
    for w in words:
        if _is_noise(w):
            if result:
                break
            continue
        result.append(w)
        if len(result) >= 6:
            break
    return "-".join(result or words[:4])


def _trim(slug: str, max_len: int = 80) -> str:
    """Trim slug to maximum length."""
    slug = re.sub(r"-+", "-", slug).strip("-")
    if len(slug) <= max_len:
        return slug
    parts, acc = [], ""
    for p in slug.split("-"):
        test = f"{acc}-{p}" if acc else p
        if len(test) > max_len:
            break
        acc = test
    return acc.strip("-") or slug[:max_len].rstrip("-")


def _safe_slug(slug: str) -> str:
    """Make slug safe for filesystem."""
    slug = slug.strip(" .")
    if not slug:
        return "Job-Posting"
    if os.name == "nt" and slug.split(".")[0].upper() in _WIN_RESERVED:
        slug = f"{slug}-job"
    return slug or "Job-Posting"


def make_folder_name(title: str, company: str) -> str:
    """Create safe folder name from job title and company.

    Args:
        title: Job title
        company: Company name

    Returns:
        Safe folder name
    """
    t, c = _abbrev(title), _company_slug(company)
    slug = f"{t}-{c}" if t and c else t or c or "Job-Posting"
    return _trim(_safe_slug(slug))


def process_job(
    job_data: dict[str, Any],
    base_dir: str | Path,
    source_url: str | None = None,
) -> dict[str, Any]:
    """Process job data and create folder with templates.

    Args:
        job_data: Dictionary with job information (title, company, description)
        base_dir: Base directory for creating job folder
        source_url: Optional source URL for the job posting

    Returns:
        Dictionary with paths to created files

    Raises:
        ValidationError: If job data is invalid
    """
    title = (job_data.get("title") or "").strip()
    company = (job_data.get("company") or "").strip()
    desc = (job_data.get("description") or "").strip() or "Description not found."

    if not title or not company:
        raise ValidationError("Job title or company missing.")

    folder_name = make_folder_name(title, company)
    folder = file_ops.ensure_job_folder(base_dir, folder_name)

    logger.info(f"Processing job: {title} at {company} -> {folder_name}")

    return {
        "folder_name": folder_name,
        "folder_path": folder,
        "file_path": file_ops.write_description(folder, f"{folder_name}.txt", desc, source_url=source_url),
        "prompt_path": file_ops.write_prompt_file(folder, "prompt.txt", prompt_creator.get_main_prompt(), desc),
        "cover_prompt_path": file_ops.write_prompt_file(
            folder, "prompt-cover.txt", prompt_creator.get_cover_prompt(), desc
        ),
        "resume_template_path": file_ops.copy_template(_TEMPLATES / "resume-template.tex", folder),
    }
