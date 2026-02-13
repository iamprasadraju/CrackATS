#!/usr/bin/env python3
"""CLI for job application workflow: scrape → template setup → AI generation."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import processor
import scraper


def _load_json_job(json_path):
    """Load job data from JSON file (from bookmarklet)."""
    data = json.loads(Path(json_path).read_text())
    required = ["title", "company", "description"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ValueError(f"JSON missing fields: {', '.join(missing)}")
    return data


def _open_in_vscode(path):
    """Open folder in VS Code if available."""
    code = shutil.which("code") or shutil.which("code.cmd")
    if code:
        try:
            subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            pass
    return False


def _generate_ai_content(job_data, folder_path, model="llama-3.3-70b-versatile"):
    """Generate tailored resume and cover letter using Groq API.

    Args:
        job_data: Job data dict with title, company, description
        folder_path: Path to job folder containing resume-template.tex
        model: Groq model to use

    Returns:
        Dict with paths to generated files
    """
    try:
        import groq_client
    except ImportError:
        raise RuntimeError("groq_client module not found.")

    folder = Path(folder_path)

    # Read master resume template (copied to folder)
    master_resume_path = folder / "resume-template.tex"
    if not master_resume_path.exists():
        raise FileNotFoundError(f"Master resume not found: {master_resume_path}")

    master_resume = master_resume_path.read_text(encoding="utf-8")

    print("\n[AI] Generating AI-tailored content...")
    print("   This may take 30-60 seconds...")

    print("\n   [EDIT] Tailoring resume to job description...")
    tailored_resume = groq_client.generate_tailored_resume(
        job_description=job_data["description"], master_resume=master_resume, model=model
    )

    # Clean up the response (remove markdown code blocks if present)
    if tailored_resume.startswith("```latex"):
        tailored_resume = tailored_resume[8:]
    if tailored_resume.startswith("```"):
        tailored_resume = tailored_resume[3:]
    if tailored_resume.endswith("```"):
        tailored_resume = tailored_resume[:-3]
    tailored_resume = tailored_resume.strip()

    # Save tailored resume
    tailored_resume_path = folder / "Resume.tex"
    tailored_resume_path.write_text(tailored_resume, encoding="utf-8")
    print(f"   [DONE] Resume.tex generated")

    print("\n   [FILE] Writing cover letter...")
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

    # Save cover letter
    cover_letter_path = folder / "Cover_Letter.txt"
    cover_letter_path.write_text(cover_letter, encoding="utf-8")
    print(f"   [DONE] Cover_Letter.txt generated")

    return {"tailored_resume_path": tailored_resume_path, "cover_letter_path": cover_letter_path}


def _cleanup_templates(folder_path):
    """Remove template files after successful generation to keep folder clean.

    Args:
        folder_path: Path to job folder
    """
    folder = Path(folder_path)
    files_to_remove = ["prompt.txt", "prompt-cover.txt", "resume-template.tex"]

    removed = []
    for filename in files_to_remove:
        file_path = folder / filename
        if file_path.exists():
            try:
                file_path.unlink()
                removed.append(filename)
            except OSError:
                pass  # Ignore errors if file can't be deleted

    return removed


def scrape_job(args):
    """Step 1: Scrape job and create folder with templates."""
    target = (args.url or "").strip()
    if not target:
        try:
            target = input("Job posting URL or JSON file: ").strip()
        except EOFError:
            pass

    if not target:
        print("Error: URL or JSON file path required.")
        sys.exit(1)

    # JSON file (from bookmarklet) → load directly
    if target.lower().endswith(".json") and not target.lower().startswith(("http://", "https://")):
        try:
            job = _load_json_job(target)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # URL → scrape and process
        print(f"\n[SEARCH] Scraping job posting...")
        job = scraper.scrape_job(target)

    # Validate job data has meaningful content
    if not job.get("title") or not job.get("description"):
        print("Error: Failed to extract job data. The job posting may be blocked or no longer available.")
        sys.exit(1)

    print(f"\n[INFO] Found: {job.get('title')} at {job.get('company')}")

    result = processor.process_job(job, Path.cwd(), target)

    print(f"\n[FOLDER] Created folder: {result['folder_path']}")
    print(f"\n[FILE] Files created:")
    print(f"   • {result['folder_name']}.txt - Job description")
    print(f"   • resume-template.tex - Your master resume (copy)")
    print(f"   • prompt.txt - AI prompt for resume tailoring")
    print(f"   • prompt-cover.txt - AI prompt for cover letter")

    # Auto-generate AI content if --generate flag is passed
    if args.generate:
        try:
            gen_result = _generate_ai_content(job, result["folder_path"], model=args.model)

            # Clean up template files if --cleanup flag is also set
            if getattr(args, "cleanup", False):
                removed = _cleanup_templates(result["folder_path"])
                if removed:
                    print(f"\n[CLEAN] Cleaned up {len(removed)} template files: {', '.join(removed)}")

            print("\n" + "=" * 60)
            print("[COMPLETE] AI generation complete!")
            print("=" * 60)
            print(f"\n[FILE] Resume (LaTeX): {gen_result['tailored_resume_path']}")
            print("   → Copy to Overleaf to generate PDF")
            print(f"\n[EDIT] Cover Letter: {gen_result['cover_letter_path']}")
            print("   → Ready to use!")
            print("=" * 60)

        except ValueError as e:
            if "GROQ_API_KEY" in str(e):
                print("\n" + "=" * 60)
                print("[WARNING]  GROQ_API_KEY not found!")
                print("=" * 60)
                print("\nTo use AI generation, add your API key to .env file:")
                print("1. Get API key: https://console.groq.com/keys")
                print("2. Create .env file:")
                print('   echo "GROQ_API_KEY=your-key-here" > .env')
                print("\nOr set environment variable:")
                print('   export GROQ_API_KEY="your-key-here"')
                print("\nTemplate folder created. Run generate command later:")
                print(f"   python3 job_tool.py generate {result['folder_path']}")
                print("=" * 60)
            else:
                print(f"\n[ERROR] Error: {e}")
        except Exception as e:
            print(f"\n[WARNING]  AI generation failed: {e}")
            print(f"\nTemplate folder created. You can retry later:")
            print(f"   python3 job_tool.py generate {result['folder_path']}")
    else:
        print("\n" + "=" * 60)
        print("[DONE] Step 1 Complete: Job scraped and folder created!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the job description and prompts in the folder")
        print("2. Run AI generation when ready:")
        print(f"   python3 job_tool.py generate {result['folder_path']}")
        print("\nOr generate immediately with --generate flag:")
        print(f'   python3 job_tool.py scrape "{target}" --generate')
        print("=" * 60)

    if _open_in_vscode(result["folder_path"]):
        print("\n[OPEN] Opened folder in VS Code")

    return result


def generate_content(args):
    """Step 2: Generate AI content for existing job folder."""
    folder_path = Path(args.folder)

    if not folder_path.exists():
        print(f"[ERROR] Error: Folder not found: {folder_path}")
        print("\n[TIP] You need to run 'scrape' command first:")
        print(f'   python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"')
        print("\nOr use --generate flag to do both steps at once:")
        print(f'   python3 job_tool.py scrape "URL" --generate')
        sys.exit(1)

    # Check for master resume template
    master_resume_path = folder_path / "resume-template.tex"
    if not master_resume_path.exists():
        print(f"[ERROR] Error: Master resume not found: {master_resume_path}")
        print("\n[TIP] The folder appears incomplete. Run 'scrape' command first:")
        print(f'   python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"')
        sys.exit(1)

    # Find job description file
    txt_files = list(folder_path.glob("*.txt"))
    job_desc_file = None
    for f in txt_files:
        if f.name not in ["prompt.txt", "prompt-cover.txt", "Cover_Letter.txt"]:
            job_desc_file = f
            break

    if not job_desc_file:
        print(f"[ERROR] Error: Job description file not found in {folder_path}")
        print("Expected a .txt file with job description (not prompt.txt or Cover_Letter.txt)")
        print("\n[TIP] Run 'scrape' command first to create a complete folder:")
        print(f'   python3 job_tool.py scrape "https://linkedin.com/jobs/view/123"')
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

    print(f"\n[FOLDER] Processing folder: {folder_path.name}")
    print(f"[FILE] Job: {job_title} at {company}")

    try:
        gen_result = _generate_ai_content(job_data, folder_path, model=args.model)

        # Clean up template files if --cleanup flag is set
        if getattr(args, "cleanup", False):
            removed = _cleanup_templates(folder_path)
            if removed:
                print(f"\n[CLEAN] Cleaned up {len(removed)} template files: {', '.join(removed)}")

        print("\n" + "=" * 60)
        print("[COMPLETE] AI generation complete!")
        print("=" * 60)
        print(f"\n[FILE] Resume (LaTeX): {gen_result['tailored_resume_path']}")
        print("   → Copy to Overleaf to generate PDF")
        print(f"\n[EDIT] Cover Letter: {gen_result['cover_letter_path']}")
        print("   → Ready to use!")
        print("\n[TIP] Tip: Review both files before submitting")
        print("=" * 60)

        if _open_in_vscode(folder_path):
            print("\n[OPEN] Opened folder in VS Code")

    except ValueError as e:
        if "GROQ_API_KEY" in str(e):
            print("\n" + "=" * 60)
            print("[WARNING]  GROQ_API_KEY not found!")
            print("=" * 60)
            print("\nTo use AI generation, add your API key to .env file:")
            print("1. Get API key: https://console.groq.com/keys")
            print("2. Create .env file:")
            print('   echo "GROQ_API_KEY=your-key-here" > .env')
            print("\nOr set environment variable:")
            print('   export GROQ_API_KEY="your-key-here"')
            print("=" * 60)
        else:
            print(f"\n[ERROR] Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] AI generation failed: {e}")
        sys.exit(1)


def test_api(args):
    """Test Groq API key."""
    print("\n[KEY] Testing Groq API key...\n")

    try:
        import groq_client

        success = groq_client.test_api_key()
        if success:
            print("\n[DONE] API key is working correctly!")
            print("\nYou can now generate resumes and cover letters.")
        else:
            print("\n[ERROR] API test failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] API test failed: {e}")
        sys.exit(1)


def main():
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
