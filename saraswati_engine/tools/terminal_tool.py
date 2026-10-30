import os
import shlex
import subprocess
from typing import Any, Dict, List

class SafeTerminalRunner:
    """
    Safety Firewall Layer that validates and executes system commands.
    Prevents unauthorized shell commands using an explicit allowlist.
    """
    def __init__(self):
        self.ALLOWED_COMMANDS: List[str] = [
            "ls",
            "pwd",
            "whoami",
            "uname",
            "date",
            "uptime",
            "df",
            "ps",
        ]

    def execute_command(self, raw_command: str) -> Dict[str, Any]:
        try:
            tokens = shlex.split(raw_command.strip())
        except ValueError as error:
            return {"success": False, "error": f"Invalid command syntax: {error}"}

        if not tokens:
            return {"success": False, "error": "Empty command string provided."}

        base_binary = tokens[0]
        if base_binary not in self.ALLOWED_COMMANDS:
            return {
                "success": False,
                "error": f"Permission Denied: Command {base_binary} is not on the Saraswati safety allowlist.",
                "blocked": True
            }
        try:
            result = subprocess.run(
                tokens,
                capture_output=True,
                text=True,
                env={**os.environ, "LANG": "C", "LC_ALL": "C"},
                timeout=5
            )
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "exit_code": 0
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip(),
                    "exit_code": result.returncode
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out (5s limit)."}
        except OSError as e:
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    runner = SafeTerminalRunner()
    print("--- Saraswati Safe Terminal Driver Test ---")

    #Allowed test command
    print("\n[Test 1] Executing allowed command: 'ls -la'")
    print(runner.execute_command("ls -la"))

    #Blocked test command
    print("\n[Test2] Testing blocked command: 'rm -rf ~'")
    print(runner.execute_command("rm -rf ~"))