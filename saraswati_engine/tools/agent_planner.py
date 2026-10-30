import re
from dataclasses import dataclass
from typing import Any


SYSTEM_ACTIONS = {
    "list_files": ("ls -la", "Here are your directory files"),
    "show_user": ("whoami", "You are currently logged in as"),
    "show_date": ("date", "Today's date and time is"),
    "system_uptime": ("uptime", "Here is the system uptime"),
    "os_info": ("uname -a", "Here is your operating system kernel information"),
    "disk_space": ("df -h", "Here is the disk space usage"),
    "process_management": (
        "ps aux --sort=-%cpu",
        "Here are the running system processes",
    ),
}

SEPARATOR = re.compile(
    r"\s*(?:;|\bthen\b|,\s*|\band then\b|\band\s+(?=(?:open|launch|start|"
    r"check|show|list|display|tell me|what|how|process(?:es)?|disk|storage|"
    r"files|uptime|kernel|username|running)\b))\s*",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
APP_PATTERN = re.compile(
    r"\b(?:open|launch|start)\s+(?P<app>firefox|(?:vs\s*code)|vscode|"
    r"visual studio code|vlc|chrome|browser|terminal|files|file manager)\b",
    re.IGNORECASE,
)
WEBSITE_PATTERN = re.compile(
    r"\b(?:open|launch|go to)\s+(?P<site>gmail|google|youtube)\b",
    re.IGNORECASE,
)
WEBSITE_URLS = {
    "gmail": "https://mail.google.com/",
    "google": "https://www.google.com/",
    "youtube": "https://www.youtube.com/",
}
INTENT_FALLBACKS = (
    ("disk_space", re.compile(r"\b(disk|storage|free space)\b", re.I)),
    ("process_management", re.compile(r"\b(process(?:es)?|running apps)\b", re.I)),
    ("list_files", re.compile(r"\b(files|directory contents)\b", re.I)),
    ("show_date", re.compile(r"\b(date|time)\b", re.I)),
    ("system_uptime", re.compile(r"\b(uptime|time since boot)\b", re.I)),
    ("os_info", re.compile(r"\b(kernel|operating system|linux version)\b", re.I)),
    ("show_user", re.compile(r"\b(username|who am i|logged in user)\b", re.I)),
)

APP_KEYS = {
    "firefox": "firefox",
    "vs code": "vscode",
    "vscode": "vscode",
    "visual studio code": "vscode",
    "vlc": "vlc",
    "chrome": "chrome",
    "browser": "browser",
    "terminal": "terminal",
    "files": "file-manager",
    "file manager": "file-manager",
}


@dataclass(frozen=True)
class PlannedAction:
    tool: str
    intent: str
    description: str
    command: str = ""
    app_key: str = ""
    url: str = ""
    recipient: str = ""
    subject: str = ""
    body: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "tool": self.tool,
            "intent": self.intent,
            "description": self.description,
        }


def _classify(classifier: Any, text: str) -> str:
    intent, confidence = classifier.predict_intent(text)
    if intent != "unknown" and confidence >= 0.7:
        return intent
    for fallback_intent, pattern in INTENT_FALLBACKS:
        if pattern.search(text):
            return fallback_intent
    return "unknown"


def plan_query(query: str, classifier: Any) -> list[PlannedAction]:
    """Build a deterministic, ordered tool plan from independently classified steps."""
    located_actions: list[tuple[int, PlannedAction]] = []
    consumed_spans: list[tuple[int, int]] = []

    for match in WEBSITE_PATTERN.finditer(query):
        site = match.group("site").lower()
        located_actions.append(
            (
                match.start(),
                PlannedAction(
                    "browser.open_url",
                    "open_url",
                    f"Open {site}",
                    url=WEBSITE_URLS[site],
                ),
            )
        )
        consumed_spans.append(match.span())

    for match in URL_PATTERN.finditer(query):
        url = match.group(0).rstrip(".,;)")
        located_actions.append(
            (
                match.start(),
                PlannedAction(
                    "browser.open_url", "open_url", f"Open {url}", url=url
                ),
            )
        )
        consumed_spans.append(match.span())

    for match in APP_PATTERN.finditer(query):
        app_name = re.sub(r"\s+", " ", match.group("app").lower()).strip()
        app_key = APP_KEYS[app_name]
        located_actions.append(
            (
                match.start(),
                PlannedAction(
                    "desktop.launch_app",
                    "launch_app",
                    f"Launch {app_name}",
                    app_key=app_key,
                ),
            )
        )
        consumed_spans.append(match.span())

    parts: list[tuple[int, str]] = []
    previous_end = 0
    for separator in SEPARATOR.finditer(query):
        parts.append((previous_end, query[previous_end : separator.start()]))
        previous_end = separator.end()
    parts.append((previous_end, query[previous_end:]))

    for part_start, raw_part in parts:
        part = raw_part.strip()
        part_start += len(raw_part) - len(raw_part.lstrip())
        if any(start <= part_start < end for start, end in consumed_spans):
            continue
        if URL_PATTERN.search(part) or APP_PATTERN.search(part) or WEBSITE_PATTERN.search(part):
            continue

        intent = _classify(classifier, part)
        if intent in SYSTEM_ACTIONS:
            command, description = SYSTEM_ACTIONS[intent]
            located_actions.append(
                (
                    part_start,
                    PlannedAction(
                        "system.command",
                        intent,
                        description,
                        command=command,
                    ),
                )
            )
        elif intent == "launch_app":
            app_match = re.search(
                r"\b(firefox|vscode|vs\s*code|visual studio code|vlc|chrome|browser|terminal)\b",
                part,
                re.IGNORECASE,
            )
            if app_match:
                app_name = re.sub(
                    r"\s+", " ", app_match.group(1).lower()
                ).strip()
                app_key = APP_KEYS[app_name]
                located_actions.append(
                    (
                        part_start,
                        PlannedAction(
                            "desktop.launch_app",
                            "launch_app",
                            f"Launch {app_name}",
                            app_key=app_key,
                        ),
                    )
                )

    return [action for _, action in sorted(located_actions, key=lambda item: item[0])]
