# 🎓 Moodle Spectrum Discord Tracker

An automated Python script powered by **Playwright** that periodically checks Universiti Malaya's **Moodle Spectrum** platform for new lecture notes, uploaded course materials (.pdf, .docx, .pptx), and lecturer announcements. When new updates are detected, it posts styled notifications directly to your **Discord** channel via Webhooks.

---

## 📌 Features

* **Persistent Session Management:** Uses Playwright to store authentication cookies (`storage_state.json`) so you only log in once.
* **Rich Discord Notifications:** Sends formatted Discord embeds with direct links and color-coded tags (Green for lecture files, Blurple for forum announcements).
* **Differential Data Tracking:** Maintains a local `seen_items.json` cache to prevent duplicate alerts.
* **Broad Selector Matching:** Captures direct file downloads, assignment uploads, folders, and announcement discussion threads.
* **Cloud Ready:** Deployable to **GitHub Actions** for free 24/7 background execution without needing your PC to stay powered on.

---

## 🛠️ Tech Stack & Prerequisites

* **Python:** 3.10 or higher
* **Automation:** Playwright (Chromium)
* **Notifications:** Discord Webhooks
* **Dependencies:** `playwright`, `requests`, `python-dotenv`

---

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

🚀 Quick Start & Installation
1. Clone the Repository
git clone [https://github.com/ethanjaydee/moodle-spectrum-tracker.git](https://github.com/ethanjaydee/moodle-spectrum-tracker.git)
cd moodle-spectrum-tracker

2. Set Up Virtual Environment
python -m venv venv

# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# On macOS / Linux:
source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt
playwright install chromium

⚙️ Configuration Guide
Step 1: Create Environment Variables
Create a file named .env in the root folder (alongside tracker.py):
SPECTRUM_USERNAME=your_student_id@siswa365.um.edu.my
SPECTRUM_PASSWORD=your_actual_password
DISCORD_WEBHOOK_URL=[https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN](https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN)

Step 2: Add Your Target Course URLs
Open tracker.py and manually add the direct URLs of the Spectrum course pages you want to monitor in the COURSE_URLS array:
# tracker.py
COURSE_URLS = [
    "[https://spectrum.um.edu.my/course/view.php?id=12345](https://spectrum.um.edu.my/course/view.php?id=12345)",  # Replace with actual Course ID
    "[https://spectrum.um.edu.my/course/view.php?id=67890](https://spectrum.um.edu.my/course/view.php?id=67890)",
]

🧪 Execution & First-Time Login
Interactive First Run (Cookie Generation)
On the very first run, set headless=False in tracker.py so Playwright opens a visible browser for you to complete any SSO or multi-factor login challenges:
# Inside tracker.py
browser = p.chromium.launch(headless=False)
Run the tracker:
python tracker.py
1. Complete the Spectrum login in the opened browser window.
2. Once landed on the main dashboard, return to your terminal and press ENTER.
3. Session cookies will be saved to storage_state.json.

Subsequent Runs (Headless Background Mode)
Re-enable headless execution inside tracker.py:
browser = p.chromium.launch(headless=True)
Future runs will read storage_state.json and execute silently without opening a browser GUI window.

☁️ 24/7 Cloud Automation (GitHub Actions)
To keep the tracker running every 2 hours automatically
1. Go to your GitHub Repository Settings -> Secrets and variables -> Actions.
2. Click New repository secret and add:
    SPECTRUM_USERNAME: Your login username
    SPECTRUM_PASSWORD: Your login password
    DISCORD_WEBHOOK_URL: Your full Discord Webhook URL
3. Ensure .github/workflows/tracker.yml is committed to your main branch.

🛡️ Security & Privacy Checklist
To protect your personal credentials and student portal session, verify that your .gitignore file includes the following before pushing to GitHub:
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
Verify before committing: Run git status to ensure .env and storage_state.json are never highlighted for staging.
