# Moodle Spectrum Discord Tracker

An automated Python script using Playwright to monitor Moodle Spectrum for new lecture notes, PDFs, and announcements, pushing instant notification embeds directly to a Discord channel via Webhooks.

## Features
- **Automated Login & Cookie Storage:** Saves session state to `storage_state.json` to bypass login forms on future runs.
- **Discord Webhook Alerts:** Sends rich embeds for newly uploaded files (.pdf, .docx) and forum announcements.
- **Diff Checking:** Maintains `seen_items.json` to prevent duplicate alerts.

## Quick Setup
1. Clone the repository: `git clone https://github.com/YOUR_USERNAME/moodle-spectrum-tracker.git`
2. Create virtual environment: `python -m venv venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Install Chromium: `playwright install chromium`
5. Copy `.env.example` to `.env` and fill in your credentials.
6. Run the script: `python tracker.py`