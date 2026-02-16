#!/usr/bin/env python3
"""CLI for job application workflow: scrape → template setup → AI generation."""

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import processor
import scraper
from exceptions import APIKeyError, CrackATSException, ValidationError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _load_json_job(json_path: str | Path) -> dict[str, Any]:
    """Load job data from JSON file (from bookmarklet).

    Args:
        json_path: Path to JSON file

    Returns:
        Job data dictionary

    Raises:
        ValidationError: If JSON is missing required fields
    """
    data: dict[str, Any] = json.loads(Path(json_path).read_text(encoding="utf-8"))
    required = ["title", "company", "description"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ValidationError(f"JSON missing fields: {', '.join(missing)}")
    return data


def _open_in_vscode(path: str | Path) -> bool:
    """Open folder in VS Code if available.

    Args:
        path: Path to open

    Returns:
        True if VS Code was opened, False otherwise
    """
    code = shutil.which("code") or shutil.which("code.cmd")
    if code:
        try:
            subprocess.Popen(
                [code, str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except OSError:
            pass
    return False


def _generate_ai_content(
    job_data: dict[str, Any],
    folder_path: str | Path,
    model: str = "llama-3.3-70b-versatile",
) -> dict[str, Path]:
    """Generate tailored resume and cover letter using Groq API.

    Args:
        job_data: Job data dict with title, company, description
        folder_path: Path to job folder containing resume-template.tex
        model: Groq model to use

    Returns:
        Dict with paths to generated files

    Raises:
        FileNotFoundError: If master resume not found
        APIKeyError: If API key is missing or invalid
    """
    try:
        import groq_client
    except ImportError as e:
        raise RuntimeError("groq_client module not found.") from e

    folder = Path(folder_path)

    master_resume_path = folder / "resume-template.tex"
    if not master_resume_path.exists():
        raise FileNotFoundError(f"Master resume not found: {master_resume_path}")

    master_resume = master_resume_path.read_text(encoding="utf-8")

    logger.info("Generating AI-tailored content...")
    logger.info("This may take 30-60 seconds...")

    logger.info("Tailoring resume to job description...")
    tailored_resume = groq_client.generate_tailored_resume(
        job_description=job_data["description"],
        master_resume=master_resume,
        model=model,
    )

    # Clean up the response (remove markdown code blocks if present)
    if tailored_resume.startswith("```latex"):
        tailored_resume = tailored_resume[8:]
    if tailored_resume.startswith("```"):
        tailored_resume = tailored_resume[3:]
    if tailored_resume.endswith("```"):
        tailored_resume = tailored_resume[:-3]
    tailored_resume = tailored_resume.strip()

    tailored_resume_path = folder / "Resume.tex"
    tailored_resume_path.write_text(tailored_resume, encoding="utf-8")
    logger.info(f"Resume.tex generated: {tailored_resume_path}")

    logger.info("Writing cover letter...")
    cover_letter = groq_client.generate_cover_letter(
        job_description=job_data["description"],
        tailored_resume=tailored_resume,
        company_name=job_data["company"],
        job_title=job_data["title"],
        model=model,
    )

    # Clean up the response
    if cover_letter.startswith("```"):
        cover_letter = cover_letter[3:]
    if cover_letter.endswith("```"):
        cover_letter = cover_letter[:-3]
    cover_letter = cover_letter.strip()

    cover_letter_path = folder / "Cover_Letter.txt"
    cover_letter_path.write_text(cover_letter, encoding="utf-8")
    logger.info(f"Cover_Letter.txt generated: {cover_letter_path}")

    return {
        "tailored_resume_path": tailored_resume_path,
        "cover_letter_path": cover_letter_path,
    }


def _cleanup_templates(folder_path: str | Path) -> list[str]:
    """Remove template files after successful generation to keep folder clean.

    Args:
        folder_path: Path to job folder

    Returns:
        List of removed filenames
    """
    folder = Path(folder_path)
    files_to_remove = ["prompt.txt", "prompt-cover.txt", "resume-template.tex"]

    removed: list[str] = []
    for filename in files_to_remove:
        file_path = folder / filename
        if file_path.exists():
            try:
                file_path.unlink()
                removed.append(filename)
                logger.debug(f"Cleaned up: {filename}")
            except OSError as e:
                logger.warning(f"Failed to remove {filename}: {e}")

    return removed


def scrape_job(args: argparse.Namespace) -> dict[str, Any]:
    """Step 1: Scrape job and create folder with templates.

    Args:
        args: Command line arguments

    Returns:
        Processing result dictionary
    """
    target = (args.url or "").strip()
    if not target:
        try:
            target = input("Job posting URL or JSON file: ").strip()
        except EOFError:
            pass

    if not target:
        logger.error("Error: URL or JSON file path required.")
        sys.exit(1)

    # JSON file (from bookmarklet) → load directly
    if target.lower().endswith(".json") and not target.lower().startswith(("http://", "https://")):
        try:
            job = _load_json_job(target)
        except Exception as e:
            logger.error(f"Error: {e}")
            sys.exit(1)
    else:
        # URL → scrape and process
        logger.info("Scraping job posting...")
        job = scraper.scrape_job(target)

    # Validate job data has meaningful content
    if not job.get("title") or not job.get("description"):
        logger.error("Error: Failed to extract job data. The job posting may be blocked or no longer available.")
        sys.exit(1)

    logger.info(f"Found: {job.get('title')} at {job.get('company')}")

    result = processor.process_job(job, Path.cwd(), target)

    logger.info(f"Created folder: {result['folder_path']}")
    logger.info("Files created:")
    logger.info(f"  • {result['folder_name']}.txt - Job description")
    logger.info(f"  • resume-template.tex - Your master resume (copy)")
    logger.info(f"  • prompt.txt - AI prompt for resume tailoring")
    logger.info(f"  • prompt-cover.txt - AI prompt for cover letter")

    # Auto-generate AI content if --generate flag is passed
    if args.generate:
        try:
            gen_result = _generate_ai_content(job, result["folder_path"], model=args.model)

            # Clean up template files if --cleanup flag is also set
            if getattr(args, "cleanup", False):
                removed = _cleanup_templates(result["folder_path"])
                if removed:
                    logger.info(f"Cleaned up {len(removed)} template files: {', '.join(removed)}")

            logger.info("=" * 60)
            logger.info("AI generation complete!")
            logger.info("=" * 60)
            logger.info(f"Resume (LaTeX): {gen_result['tailored_resume_path']}")
            logger.info("  → Copy to Overleaf to generate PDF")
            logger.info(f"Cover Letter: {gen_result['cover_letter_path']}")
            logger.info("  → Ready to use!")
            logger.info("=" * 60)

        except APIKeyError as e:
            logger.error("=" * 60)
            logger.error("GROQ_API_KEY not found!")
            logger.error("=" * 60)
            logger.error("\nTo use AI generation, add your API key to .env file:")
            logger.error("1. Get API key: https://console.groq.com/keys")
            logger.error("2. Create .env file:")
            logger.error('   echo "GROQ_API_KEY=your-key-here" > .env')
            logger.error("\nOr set environment variable:")
            logger.error('   export GROQ_API_KEY="your-key-here"')
            logger.error("\nTemplate folder created. Run generate command later:")
            logger.error(f"   python3 job_tool.py generate {result['folder_path']}")
            logger.error("=" * 60)
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            logger.error(f"\nTemplate folder created. You can retry later:")
            logger.error(f"   python3 job_tool.py generate {result['folder_path']}")
    else:
        logger.info("=" * 60)
        logger.info("Step 1 Complete: Job scraped and folder created!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Review the job description and prompts in the folder")
        logger.info("2. Run AI generation when ready:")
        logger.info(f"   python3 job_tool.py generate {result['folder_path']}")
        logger.info("\nOr generate immediately with --generate flag:")
        logger.info(f'   python3 job_tool.py scrape "{target}" --generate')
        logger.info("=" * 60)

    if _open_in_vscode(result["folder_path"]):
        logger.info("Opened folder in VS Code")

    return result


def generate_content(args: argparse.Namespace) -> None:
    """Step 2: Generate AI content for existing job folder.

    Args:
        args: Command line arguments
    """
    folder_path = Path(args.folder)

    if not folder_path.exists():
        logger.error(f"Error: Folder not found: {folder_path}")
        logger.error("\nYou need to run 'scrape' command first:")
        logger.error(f'   python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"')
        logger.error("\nOr use --generate flag to do both steps at once:")
        logger.error(f'   python3 job_tool.py scrape "URL" --generate')
        sys.exit(1)

    # Check for master resume template
    master_resume_path = folder_path / "resume-template.tex"
    if not master_resume_path.exists():
        logger.error(f"Error: Master resume not found: {master_resume_path}")
        logger.error("\nThe folder appears incomplete. Run 'scrape' command first:")
        logger.error(f'   python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"')
        sys.exit(1)

    # Find job description file
    txt_files = list(folder_path.glob("*.txt"))
    job_desc_file: Path | None = None
    for f in txt_files:
        if f.name not in ["prompt.txt", "prompt-cover.txt", "Cover_Letter.txt"]:
            job_desc_file = f
            break

    if not job_desc_file:
        logger.error(f"Error: Job description file not found in {folder_path}")
        logger.error("Expected a .txt file with job description (not prompt.txt or Cover_Letter.txt)")
        logger.error("\nRun 'scrape' command first to create a complete folder:")
        logger.error(f'   python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"')
        sys.exit(1)

    # Parse job description file
    content = job_desc_file.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Extract title and company from first few lines
    job_title = folder_path.name.replace("-", " ")
    company = "Unknown"
    description = content

    # Try to parse structured format
    for line in lines[:10]:
        if line.startswith("Title: "):
            job_title = line[7:].strip()
        elif line.startswith("Company: "):
            company = line[9:].strip()

    job_data = {"title": job_title, "company": company, "description": description}

    logger.info(f"Processing folder: {folder_path.name}")
    logger.info(f"Job: {job_title} at {company}")

    try:
        gen_result = _generate_ai_content(job_data, folder_path, model=args.model)

        # Clean up template files if --cleanup flag is set
        if getattr(args, "cleanup", False):
            removed = _cleanup_templates(folder_path)
            if removed:
                logger.info(f"Cleaned up {len(removed)} template files: {', '.join(removed)}")

        logger.info("=" * 60)
        logger.info("AI generation complete!")
        logger.info("=" * 60)
        logger.info(f"Resume (LaTeX): {gen_result['tailored_resume_path']}")
        logger.info("  → Copy to Overleaf to generate PDF")
        logger.info(f"Cover Letter: {gen_result['cover_letter_path']}")
        logger.info("  → Ready to use!")
        logger.info("\nTip: Review both files before submitting")
        logger.info("=" * 60)

        if _open_in_vscode(folder_path):
            logger.info("Opened folder in VS Code")

    except APIKeyError as e:
        logger.error("=" * 60)
        logger.error("GROQ_API_KEY not found!")
        logger.error("=" * 60)
        logger.error("\nTo use AI generation, add your API key to .env file:")
        logger.error("1. Get API key: https://console.groq.com/keys")
        logger.error("2. Create .env file:")
        logger.error('   echo "GROQ_API_KEY=your-key-here" > .env')
        logger.error("\nOr set environment variable:")
        logger.error('   export GROQ_API_KEY="your-key-here"')
        logger.error("=" * 60)
        sys.exit(1)
    except Exception as e:
        logger.error(f"AI generation failed: {e}")
        sys.exit(1)


def test_api(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Test Groq API key.

    Args:
        args: Command line arguments (unused)
    """
    logger.info("Testing Groq API key...")

    try:
        import groq_client

        success = groq_client.test_api_key()
        if success:
            logger.info("API key is working correctly!")
            logger.info("You can now generate resumes and cover letters.")
        else:
            logger.error("API test failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"API test failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Job application workflow: scrape → setup → AI generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WORKFLOW:
  Step 1 - Scrape job posting:
      python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"

  Step 2 - Generate AI content:
      python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/

TESTING:
  Test if your API key works:
      python3 job_tool.py test

QUICK START:
  # Scrape + generate in one command
  python3 job_tool.py scrape "https://linkedin.com/jobs/view/123" --generate

  # Scrape + generate + cleanup templates
  python3 job_tool.py scrape "https://linkedin.com/jobs/view/123" --generate --cleanup

  # Or do it in two steps (review first, then generate)
  python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"
  # Review the job description, then...
  python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/

  # Generate + cleanup template files
  python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/ --cleanup

SETUP:
  1. Edit templates/resume-template.tex with your info (one-time)
  2. Set GROQ_API_KEY in .env file:
       echo "GROQ_API_KEY=your-key-here" > .env
  3. Test: python3 job_tool.py test
  4. Start scraping and generating!
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape job posting and create template folder (Step 1)")
    scrape_parser.add_argument("url", nargs="?", help="Job posting URL or JSON file path")
    scrape_parser.add_argument(
        "-g", "--generate", action="store_true", help="Also generate AI content immediately (skip Step 2)"
    )
    scrape_parser.add_argument(
        "--cleanup", action="store_true", help="Remove template files after generation (use with --generate)"
    )
    scrape_parser.add_argument(
        "--model", default="llama-3.3-70b-versatile", help="Groq model to use (default: llama-3.3-70b-versatile)"
    )
    scrape_parser.set_defaults(func=scrape_job)

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate AI-tailored resume and cover letter for existing folder (Step 2)"
    )
    gen_parser.add_argument("folder", help="Path to job folder created by scrape command")
    gen_parser.add_argument(
        "--model", default="llama-3.3-70b-versatile", help="Groq model to use (default: llama-3.3-70b-versatile)"
    )
    gen_parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove template files after generation (prompt.txt, prompt-cover.txt, resume-template.tex)",
    )
    gen_parser.set_defaults(func=generate_content)

    # Test command
    test_parser = subparsers.add_parser("test", help="Test if Groq API key is working")
    test_parser.set_defaults(func=test_api)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
