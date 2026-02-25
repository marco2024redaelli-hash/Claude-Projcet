"""
Create the Claude application data directory.

Cross-platform: works on Windows, macOS, and Linux.
  - Windows : %APPDATA%\\Claude
  - macOS   : ~/Library/Application Support/Claude
  - Linux   : ~/.config/Claude  (XDG_CONFIG_HOME respected)
"""

import os
import platform
import sys


def get_claude_appdata_dir():
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA")
        if not base:
            base = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(base, "Claude")
    elif system == "Darwin":
        return os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "Claude"
        )
    else:  # Linux and other POSIX
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
        return os.path.join(base, "Claude")


def main():
    target = get_claude_appdata_dir()
    if os.path.isdir(target):
        print(f"Directory already exists: {target}")
    else:
        os.makedirs(target, exist_ok=True)
        print(f"Created directory: {target}")
    return target


if __name__ == "__main__":
    main()
