# Crack ATS - AI-Powered Resume & Cover Letter Generator

**Get more interviews by generating tailored resumes and cover letters for each job using AI.**

This tool scrapes job postings and automatically generates customized resumes and cover letters that match each job description. No more generic applications - let AI tailor your resume with the right keywords and compelling cover letters.

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Setup](#setup)
- [Quick Start Guide](#quick-start-guide)
- [Detailed Usage](#detailed-usage)
  - [Step 1: Scrape Job Postings](#step-1-scrape-job-postings)
  - [Step 2: Generate AI Content](#step-2-generate-ai-content)
  - [Step 3: Create PDF](#step-3-create-pdf)
- [Commands Reference](#commands-reference)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

- **Automatic Job Scraping** - Extract job descriptions from LinkedIn and other job boards
- **AI-Powered Tailoring** - Uses Groq AI to customize your resume for each job
- **Cover Letter Generation** - Creates compelling, personalized cover letters
- **LaTeX Resume Output** - Generates professional PDF-ready resumes
- **Two-Step Workflow** - Review before generating, or do it all in one command
- **Privacy Focused** - All processing happens locally, only job data sent to AI
- **ATS Optimized** - AI includes relevant keywords to pass Applicant Tracking Systems

---

## How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Job Posting   │────▶│  AI Processing   │────▶│  Tailored       │
│   (LinkedIn)    │     │  (Groq API)      │     │  Application    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
  Scrape job info        Analyze job + resume      Generate:
  - Title                - Match keywords          - Custom resume
  - Company              - Highlight skills        - Cover letter
  - Description          - Reorder experience
```

The AI analyzes your master resume alongside the job description to create tailored documents that highlight your most relevant experience and skills.

---

## Prerequisites

- **Python 3.8+** - Check with `python3 --version`
- **Groq API Key** - Get free at [console.groq.com](https://console.groq.com/keys)
- **Git** - For cloning the repository
- **Text Editor** - VS Code, Vim, or any editor for customizing your resume
- **Overleaf Account** (optional) - For generating PDFs without installing LaTeX

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/crack-ats.git
cd crack-ats
```

### 2. Install Dependencies

The tool uses Python's standard library by default. For enhanced scraping:

```bash
# Optional but recommended for better LinkedIn scraping
pip install playwright
playwright install chromium
```

### 3. Set Up API Key

Create a `.env` file in the project root:

```bash
# Option 1: Create .env file
echo "GROQ_API_KEY=your-api-key-here" > .env

# Option 2: Set environment variable
export GROQ_API_KEY="your-api-key-here"
```

**To get your API key:**
1. Go to [console.groq.com/keys](https://console.groq.com/keys)
2. Sign up or log in
3. Click "Create API Key"
4. Copy the key and paste it above

### 4. Test Your Setup

```bash
python3 job_tool.py test
```

You should see: `[DONE] API key is working correctly!`

---

## Data Storage

Your job application data is stored separately from the application code:

**Database Location:**
- **Windows**: `%APPDATA%/CrackATS/applications.db`
- **macOS**: `~/Library/Application Support/CrackATS/applications.db`
- **Linux**: `~/.local/share/CrackATS/applications.db`

**Automatic Migration**: If you have an existing database from a previous version in the project folder, it will be automatically migrated to the new location on first run.

**Backups**: The application automatically creates backups before any database changes. Backups are stored in the `backups/` subdirectory of your user data folder.

**To check your database location:** Visit `http://localhost:8000/api/database/info` while the server is running.

---

## Setup

### Configure Your Master Resume

The master resume is your source of truth. The AI will use it as a base and tailor it for each job.

```bash
# Open the template
nano templates/resume-template.tex
# or
code templates/resume-template.tex
```

**Replace all `[PLACEHOLDER]` text with your actual information:**

#### Personal Information
```latex
{\LARGE [YOUR FULL NAME]}\\
[YOUR LOCATION] \textbullet\ \href{mailto:your.email@example.com}{your.email@example.com}
```

#### Professional Summary
```latex
\section*{Summary}
[2-3 sentences about your experience, skills, and career goals]
```

**Tips for best results:**
- Include specific metrics (e.g., "Increased performance by 40%")
- List all relevant technologies you've worked with
- Keep descriptions concise but detailed
- Include quantifiable achievements
- Add both technical and soft skills

#### Experience Section
```latex
\section*{Experience}
\textbf{[JOB TITLE]} \hfill [START DATE] -- [END DATE]\\
[Company Name], [Location]
\begin{itemize}[leftmargin=*,nosep]
    \item [Achievement with metrics]
    \item [Another achievement]
\end{itemize}
```

#### Projects Section
```latex
\section*{Projects}
\textbf{[PROJECT NAME]} \hfill [TECHNOLOGIES] \textbullet\ \href{https://github.com/...}{GitHub}
\begin{itemize}[leftmargin=*,nosep]
    \item [What problem it solves]
    \item [Technologies used and results]
\end{itemize}
```

**Example filled resume:**
```latex
{\LARGE John Smith}\\
San Francisco, CA \textbullet\ \href{mailto:john@example.com}{john@example.com}

\section*{Summary}
Full-stack developer with 5 years of experience building scalable web applications.
Specialized in Python, React, and cloud infrastructure. Passionate about clean code
and system design.

\section*{Experience}
\textbf{Senior Software Engineer} \hfill Jan 2022 -- Present\\
TechCorp Inc., San Francisco, CA
\begin{itemize}[leftmargin=*,nosep]
    \item Led migration to microservices architecture serving 1M+ daily users
    \item Reduced API response time by 45\% through query optimization
    \item Mentored 3 junior developers and improved team velocity by 25\%
\end{itemize}
```

---

## Quick Start Guide

### Method 1: Two-Step Workflow (Recommended for First-Time Users)

**Step 1: Scrape the job posting**
```bash
python3 job_tool.py scrape "https://linkedin.com/jobs/view/1234567890"
```

Output:
```
[SEARCH] Scraping job posting...
[INFO] Found: AI Software Engineer at Thomson Reuters
[FOLDER] Created folder: AI-Soft-Engi-Thomson-Reuters
[FILE] Files created:
   • AI-Soft-Engi-Thomson-Reuters.txt - Job description
   • resume-template.tex - Your master resume (copy)
   • prompt.txt - AI prompt for resume tailoring
   • prompt-cover.txt - AI prompt for cover letter

============================================================
[DONE] Step 1 Complete: Job scraped and folder created!
============================================================
```

**Step 2: Generate AI content**
```bash
python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/
```

Output:
```
[FOLDER] Processing folder: AI-Soft-Engi-Thomson-Reuters
[FILE] Job: AI Software Engineer at Thomson Reuters

[AI] Generating AI-tailored content...
   This may take 30-60 seconds...

   [EDIT] Tailoring resume to job description...
   [DONE] Resume.tex generated

   [FILE] Writing cover letter...
   [DONE] Cover_Letter.txt generated

============================================================
[COMPLETE] AI generation complete!
============================================================

[FILE] Resume (LaTeX): AI-Soft-Engi-Thomson-Reuters/Resume.tex
   -> Copy to Overleaf to generate PDF

[EDIT] Cover Letter: AI-Soft-Engi-Thomson-Reuters/Cover_Letter.txt
   -> Ready to use!
```

**Step 3: Generate PDF**
1. Go to [overleaf.com](https://www.overleaf.com)
2. Click "New Project" → "Upload Project"
3. Upload `Resume.tex` from the job folder
4. Click "Recompile" to generate PDF
5. Download and use for your application

### Method 2: One-Command Workflow (Fast)

Skip review and generate everything at once:
```bash
python3 job_tool.py scrape "https://linkedin.com/jobs/view/123" --generate
```

With cleanup (removes temporary files):
```bash
python3 job_tool.py scrape "URL" --generate --cleanup
```

---

## Detailed Usage

### Step 1: Scrape Job Postings

The `scrape` command extracts job information and creates a folder with templates.

**Basic usage:**
```bash
python3 job_tool.py scrape "https://linkedin.com/jobs/view/1234567890"
```

**With immediate generation:**
```bash
python3 job_tool.py scrape "URL" --generate
```

**With specific model:**
```bash
python3 job_tool.py scrape "URL" --generate --model llama-3.3-70b-versatile
```

**From JSON file (if LinkedIn blocks scraping):**
```bash
python3 job_tool.py scrape job-data.json
```

**Available models:**
- `llama-3.3-70b-versatile` (default, best quality)
- `llama-3.1-8b-instant` (faster, lower quality)
- `mixtral-8x7b-32768` (alternative)

**What gets created:**
```
AI-Soft-Engi-Thomson-Reuters/
├── AI-Soft-Engi-Thomson-Reuters.txt  # Job description
├── resume-template.tex               # Copy of your master resume
├── prompt.txt                        # AI instructions for resume
└── prompt-cover.txt                  # AI instructions for cover letter
```

### Step 2: Generate AI Content

The `generate` command creates tailored resume and cover letter.

**Requirements:**
- Must run after `scrape` command
- Folder must contain job description and resume-template.tex

**Basic usage:**
```bash
python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/
```

**With specific model:**
```bash
python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/ --model llama-3.3-70b-versatile
```

**With cleanup:**
```bash
python3 job_tool.py generate AI-Soft-Engi-Thomson-Reuters/ --cleanup
```

The `--cleanup` flag removes:
- `prompt.txt`
- `prompt-cover.txt`
- `resume-template.tex`

Keeps only:
- Job description
- `Resume.tex` (generated)
- `Cover_Letter.txt` (generated)

### Step 3: Create PDF

**Option A: Overleaf (Recommended - No LaTeX installation needed)**
1. Go to [overleaf.com](https://www.overleaf.com)
2. Click "New Project" → "Upload Project"
3. Upload `Resume.tex`
4. Click "Recompile"
5. Download PDF

**Option B: Local LaTeX (if installed)**
```bash
cd AI-Soft-Engi-Thomson-Reuters/
pdflatex Resume.tex
```

---

## Commands Reference

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `scrape` | Extract job info and create template folder | `python3 job_tool.py scrape "URL"` |
| `generate` | Create tailored resume and cover letter | `python3 job_tool.py generate folder/` |
| `test` | Verify Groq API key is working | `python3 job_tool.py test` |

### Scrape Options

```bash
python3 job_tool.py scrape [URL|JSON_FILE] [OPTIONS]

Options:
  --generate      Generate AI content immediately after scraping
  --cleanup       Remove template files after generation
  --model MODEL   Choose AI model (default: llama-3.3-70b-versatile)
```

### Generate Options

```bash
python3 job_tool.py generate [FOLDER_PATH] [OPTIONS]

Options:
  --model MODEL   Choose AI model
  --cleanup       Remove template files after generation
```

---

## Advanced Usage

### Working with Blocked Sites

If LinkedIn blocks scraping, use the browser bookmarklet:

1. Create a bookmark with this JavaScript:
```javascript
javascript:(function(){const t=document.querySelector('h1')?.innerText?.trim()||'';const c=document.querySelector('[data-testid="job-title"]')?.innerText?.trim()||document.querySelector('.topcard__org-name-link')?.innerText?.trim()||document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText?.trim()||'';const d=document.querySelector('.show-more-less-html__markup')?.innerText?.trim()||document.querySelector('.description__text')?.innerText?.trim()||document.querySelector('[data-testid="job-description"]')?.innerText?.trim()||'';const data={title:t,company:c,description:d,url:window.location.href};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`job-${Date.now()}.json`;a.click();URL.revokeObjectURL(url);alert('Job saved!');})();
```

2. Navigate to any job posting
3. Click the bookmarklet
4. A JSON file will download
5. Process it:
```bash
python3 job_tool.py scrape downloaded-job.json --generate
```

### Batch Processing Multiple Jobs

Create a script for multiple applications:

```bash
#!/bin/bash

jobs=(
  "https://linkedin.com/jobs/view/111"
  "https://linkedin.com/jobs/view/222"
  "https://linkedin.com/jobs/view/333"
)

for url in "${jobs[@]}"; do
  python3 job_tool.py scrape "$url" --generate --cleanup
  sleep 5  # Be nice to the servers
done
```

### Customizing AI Output

You can modify the prompts in the generated `prompt.txt` and `prompt-cover.txt` files before running the generate command to customize the AI output style.

---

## Troubleshooting

### Common Issues

**"GROQ_API_KEY not set"**
```bash
# Solution: Set your API key
export GROQ_API_KEY="your-key-here"
# Or create .env file
echo "GROQ_API_KEY=your-key-here" > .env
```

**"LinkedIn blocked" or "Failed to extract job data"**
- Use the browser bookmarklet method (see Advanced Usage)
- Save the job page as HTML and run: `python3 job_tool.py scrape saved.html`
- Check if the job requires login

**"Master resume not found"**
```bash
# Make sure you created templates/resume-template.tex
ls templates/resume-template.tex
# If missing, copy from example
cp templates/resume-template.tex.example templates/resume-template.tex
```

**"No job data found"**
- Job posting might be expired
- Some sites block automated scraping
- Try the bookmarklet method

**LaTeX compilation errors**
- Check for special characters in your resume
- Make sure all brackets are closed
- Use Overleaf for easier debugging

**AI generates incorrect information**
- This is expected - always review the output
- Check your master resume for ambiguous entries
- Edit the generated files before submitting

### Getting Help

1. Check the job folder contents:
```bash
ls -la AI-Soft-Engi-Company-Name/
```

2. Verify API key:
```bash
python3 job_tool.py test
```

3. Check Python version:
```bash
python3 --version  # Must be 3.8+
```

---

## Best Practices

### Do's

- **[DONE] Review AI output** before submitting - AI can make mistakes
- **[DONE] Keep master resume updated** with new skills and projects
- **[DONE] Use specific examples** with metrics in your master resume
- **[DONE] Apply early** - Jobs get 250+ applications in 24 hours
- **[DONE] Track everything** - Each folder represents one application
- **[DONE] Customize company names** if AI missed them
- **[DONE] Save successful versions** - Keep backup of well-performing resumes
- **[DONE] Tailor for each job** - Don't reuse the same generated resume

### Don'ts

- **[ERROR] Submit without review** - Always check AI-generated content
- **[ERROR] Lie or exaggerate** - Only include real experience
- **[ERROR] Copy job description verbatim** - Use your own words
- **[ERROR] Spam applications** - Quality over quantity
- **[ERROR] Ignore ATS keywords** - The AI handles this, but verify
- **[ERROR] Use the same resume** for different job types

### Tips for Better Results

1. **Detailed Master Resume**: The more detail in your master resume, the better the AI can tailor
2. **Clear Job Descriptions**: Ensure job postings are complete before scraping
3. **Review Keywords**: Check that important job keywords appear in your generated resume
4. **Consistent Formatting**: Keep your master resume well-formatted for best LaTeX output
5. **Save Templates**: Keep backup copies of successful resume versions

---

## Project Structure

```
crack-ats/
├── job_tool.py              # Main CLI entry point
├── groq_client.py           # Groq API integration
├── scraper.py               # Job scraping (LinkedIn, Indeed, etc.)
├── processor.py             # Folder creation and file management
├── file_ops.py              # File operations utilities
├── prompt_creator.py        # AI prompt generation
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variables template
├── templates/
│   ├── resume-template.tex      # YOUR master resume (EDIT THIS!)
│   ├── prompt-template.txt      # AI instructions template
│   └── cover-letter-template.txt # Cover letter template
│
└── [Generated Job Folders]/
    ├── [Job-Description].txt    # Scraped job description
    ├── resume-template.tex      # Copy of your master resume
    ├── prompt.txt               # AI resume instructions
    ├── prompt-cover.txt         # AI cover letter instructions
    ├── Resume.tex               # AI-generated tailored resume
    └── Cover_Letter.txt         # AI-generated cover letter
```

---

## How AI Tailoring Works

### Resume Generation Process

1. **Analyze** - AI reads job description and extracts key requirements
2. **Match** - Compares requirements with your master resume
3. **Tailor** - Rewrites content to highlight relevant experience
4. **Optimize** - Integrates keywords naturally (not verbatim copying)
5. **Format** - Preserves LaTeX structure and professional formatting

**The AI will:**
- [DONE] Rewrites bullet points to highlight relevant experience
- [DONE] Integrates keywords naturally (not verbatim copying)
- [DONE] Reorders content to emphasize matching skills
- [DONE] Removes irrelevant content
- [DONE] Keeps LaTeX formatting intact
- [DONE] Preserves dates, titles, company names

### Cover Letter Generation

Creates a 4-paragraph structure:

1. **Introduction** - Who you are and position interest (2 sentences)
2. **Skills Match** - 3 key skills with specific examples (3 sentences)
3. **Company Fit** - Why you're interested in this company (2 sentences)
4. **Closing** - Call to action and professional sign-off

---

## Privacy & Security

- **Local Processing**: Your master resume stays on your machine
- **API Calls**: Only job descriptions and tailored content are sent to Groq
- **No Storage**: Job data is stored only in local folders you control
- **API Key**: Keep your `.env` file private and don't commit it
- **Generated Content**: Review before sharing - AI may generate placeholder content

---

## License

MIT License - Free to use and modify.

See [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Stop sending generic resumes. Start getting interviews with AI-tailored applications.**

Built with Python and Groq AI.
