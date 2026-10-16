import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

USERNAME = os.getenv("SPECTRUM_USERNAME")
PASSWORD = os.getenv("SPECTRUM_PASSWORD")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

STORAGE_STATE = BASE_DIR / "storage_state.json"
SEEN_ITEMS_FILE = BASE_DIR / "seen_items.json"
LOGIN_URL = "https://spectrum.um.edu.my/login/index.php"

# Add your Moodle course URLs here
COURSE_URLS = [
    "https://spectrum.um.edu.my/course/view.php?id=25836",
    "https://spectrum.um.edu.my/course/view.php?id=27335",
    "https://spectrum.um.edu.my/course/view.php?id=27337",
    "https://spectrum.um.edu.my/course/view.php?id=23041",
    "https://spectrum.um.edu.my/course/view.php?id=150",
    "https://spectrum.um.edu.my/course/view.php?id=151",
    "https://spectrum.um.edu.my/course/view.php?id=152",
]

RESOURCE_LINK_SELECTOR = (
    "a[href*='/mod/resource/'], "
    "a[href*='/mod/folder/'], "
    "a[href*='/mod/assign/'], "
    "a[href*='/pluginfile.php/']"
)
SECTION_LINK_SELECTOR = (
    "a[href*='/course/section.php'], "
    "a[href*='/course/view.php'][href*='section=']"
)
FOLDER_LINK_SELECTOR = "a[href*='/mod/folder/view.php']"
FOLDER_FILE_LINK_SELECTOR = "a[href*='/pluginfile.php/']"
FORUM_LINK_SELECTOR = "a[href*='/mod/forum/view.php']"
DISCUSSION_LINK_SELECTOR = "a[href*='/mod/forum/discuss.php']"
ANNOUNCEMENT_BASELINE_MARKER = "__spectrum_announcement_baseline_complete__"
ANNOUNCEMENT_FORUM_KEYWORDS = ("announc", "pengum")
WEBHOOK_MIN_INTERVAL_SECONDS = 1.0
WEBHOOK_MAX_ATTEMPTS = 5
_last_webhook_sent_at = 0.0


def load_seen_items():
    if not SEEN_ITEMS_FILE.exists():
        return []

    content = SEEN_ITEMS_FILE.read_text(encoding="utf-8")
    if not content.strip():
        return []

    items = json.loads(content)
    if not isinstance(items, list):
        raise ValueError(f"{SEEN_ITEMS_FILE} must contain a JSON list")
    return items


def save_seen_items(items):
    SEEN_ITEMS_FILE.write_text(
        json.dumps(items, indent=2),
        encoding="utf-8",
    )


def send_discord_alert(
    title,
    link,
    item_type,
    course_name="Spectrum Update",
    description=None,
):
    global _last_webhook_sent_at

    color = 5763719 if item_type == "file" else 5893266
    embed = {
        "title": f"🔔 New {item_type.capitalize()}: {title}",
        "url": link,
        "color": color,
        "fields": [
            {"name": "Source", "value": course_name, "inline": True},
            {"name": "Type", "value": item_type.upper(), "inline": True},
        ],
        "footer": {"text": "Spectrum Update Bot"},
    }
    if description:
        embed["description"] = description[:4000]
    payload = {"embeds": [embed]}

    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        delay = WEBHOOK_MIN_INTERVAL_SECONDS - (
            time.monotonic() - _last_webhook_sent_at
        )
        if delay > 0:
            time.sleep(delay)

        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            _last_webhook_sent_at = time.monotonic()
            return

        if attempt == WEBHOOK_MAX_ATTEMPTS - 1:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            try:
                retry_after = response.json().get("retry_after")
            except (ValueError, requests.exceptions.JSONDecodeError):
                retry_after = None
        try:
            retry_delay = max(0.0, float(retry_after))
        except (TypeError, ValueError):
            retry_delay = 2.0 ** attempt
        print(f"Discord rate limited the webhook; retrying in {retry_delay:.2f}s.")
        time.sleep(retry_delay)


def _canonical_discussion_url(href, page_url):
    absolute_url = urljoin(page_url, href)
    parsed_url = urlparse(absolute_url)
    discussion_id = parse_qs(parsed_url.query).get("d", [None])[0]
    if not discussion_id:
        return None
    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?d={discussion_id}"


def _record_new_file(title, href, course_name, seen_items):
    title = title.strip()
    if not title:
        title = unquote(urlparse(href).path.rsplit("/", maxsplit=1)[-1])
    if not title or not href or "action=" in href or href in seen_items:
        return

    print(f"[NEW FILE DETECTED] {title}")
    send_discord_alert(title, href, "file", course_name)
    seen_items.append(href)
    save_seen_items(seen_items)


