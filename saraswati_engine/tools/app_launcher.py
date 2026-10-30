from pathlib import Path
import subprocess
from typing import Any, Dict

class SafeAppLauncher:
    """
    Safety Firewall Layer that validates and launches desktop applications and web links.
    """
    def __init__(self):
        # Explicit allowlist of safe desktop applications and browsers
        self.ALLOWED_APPS: Dict[str, str] = {
            "vscode": "code",
            "code": "code",
            "firefox": "firefox",
            "chrome": "google-chrome",
            "browser": "google-chrome",
            "vlc": "vlc",
            "terminal": "konsole",  # Or gnome-terminal depending on your desktop environment
            "settings": "kcmshell6",  # Or systemsettings
            "file-manager": "xdg-open",
        }

    def launch_application(self, app_key: str) -> Dict[str, Any]:
        app_key = app_key.lower().strip()
        
        if app_key not in self.ALLOWED_APPS:
            return {
                "success": False,
                "error": f"Permission Denied: Application '{app_key}' is not on the Saraswati app allowlist.",
                "blocked": True
            }

        binary = self.ALLOWED_APPS[app_key]
        arguments = [binary]
        if app_key == "file-manager":
            arguments.append(str(Path.home()))
        try:
            # Launch in background detached from python process
            subprocess.Popen(
                arguments,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return {
                "success": True,
                "output": f"Successfully launched {app_key}."
            }
        except OSError as e:
            return {
                "success": False,
                "error": str(e)
            }

if __name__ == "__main__":
    launcher = SafeAppLauncher()
    print("--- Saraswati Safe App Launcher Test ---")
    print(launcher.launch_application("vscode"))