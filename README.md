# CrackATS - AI Resume Generator & Job Tracker

Generate tailored resumes and cover letters for each job application using AI. Track your applications with a visual kanban board.

## Features

- **AI-Powered Resume Tailoring** - Automatically customizes your resume for each job description
- **Cover Letter Generation** - Creates personalized cover letters that match the job
- **Job Application Tracker** - Visual kanban board to track applications through the hiring process
- **Cross-Platform** - Works on Windows, macOS, and Linux
- **Safe Data Storage** - Database stored in user directory, survives app updates
- **Privacy First** - All data stored locally, only job descriptions sent to AI

## Installation

### Prerequisites

- Python 3.10 or higher
- Groq API key (free at [console.groq.com](https://console.groq.com/keys))

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/crack-ats.git
cd crack-ats

# 2. Create virtual environment (recommended)
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your API key
echo "GROQ_API_KEY=your-api-key-here" > .env
```

## Configuration

### 1. Customize Your Master Resume

Edit `templates/resume-template.tex` with your information:

```latex
{\LARGE Your Name}\\
Your Location • your.email@example.com

\section*{Summary}
Brief professional summary...

\section*{Experience}
\textbf{Job Title} \hfill Start Date -- End Date\\
Company Name, Location
\begin{itemize}
    \item Achievement with metrics
    \item Another achievement
\end{itemize}
```

**Tips for best results:**
- Include specific metrics (e.g., "Increased performance by 40%")
- List all technologies you've worked with
- Keep descriptions detailed but concise
- Add both technical and soft skills

### 2. Test Your Setup

```bash
python job_tool.py test
```

You should see: "API key is working correctly!"

## Usage

### Web Interface (Recommended)

Start the server:

```bash
python main.py
```

Visit `http://localhost:8000`

#### Generator Tab
1. Paste a job posting URL (LinkedIn, Indeed, etc.)
2. Click "Generate Resume"
3. AI analyzes the job and creates tailored resume + cover letter
4. Copy to Overleaf or download as .tex file

#### Tracker Tab
- **Kanban Board**: Drag cards between columns (Saved → Applied → Shortlisted → Interview → Offer)
- **Add Applications**: Click "+ New Application" or drag existing cards
- **View Documents**: Click "View Docs" on any card to see resume/cover letter
- **Statistics**: Track total applications, response rate, and offers

### Command Line Interface

#### Basic Commands

```bash
# Scrape a job and create folder
python job_tool.py scrape "https://linkedin.com/jobs/view/123"

# Scrape and generate immediately
python job_tool.py scrape "https://linkedin.com/jobs/view/123" --generate

# Generate AI content for existing folder
python job_tool.py generate "AI-Soft-Engi-Google/"

# Clean up template files after generation
python job_tool.py scrape "URL" --generate --cleanup
```

#### CLI Workflow Example

```bash
# Step 1: Scrape job
python job_tool.py scrape "https://linkedin.com/jobs/view/123456"
# Creates folder: AI-Soft-Engi-Google/

# Step 2: Review job description in the folder
# Edit prompts if needed

# Step 3: Generate AI content
python job_tool.py generate "AI-Soft-Engi-Google/"

# Output:
# - Resume.tex (LaTeX format)
# - Cover_Letter.txt
```

## Data Storage

Your job application data is stored separately from the application code in platform-specific user directories:

### Database Locations

| Platform | Full Path | Environment Variable |
|----------|-----------|---------------------|
| **Windows** | `C:\Users\<Username>\AppData\Roaming\CrackATS\applications.db` | `%APPDATA%\CrackATS\` |
| **macOS** | `/Users/<Username>/Library/Application Support/CrackATS/applications.db` | `~/Library/Application Support/CrackATS/` |
| **Linux** | `/home/<Username>/.local/share/CrackATS/applications.db` | `~/.local/share/CrackATS/` |

### What's Stored

```
CrackATS/
├── applications.db           # Main SQLite database (all your job applications)
└── backups/
    ├── applications_20240115_143022.db
    ├── applications_20240116_091530.db
    └── ...                   # Last 10 automatic backups
```

### Automatic Migration

**First Run:** If upgrading from v1.x, your existing database in the project folder is automatically:
1. Copied to the new user data location
2. Renamed to `applications.db.backup` in project folder (safety backup)
3. New location used going forward

### Backups

**Automatic:** Before any database schema changes or major operations
**Retention:** Last 10 backups (older ones auto-deleted)
**Location:** `backups/` subdirectory in your user data folder

**Manual Backup via API:**
```bash
curl -X POST http://localhost:8000/api/database/backup
```

**Check Your Database Location:**
```bash
curl http://localhost:8000/api/database/info
```

### Why This Matters

- **App Updates:** Your data survives app upgrades/reinstalls
- **Multi-User:** Each OS user has their own isolated database
- **Permissions:** No admin rights needed (writes to user directory)
- **Backup:** Easy to backup/sync your `CrackATS/` folder

- Automatic backups created before database changes
- Stored in `backups/` subdirectory
- Last 10 backups retained
- Manual backup: `POST /api/database/backup` (web interface)

## Project Structure

```
crack-ats/
├── main.py                 # FastAPI web server
├── job_tool.py            # CLI interface
├── database.py            # Database models
├── paths.py               # Cross-platform paths
├── exceptions.py          # Custom exceptions
├── groq_client.py         # AI API client
├── scraper.py             # Job scraping
├── static/                # Web UI files
│   ├── index.html
│   ├── style.css
│   └── app.js
├── templates/             # LaTeX templates
│   ├── resume-template.tex
│   ├── prompt-template.txt
│   └── cover-letter-template.txt
└── requirements.txt
```

## Troubleshooting

### API Key Issues

```bash
# Test API key
python job_tool.py test

# Check .env file exists
cat .env
```

### Database Issues

```bash
# Check database location
curl http://localhost:8000/api/database/info

# View debug info
curl http://localhost:8000/api/debug/statuses
```

### Windows Path Issues

If viewing documents fails on Windows, ensure you're using the web interface which handles Windows paths correctly.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key | Required |
| `GROQ_MODEL` | AI model to use | `llama-3.3-70b-versatile` |

## API Endpoints

### Applications
- `GET /api/applications` - List all applications
- `POST /api/applications` - Create new application
- `GET /api/applications/{id}` - Get specific application
- `PUT /api/applications/{id}` - Update application
- `DELETE /api/applications/{id}` - Delete application
- `POST /api/applications/{id}/status` - Update status (for drag-and-drop)

### Documents
- `GET /resume/{folder}` - Get resume content
- `GET /cover-letter/{folder}` - Get cover letter content
- `POST /api/save-document` - Save document changes

### Database
- `GET /api/database/info` - Database location and status
- `POST /api/database/backup` - Create manual backup
- `POST /api/applications/reset` - Reset database (deletes all data)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

- Report issues: [GitHub Issues](https://github.com/yourusername/crack-ats/issues)
- Get API key: [console.groq.com](https://console.groq.com/keys)
