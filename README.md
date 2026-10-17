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
  uploads, folders, section pages, and announcement discussion threads.
- **Embedded announcement detection:** Finds announcement text posted directly
  in Moodle course sections, including English and Malay headings such as
  `Announcement`, `Pengumuman`, and `Pengumunan`.
- **AI announcement fallback:** Optionally classifies ambiguous course-section
  text with the direct Mistral API when a human would recognize it as a notice
  even without an announcement heading.
- **Resilient notifications:** Spaces Discord webhook requests and retries
  Discord rate-limit responses.
- **Cloud ready:** Deployable to **GitHub Actions** for free background
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
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=ministral-3b-latest
AI_ANNOUNCEMENT_ENABLED=true
AI_ANNOUNCEMENT_THRESHOLD=0.80
AI_ANNOUNCEMENT_DRY_RUN=false
```

`SPECTRUM_USERNAME` and `SPECTRUM_PASSWORD` are used to attempt automatic
Spectrum/SSO login. If automatic login is not available or does not complete,
the local tracker opens a visible browser so you can finish logging in
manually.

AI fallback classification is disabled unless `AI_ANNOUNCEMENT_ENABLED=true`
and `MISTRAL_API_KEY` is configured. The threshold must be between `0` and `1`;
`0.80` is the recommended starting value.

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

Run the tracker normally:

```bash
python tracker.py
```

When `storage_state.json` is missing, invalid, or expired, the tracker:

1. Opens a visible browser window locally.
2. Attempts the configured username/password and Spectrum SSO flow.
3. Waits up to five minutes for you to complete any remaining SSO or
   multi-factor login steps manually.
4. Saves the successful browser session to `storage_state.json`.

You do not need to edit the `headless` setting in `tracker.py`.

### Subsequent runs

When `storage_state.json` is valid, the tracker loads it and runs headlessly.
If the saved session has expired, it starts a new local headed login flow and
replaces the saved session after successful authentication.

The tracker checks each configured course for:

- Resources, assignments, folders, and files linked through section pages
- Announcement forums and their discussion topics
- Announcement text embedded directly in course sections

On the first run with a new `seen_items.json`, existing forum topics are
recorded as a baseline without sending a notification. New items found on
later runs are sent to Discord and deduplicated by their
tracked URL or generated announcement ID. Successful notifications are saved
immediately to reduce duplicate alerts if a run is interrupted.

## ☁️ Hourly Cloud Automation (GitHub Actions)

The included workflow runs the tracker every hour and can also be started
manually with **Run workflow**:

1. Go to your GitHub repository **Settings → Secrets and variables →
   Actions**.
2. Click **New repository secret** and add:
   - `SPECTRUM_USERNAME`: Your login username
   - `SPECTRUM_PASSWORD`: Your login password
   - `DISCORD_WEBHOOK_URL`: Your full Discord webhook URL
   - `STORAGE_STATE_BASE64`: A base64-encoded copy of your locally generated
     `storage_state.json`
3. Ensure `.github/workflows/tracker.yml` is committed to your `main` branch.

GitHub Actions always runs headlessly, so it cannot complete an interactive
login. Generate and validate `storage_state.json` locally first, then encode
its contents and save the result as the `STORAGE_STATE_BASE64` secret. In
Windows PowerShell, copy the encoded value with:

```powershell
[Convert]::ToBase64String(
    [IO.File]::ReadAllBytes("storage_state.json")
) | Set-Clipboard
```

The workflow restores this session before running and commits updated
`seen_items.json` back to the repository. Keep `storage_state.json` out of
source control; update the `STORAGE_STATE_BASE64` secret whenever the local
session needs to be refreshed.

If the saved session expires in GitHub Actions, the workflow will stop with a
login error rather than waiting for manual interaction. Refresh the session
locally and update the secret.

## 🤖 AI Announcement Fallback

The normal selectors and announcement-heading rules run first. The optional AI
fallback then reviews eligible Moodle section text that was not already
recognized as an announcement. It asks the direct Mistral API for strict JSON
using `MISTRAL_MODEL` (default: `ministral-3b-latest`).

- Whether the text is an announcement
- A confidence score from `0` to `1`
- A short title and summary

Only results at or above `AI_ANNOUNCEMENT_THRESHOLD` are sent to Discord.
Candidate IDs and negative classifications are stored in `seen_items.json`,
so the same unchanged text is not classified on every run. Email addresses and
long numeric identifiers are redacted before candidate text is sent to Mistral.

Set these GitHub Actions secrets when enabling the feature:

```text
MISTRAL_API_KEY
MISTRAL_MODEL
AI_ANNOUNCEMENT_ENABLED
AI_ANNOUNCEMENT_THRESHOLD
AI_ANNOUNCEMENT_DRY_RUN
```

AI failures are logged and skipped; deterministic scraping continues. Use
`AI_ANNOUNCEMENT_ENABLED=false` to run without AI classification. Set
`AI_ANNOUNCEMENT_DRY_RUN=true` to review AI decisions without Discord sends or
seen-item updates.

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
