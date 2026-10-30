import os
import re
import shutil
import webbrowser
from pathlib import Path
from urllib.parse import urlencode


class VisibleDesktopAutomation:
    """Opens web pages and email drafts in visible desktop browser windows."""

    def open_url(self, url: str) -> dict[str, object]:
        if not url.startswith(("https://", "http://")):
            return {"success": False, "error": "Only HTTP and HTTPS URLs are allowed."}
        if not webbrowser.open(url, new=2, autoraise=True):
            return {"success": False, "error": "No desktop browser could open the URL."}
        return {"success": True, "output": f"Opened {url} in the desktop browser."}

    def send_email(self, recipient: str, subject: str, body: str) -> dict[str, object]:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
            return {"success": False, "error": "Enter a valid recipient email address."}
        if not subject.strip() or not body.strip():
            return {"success": False, "error": "Email subject and body are required."}

        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError(
                "Visible email automation requires Playwright. Install project "
                "dependencies and run `python -m playwright install chromium`."
            ) from error

        profile_directory = (
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
            / "saraswati"
            / "browser-profile"
        )
        profile_directory.mkdir(parents=True, exist_ok=True)
        chrome_executable = shutil.which("google-chrome") or shutil.which("chrome")
        compose_url = "https://mail.google.com/mail/?" + urlencode(
            {
                "view": "cm",
                "fs": "1",
                "to": recipient,
                "su": subject.strip(),
                "body": body.strip(),
            }
        )

        send_clicked = False
        try:
            with sync_playwright() as playwright:
                launch_options: dict[str, object] = {
                    "user_data_dir": str(profile_directory),
                    "headless": False,
                    "args": ["--no-first-run"],
                }
                if chrome_executable:
                    launch_options["executable_path"] = chrome_executable
                context = playwright.chromium.launch_persistent_context(**launch_options)
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto(compose_url, wait_until="domcontentloaded", timeout=45000)
                    send_button = page.get_by_role(
                        "button", name=re.compile(r"^Send", re.IGNORECASE)
                    ).first
                    send_button.wait_for(state="visible", timeout=45000)
                    send_button.click(timeout=10000)
                    send_clicked = True
                    page.get_by_text(
                        re.compile(r"Message sent", re.IGNORECASE)
                    ).wait_for(state="visible", timeout=15000)
                finally:
                    context.close()
        except PlaywrightTimeoutError as error:
            if send_clicked:
                raise RuntimeError(
                    "Gmail's Send button was clicked, but delivery was not "
                    "confirmed. Check the Sent folder before preparing another draft."
                ) from error
            raise RuntimeError(
                "Gmail did not become ready to send. Sign in to Gmail in the "
                "visible Saraswati browser profile, then prepare a new draft."
            ) from error
        except PlaywrightError as error:
            raise RuntimeError(f"Visible browser automation failed: {error}") from error

        return {"success": True, "output": f"Email sent to {recipient}."}
