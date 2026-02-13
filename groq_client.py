"""Groq API client for resume and cover letter generation."""

import json
import os
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _load_env_file():
    """Load environment variables from .env file if present."""
    # Check current working directory first, then script directory
    possible_paths = [Path.cwd() / ".env", Path(__file__).parent / ".env"]

    for env_file in possible_paths:
        if env_file.exists():
            content = env_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Match KEY=value format
                    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
                    if match:
                        key, value = match.groups()
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
            return  # Stop after first .env found


def get_api_key():
    """Get Groq API key from environment variable or .env file."""
    # First try to load from .env file
    _load_env_file()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found.\n\n"
            "Please set it using one of these methods:\n"
            "1. Create a .env file with: GROQ_API_KEY=your-key-here\n"
            "2. Or set environment variable: export GROQ_API_KEY='your-key'"
        )
    return api_key


def _create_ssl_context():
    """Create SSL context, handling macOS certificate issues."""
    try:
        # Try to use certifi if available (handles macOS certificates properly)
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        # Fall back to default context
        return ssl.create_default_context()


def call_groq_api(messages, model=DEFAULT_MODEL, temperature=0.7, max_tokens=4000):
    """Call Groq API with given messages.

    Args:
        messages: List of dicts with 'role' and 'content' keys
        model: Model to use
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate

    Returns:
        Generated text content
    """
    api_key = get_api_key()

    data = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

    req = urllib.request.Request(
        GROQ_API_URL,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TurboApply/1.0",
        },
        method="POST",
    )

    ssl_context = _create_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=120, context=ssl_context) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")

        # Provide helpful error messages for common issues
        if e.code == 401:
            raise RuntimeError(
                f"Groq API Error 401: Invalid API key\n\n"
                f"Your API key is invalid or expired.\n"
                f"1. Check your key at: https://console.groq.com/keys\n"
                f"2. Generate a new key if needed\n"
                f"3. Update: export GROQ_API_KEY='your-new-key'\n\n"
                f"Response: {error_body}"
            ) from e
        elif e.code == 403:
            raise RuntimeError(
                f"Groq API Error 403: Access Denied\n\n"
                f"Possible causes:\n"
                f"1. API key revoked or expired\n"
                f"2. Account not verified (check email)\n"
                f"3. Rate limit exceeded\n"
                f"4. IP address blocked\n\n"
                f"Solutions:\n"
                f"• Check account status: https://console.groq.com\n"
                f"• Generate new API key\n"
                f"• Check if you received verification email\n\n"
                f"Response: {error_body}"
            ) from e
        elif e.code == 429:
            raise RuntimeError(
                f"Groq API Error 429: Rate Limit Exceeded\n\n"
                f"You've made too many requests. Please wait a minute and try again.\n\n"
                f"Response: {error_body}"
            ) from e
        else:
            raise RuntimeError(f"Groq API error: {e.code} - {error_body}") from e
    except ssl.SSLError as e:
        raise RuntimeError(
            f"SSL Certificate error: {e}\n\n"
            "On macOS, run: /Applications/Python 3.x/Install Certificates.command\n"
            "Or install certifi: pip install certifi\n\n"
            "Alternatively, set environment variable to bypass SSL (not recommended):\n"
            "export PYTHONHTTPSVERIFY=0"
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to call Groq API: {e}") from e


def generate_tailored_resume(job_description, master_resume, model=DEFAULT_MODEL):
    """Generate tailored resume based on job description.

    Args:
        job_description: Job posting description text
        master_resume: Master resume LaTeX content
        model: Model to use

    Returns:
        Tailored resume LaTeX content
    """
    prompt = f"""You are an expert resume writer specializing in tailoring resumes for specific job descriptions.

MASTER RESUME (LaTeX format):
```latex
{master_resume}
```

JOB DESCRIPTION:
{job_description}

TASK:
Tailor the master resume to align with the job description. Follow these guidelines:
1. Revise bullet points and descriptions to highlight relevant experience matching the job requirements
2. Incorporate keywords from the job description naturally (don't copy verbatim)
3. Remove or minimize content that's not relevant to this specific role
4. Keep the same LaTeX structure and formatting - only modify the content
5. Do not change dates, job titles, company names, or degree information
6. Keep "Relevant Coursework" to maximum two lines
7. Ensure all content remains factual and accurate - do not invent experience

Return ONLY the complete LaTeX resume code, ready to compile."""

    messages = [
        {
            "role": "system",
            "content": "You are an expert resume writer. Return only valid LaTeX code without any explanations or markdown formatting.",
        },
        {"role": "user", "content": prompt},
    ]

    return call_groq_api(messages, model=model, temperature=0.7, max_tokens=4000)


def generate_cover_letter(job_description, tailored_resume, company_name, job_title, model=DEFAULT_MODEL):
    """Generate cover letter based on job description and tailored resume.

    Args:
        job_description: Job posting description text
        tailored_resume: Tailored resume content (for context)
        company_name: Company name
        job_title: Job title
        model: Model to use

    Returns:
        Cover letter text
    """
    prompt = f"""You are an expert cover letter writer.

JOB TITLE: {job_title}
COMPANY: {company_name}

JOB DESCRIPTION:
{job_description}

TAILORED RESUME (for context):
```
{tailored_resume[:2000]}
```

TASK:
Write a compelling cover letter following this exact structure:

**Intro:** "Dear Hiring Manager,"

**First paragraph (2 sentences):** 
- Describe who the applicant is (positions or experiences related to the job, don't mention university)
- What makes them personable (what they like or believe in)
- What they want (learning or working on specific topics)

**Second paragraph (3 sentences):**
- 3 skills that matter for the position
- For each skill, explain how they use it, give an example, and explain why it was useful
- Do not enumerate skills (no "1. 2. 3.")

**Third paragraph (2 sentences):**
- Pick 2 aspects of the company relevant to the applicant
- Explain why the applicant would be interested to work at this company
- Do not enumerate aspects

**Last paragraph (use this exact format):**
"I am confident that my experience aligns with {company_name}'s needs and hope to further discuss how I can contribute to your team's success.

Thank you,
[Full Name]"

GUIDELINES:
- Do not use sentence structures with '—' (em dash)
- Keep the tone professional but personable
- Be specific about skills and company aspects
- Make it sound human and authentic, not generic

Return ONLY the cover letter text, no explanations or formatting."""

    messages = [
        {
            "role": "system",
            "content": "You are an expert cover letter writer. Return only the cover letter text without any explanations or markdown formatting.",
        },
        {"role": "user", "content": prompt},
    ]

    return call_groq_api(messages, model=model, temperature=0.8, max_tokens=2000)


def extract_resume_sections(latex_content):
    """Extract key sections from LaTeX resume for cover letter context.

    Args:
        latex_content: LaTeX resume content

    Returns:
        Dict with extracted sections
    """
    sections = {"skills": "", "experience": "", "education": ""}

    # Simple extraction - can be improved with proper LaTeX parsing
    lines = latex_content.split("\n")
    current_section = None
    section_buffer = []

    for line in lines:
        line = line.strip()
        if "\\section{" in line.lower() or "\\section*{" in line.lower():
            if current_section and section_buffer:
                sections[current_section] = "\n".join(section_buffer)
            section_buffer = []

            lower_line = line.lower()
            if "skill" in lower_line:
                current_section = "skills"
            elif "experience" in lower_line or "work" in lower_line:
                current_section = "experience"
            elif "education" in lower_line:
                current_section = "education"
            else:
                current_section = None
        elif current_section:
            section_buffer.append(line)

    if current_section and section_buffer:
        sections[current_section] = "\n".join(section_buffer)

    return sections


def test_api_key():
    """Test if the API key is valid by making a simple request."""
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'API key is working!' if you receive this message."},
        ]
        result = call_groq_api(messages, model="llama-3.1-8b-instant", max_tokens=50)
        print(f"[DONE] API Key Test: {result}")
        return True
    except Exception as e:
        print(f"[ERROR] API Key Test Failed: {e}")
        return False
