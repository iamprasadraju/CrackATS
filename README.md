# CrackATS - AI Resume Generator & Job Tracker

Generate tailored resumes and cover letters for each job application using AI. Track your applications with a visual kanban board and instantly open them in Overleaf for editing.

## Features

- **AI-Powered Resume Tailoring** - Automatically customizes your resume for each job description
- **Cover Letter Generation** - Creates personalized cover letters that match the job
- **Overleaf Integration** - One-click export to Overleaf with automatic project naming
- **Job Application Tracker** - Visual kanban board to track applications through the hiring process
- **Document Viewer** - View and edit resumes/cover letters directly in the browser
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

# 4. Start the web interface
python main.py
```

Visit `http://localhost:8000` and click **"Set API Key"** in the navbar to configure your Groq API key through the UI.

**Alternative (CLI):** Set via environment variable:
```bash
echo "GROQ_API_KEY=your-api-key-here" > .env
```

## Configuration

### 1. Customize Your Master Resume (Optional)

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

### 2. Using the Web Interface

After running `python main.py`, visit `http://localhost:8000`

#### Set API Key (First Time Setup)
1. Click **"Set API Key"** button in the navbar
2. Get your free API key from [console.groq.com/keys](https://console.groq.com/keys)
3. Paste your key (format: `gsk_...`)
4. Click **Save API Key**
5. The key is tested and saved to `.env` automatically

## Usage

### Web Interface

#### Generator Tab
1. Paste a job posting URL (LinkedIn, Indeed, etc.)
2. Click "Generate Resume"
3. AI analyzes the job and creates tailored resume + cover letter
4. Click **"Overleaf"** button to instantly open in Overleaf
   - Project automatically named: `Role_Company.tex`
   - Duplicate prevention: Re-opens go to your projects dashboard
5. Or use Copy/Download to save locally

#### Overleaf Integration

**First Click:**
- Creates new Overleaf project
- Named after the job: `Software_Engineer_Google.tex`
- Content encoded and opened in new tab

**Subsequent Clicks:**
- Automatically redirects to your Overleaf projects dashboard
- Prevents duplicate project creation
- Session-based tracking (resets on browser close)

#### Tracker Tab
- **Kanban Board**: Drag cards between columns (Saved → Applied → Shortlisted → Interview → Technical → Offer)
- **Add Applications**: Click "+ New Application" or use "+ Add" in each column
- **View Documents**: Click "View Docs" to see resume/cover letter
  - Edit documents directly in the modal
  - Open in Overleaf with one click
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
│   ├── index.html         # Main HTML with credits footer
│   ├── style.css          # Styles with Overleaf button, footer
│   └── app.js             # JavaScript with Overleaf integration
├── templates/             # LaTeX templates
│   ├── resume-template.tex
│   ├── prompt-template.txt
│   └── cover-letter-template.txt
└── requirements.txt
```

## Troubleshooting

### API Key Issues

**Using Web UI (Recommended):**
1. Click **"Set API Key"** in the navbar
2. Enter your key (starts with `gsk_`)
3. Click Save - it's tested automatically

**Using CLI:**
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
- `GET /api/applications/stats/overview` - Get application statistics

### Documents
- `GET /resume/{folder}` - Get resume content
- `GET /cover-letter/{folder}` - Get cover letter content
- `POST /api/save-document` - Save document changes
- `GET /tex-export/{folder}/{filename}` - Export raw TeX for Overleaf

### Template
- `GET /template` - Get master resume template
- `POST /template` - Update master resume template

### Database
- `GET /api/database/info` - Database location and status
- `POST /api/database/backup` - Create manual backup
- `POST /api/applications/reset` - Reset database (deletes all data)
- `POST /api/applications/cleanup` - Remove orphaned applications

### Configuration
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update API key

### Status Tracking

The application tracks jobs through these stages:
1. **Saved** - Job saved for later
2. **Applied** - Application submitted
3. **Shortlisted** - Application shortlisted
4. **Interview** - Interview scheduled
5. **Technical** - Technical round
6. **Offer** - Offer received
7. **Rejected** - Application rejected
8. **Withdrawn** - Application withdrawn

## Overleaf Integration Details

### How It Works

1. **Click "Overleaf" button**
2. Content is base64 encoded (avoids localhost restrictions)
3. Opens: `https://www.overleaf.com/docs?snip_uri=data:application/x-tex;base64,...&snip_name=Role_Company.tex`
4. Overleaf creates new project with your content

### Technical Implementation

- Uses base64 data URI for content transfer
- Passes `snip_name` parameter for project naming
- Session storage tracks opened documents
- Redirects to dashboard on repeat clicks

### Supported Files

- `.tex` files (resumes) - `application/x-tex`
- `.txt` files (cover letters) - `text/plain`

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

## Credits & Donations

**Created with ❤️ by Prasad Raju**

If this project helped you land your dream job, consider supporting its development:

**Ethereum (ETH):** `0xdeFE5597a76EFECDc29Fa01798c5470224dB394F`

---

Made with ❤️ using FastAPI, Groq AI, and modern web technologies.
