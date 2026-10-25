"""Окно программы: Edge/Chrome в режиме приложения (без вкладок и адресной строки)."""

import os
import shutil
import subprocess
import webbrowser

from . import paths

_BROWSERS = (
    r"Microsoft\Edge\Application\msedge.exe",
    r"Google\Chrome\Application\chrome.exe",
    r"BraveSoftware\Brave-Browser\Application\brave.exe",
    r"Chromium\Application\chrome.exe",
)


def find_browser():
    roots = [os.environ.get(name) for name in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    for rel in _BROWSERS:
        for root in roots:
            if root and os.path.isfile(os.path.join(root, rel)):
                return os.path.join(root, rel)
    for name in ("msedge", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def open_window(url):
    """Возвращает процесс окна или None, если пришлось открыть обычный браузер."""
    exe = find_browser()
    if exe:
        args = [
            exe,
            f"--app={url}",
            f"--user-data-dir={paths.BROWSER_PROFILE}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=Translate",
            "--window-size=1400,900",
        ]
        try:
            return subprocess.Popen(args)
        except OSError:
            pass
    webbrowser.open(url)
    return None