def _scrape_embedded_announcements(page, course_name, course_url, seen_items):
    announcements = page.locator("li.section").evaluate_all(
        """sections => sections.flatMap(section => {
            const sectionTitle = (
                section.querySelector('.sectionname, h3.sectionname, h3')
                    ?.innerText || ''
            ).trim();
            if (!/announc|pengum/i.test(sectionTitle)) return [];

            const paragraphs = [...section.querySelectorAll('p')];
            const items = [];
            for (let index = 0; index < paragraphs.length; index++) {
                const paragraph = paragraphs[index];
                const heading = paragraph.querySelector('strong, b');
                if (!heading) continue;

                const title = (heading.innerText || '').trim();
                if (!title) continue;

                const body = [];
                for (let next = index + 1; next < paragraphs.length; next++) {
                    if (paragraphs[next].querySelector('strong, b')) break;
                    const text = (paragraphs[next].innerText || '')
                        .trim().replace(/\\s+/g, ' ');
                    if (text) body.push(text);
                }
                items.push({
                    sectionId: section.id || sectionTitle,
                    sectionTitle,
                    title,
                    body: body.join(' ')
                });
            }
            return items;
        })"""
    )

    for announcement in announcements:
        title = announcement["title"]
        body = announcement["body"]
        identity = json.dumps(
            [
                urlparse(course_url).path,
                announcement["sectionId"],
                title,
                body,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        announcement_id = (
            "embedded-announcement:"
            + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        )
        if announcement_id in seen_items:
            continue

        link = f"{course_url}#{announcement['sectionId']}"
        print(f"[NEW ANNOUNCEMENT DETECTED] {title}")
        send_discord_alert(
            title,
            link,
            "announcement",
            f"{course_name} / {announcement['sectionTitle']}",
            description=body or None,
        )
        seen_items.append(announcement_id)
        save_seen_items(seen_items)


def _scrape_resource_page(page, course_name, seen_items):
    folder_urls = page.locator(FOLDER_LINK_SELECTOR).evaluate_all(
        "links => [...new Set(links.map(link => link.href))]"
    )

    for link in page.locator(RESOURCE_LINK_SELECTOR).all():
        href = link.get_attribute("href")
        if href:
            _record_new_file(link.inner_text(), href, course_name, seen_items)

    for folder_url in folder_urls:
        page.goto(folder_url, wait_until="domcontentloaded")
        if not _is_logged_in(page):
            raise RuntimeError(
                "Spectrum session expired while reading a course folder. "
                "Run tracker.py again to sign in and refresh storage_state.json."
            )

        folder_title = page.title().split("|", maxsplit=1)[0].strip()
        folder_source = f"{course_name} / {folder_title}"
        for link in page.locator(FOLDER_FILE_LINK_SELECTOR).all():
            href = link.get_attribute("href")
            if href:
                _record_new_file(
                    link.inner_text(),
                    href,
                    folder_source,
                    seen_items,
                )


def _is_announcement_forum(title):
    normalized_title = title.casefold()
    return any(keyword in normalized_title for keyword in ANNOUNCEMENT_FORUM_KEYWORDS)


def _has_valid_storage_state():
    if not STORAGE_STATE.is_file():
        return False

    try:
        state = json.loads(STORAGE_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return (
        isinstance(state, dict)
        and isinstance(state.get("cookies"), list)
        and isinstance(state.get("origins"), list)
    )


def _should_force_headless():
    return os.getenv("GITHUB_ACTIONS", "").lower() == "true"


def _is_logged_in(page):
    parsed_url = urlparse(page.url)
    if parsed_url.hostname != "spectrum.um.edu.my":
        return False
    if parsed_url.path.startswith("/login/"):
        return False

    login_fields = page.locator(
        "input[name='username'], input[name='password'], "
        "#username, #password, #i0116, #i0118"
    )
    return not login_fields.first.is_visible()


def _try_automatic_login(page):
    sso_button = page.locator(
        "a:has-text('Single Sign On'), "
        "a:has-text('SSO'), "
        ".login-identityprovider a"
    ).first
    if sso_button.is_visible():
        print("Following the Spectrum SSO redirect...")
        sso_button.click()
        page.wait_for_load_state("domcontentloaded")

    username_submitted = False
    username_field = page.locator(
        "#username, input[name='username'], input[type='email'], #i0116"
    ).first
    if USERNAME and username_field.is_visible():
        username_field.fill(USERNAME)

        next_button = page.locator(
            "input[type='submit'][value='Next'], #idSIButton9"
        ).first
        if next_button.is_visible():
            next_button.click()
            username_submitted = True
            page.wait_for_load_state("domcontentloaded")

    password_field = page.locator(
        "#password, input[name='password'], input[type='password'], #i0118"
    ).first
    if username_submitted and not password_field.is_visible():
        try:
            password_field.wait_for(state="visible", timeout=10000)
        except PlaywrightTimeoutError:
            print("SSO has not presented a password prompt; waiting for manual login.")

    if PASSWORD and password_field.is_visible():
        password_field.fill(PASSWORD)
        submit_button = page.locator(
            "button[type='submit'], #loginbtn, "
            "input[type='submit'], #idSIButton9"
        ).first
        if submit_button.is_visible():
            submit_button.click()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                print("Login response is still loading; checking authentication status.")


def _authenticate(page, context):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    _try_automatic_login(page)

    if not _is_logged_in(page):
        print(
            "Please complete Spectrum/SSO login in the open browser, "
            "the tracker will continue after login is detected."
        )
        login_deadline = time.monotonic() + 300
        while not _is_logged_in(page) and time.monotonic() < login_deadline:
            page.wait_for_timeout(1000)
        if not _is_logged_in(page):
            raise RuntimeError(
                "Spectrum login was not detected within five minutes; "
                "storage_state.json was not saved."
            )

    page.goto(COURSE_URLS[0], wait_until="domcontentloaded")
    if not _is_logged_in(page):
        raise RuntimeError(
            "Spectrum login was not detected after the login step; "
            "storage_state.json was not saved."
        )

    context.storage_state(path=str(STORAGE_STATE))
    print("Login successful; session state saved.")


def _scrape_course(page, url, seen_items, baseline_announcements):
    page.goto(url, wait_until="domcontentloaded")
    if not _is_logged_in(page):
        raise RuntimeError(
            "Spectrum session expired while scraping. Run tracker.py again "
            "to sign in and refresh storage_state.json."
        )

    course_name = page.title()
    print(f"Scraping: {course_name} ({page.url})")

    section_urls = page.locator(SECTION_LINK_SELECTOR).evaluate_all(
        "links => [...new Set(links.map(link => link.href))]"
    )
    forum_urls = set(
        page.locator(FORUM_LINK_SELECTOR).evaluate_all(
            "links => links.map(link => link.href)"
        )
    )
    _scrape_embedded_announcements(page, course_name, url, seen_items)

    _scrape_resource_page(page, course_name, seen_items)

    for section_url in section_urls:
        page.goto(section_url, wait_until="domcontentloaded")
        if not _is_logged_in(page):
            raise RuntimeError(
                "Spectrum session expired while reading a course section. "
                "Run tracker.py again to sign in and refresh storage_state.json."
            )

        forum_urls.update(
            page.locator(FORUM_LINK_SELECTOR).evaluate_all(
                "links => links.map(link => link.href)"
            )
        )
        section_title = page.title().split("|", maxsplit=1)[0].strip()
        _scrape_resource_page(
            page,
            f"{course_name} / {section_title}",
            seen_items,
        )

    for forum_url in sorted(forum_urls):
        page.goto(forum_url, wait_until="domcontentloaded")
        if not _is_logged_in(page):
            raise RuntimeError(
                "Spectrum session expired while reading an announcement forum. "
                "Run tracker.py again to sign in and refresh storage_state.json."
            )

        forum_title = page.title().split("|", maxsplit=1)[0].strip()
        if not _is_announcement_forum(forum_title):
            continue

        topics_by_url = {}
        for link in page.locator(DISCUSSION_LINK_SELECTOR).all():
            href = link.get_attribute("href")
            title = link.inner_text().strip()
            if not href or not title:
                continue
            topic_url = _canonical_discussion_url(href, page.url)
            if topic_url:
                topics_by_url.setdefault(topic_url, title)

        for topic_url, title in topics_by_url.items():
            if topic_url in seen_items:
                continue
            if baseline_announcements:
                seen_items.append(topic_url)
                continue

            print(f"[NEW ANNOUNCEMENT DETECTED] {title}")
            send_discord_alert(
                title,
                topic_url,
                "announcement",
                f"{course_name} / {forum_title}",
            )
            seen_items.append(topic_url)
            save_seen_items(seen_items)


def run_tracker():
    seen_items = load_seen_items()
    storage_is_valid = _has_valid_storage_state()
    force_headless = _should_force_headless()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=storage_is_valid or force_headless
        )
        try:
            try:
                context = browser.new_context(
                    storage_state=str(STORAGE_STATE) if storage_is_valid else None
                )
            except PlaywrightError:
                if not storage_is_valid:
                    raise
                print(
                    "Saved session state is invalid; starting a fresh browser session."
                )
                browser.close()
                browser = playwright.chromium.launch(headless=force_headless)
                context = browser.new_context()
                storage_is_valid = False

            page = context.new_page()
            if storage_is_valid:
                page.goto(COURSE_URLS[0], wait_until="domcontentloaded")
                if not _is_logged_in(page):
                    print(
                        "Saved session has expired; starting a fresh browser session."
                    )
                    context.close()
                    browser.close()
                    browser = playwright.chromium.launch(headless=force_headless)
                    context = browser.new_context()
                    page = context.new_page()
                    _authenticate(page, context)
            else:
                _authenticate(page, context)

            print("Checking course pages for updates...")
            baseline_announcements = (
                ANNOUNCEMENT_BASELINE_MARKER not in seen_items
            )
            for course_url in COURSE_URLS:
                _scrape_course(
                    page,
                    course_url,
                    seen_items,
                    baseline_announcements,
                )

            if baseline_announcements:
                seen_items.append(ANNOUNCEMENT_BASELINE_MARKER)
                print(
                    "Announcement baseline established; existing topics "
                    "were recorded without notifications."
                )

            save_seen_items(seen_items)
            print("Tracker run complete.")
        finally:
            browser.close()


if __name__ == "__main__":
    run_tracker()
