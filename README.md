# 🎓 Moodle Spectrum Discord Tracker

An automated Python script powered by **Playwright** that periodically checks
Universiti Malaya's **Moodle Spectrum** platform for:

- New lecture notes
- Uploaded course materials (`.pdf`, `.docx`, `.pptx`)
- Lecturer announcements

When new updates are detected, it posts styled notifications directly to your
**Discord** channel via webhooks.

## 📌 Features

- **Persistent session management:** Uses Playwright to store authentication
  cookies (`storage_state.json`) so you only log in once.
- **Rich Discord notifications:** Sends formatted Discord embeds with direct
  links and color-coded tags:
  - Green for lecture files
  - Blurple for forum announcements
- **Differential data tracking:** Maintains a local `seen_items.json` cache to
  prevent duplicate alerts.
- **Broad selector matching:** Captures direct file downloads, assignment
  uploads, folders, and announcement discussion threads.
- **Cloud ready:** Deployable to **GitHub Actions** for free 24/7 background
  execution without needing your PC to stay powered on.

## 🛠️ Tech Stack and Prerequisites

| Component | Used for |
| --- | --- |
| Python 3.10 or higher | Application runtime |
| Playwright (Chromium) | Browser automation |
| Discord webhooks | Notifications |
| `playwright`, `requests`, `python-dotenv` | Python dependencies |

## 📁 Project Directory Structure

```text
moodle-spectrum-tracker/
│
├── .github/
│   └── workflows/
│       └── tracker.yml          # GitHub Actions 24/7 automation script
│
├── .env                         # Local private credentials (NEVER commit to Git)
├── .env.example                 # Safe environment template for repository
├── .gitignore                   # Prevents sensitive files from uploading to GitHub
├── tracker.py                   # Main Python scraping script
├── requirements.txt             # Python package dependencies
├── seen_items.json              # Local cache storing processed update links
├── storage_state.json           # Session cookies generated post-login
└── README.md                    # Project documentation
```

## 🚀 Quick Start and Installation

### 1. Clone the repository

```bash
git clone https://github.com/ethanjaydee/moodle-spectrum-tracker.git
cd moodle-spectrum-tracker
```

### 2. Set up a virtual environment

```bash
python -m venv venv
```

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ Configuration Guide

### Step 1: Create environment variables

Create a file named `.env` in the root folder, alongside `tracker.py`:

```dotenv
SPECTRUM_USERNAME=your_student_id@siswa365.um.edu.my
SPECTRUM_PASSWORD=your_actual_password
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### Step 2: Add your target course URLs

Open `tracker.py` and manually add the direct URLs of the Spectrum course
pages you want to monitor in the `COURSE_URLS` array:

```python
# tracker.py
COURSE_URLS = [
    "https://spectrum.um.edu.my/course/view.php?id=12345",  # Replace with actual Course ID
    "https://spectrum.um.edu.my/course/view.php?id=67890",
]
```

## 🧪 Execution and First-Time Login

### Interactive first run (cookie generation)

On the very first run, set `headless=False` in `tracker.py` so Playwright
opens a visible browser for you to complete any SSO or multi-factor login
challenges:

```python
# Inside tracker.py
browser = p.chromium.launch(headless=False)
```

Run the tracker:

```bash
python tracker.py
```

1. Complete the Spectrum login in the opened browser window.
2. Once landed on the main dashboard, return to your terminal and press
   **Enter**.
3. Session cookies will be saved to `storage_state.json`.

### Subsequent runs (headless background mode)

Re-enable headless execution inside `tracker.py`:

```python
browser = p.chromium.launch(headless=True)
```

Future runs will read `storage_state.json` and execute silently without
opening a browser GUI window.

## ☁️ 24/7 Cloud Automation (GitHub Actions)

To keep the tracker running every 2 hours automatically:

1. Go to your GitHub repository **Settings → Secrets and variables →
   Actions**.
2. Click **New repository secret** and add:
   - `SPECTRUM_USERNAME`: Your login username
   - `SPECTRUM_PASSWORD`: Your login password
   - `DISCORD_WEBHOOK_URL`: Your full Discord webhook URL
3. Ensure `.github/workflows/tracker.yml` is committed to your `main` branch.

## 🛡️ Security and Privacy Checklist

To protect your personal credentials and student portal session, verify that
your `.gitignore` file includes the following before pushing to GitHub:

```gitignore
.env
.env.*
!.env.example
storage_state.json
seen_items.json
__pycache__/
*.pyc
.venv/
venv/
.vscode/
```

Before committing, run `git status` to ensure `.env` and `storage_state.json`
are never highlighted for staging.
