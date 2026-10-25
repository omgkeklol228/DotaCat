"""Поиск Steam/Dota 2, аккаунтов и правка параметров запуска (localconfig.vdf)."""

import os
import re
import shutil
import subprocess
import time

from . import vdf

DOTA_APPID = "570"
STEAM_ID64_BASE = 76561197960265728
DOTA_REL = os.path.join("steamapps", "common", "dota 2 beta")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
APPS_BLOCK = ("UserLocalConfigStore", "Software", "Valve", "Steam", "apps")


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def find_steam_root():
    candidates = []
    try:
        import winreg

        for hive, key, value in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    candidates.append(os.path.normpath(winreg.QueryValueEx(handle, value)[0]))
            except OSError:
                pass
    except ImportError:
        pass
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        if os.environ.get(env):
            candidates.append(os.path.join(os.environ[env], "Steam"))
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, "steam.exe")):
            return path
    return ""


def library_folders(steam_root):
    found = [steam_root] if steam_root else []
    for rel in (("steamapps", "libraryfolders.vdf"), ("config", "libraryfolders.vdf")):
        path = os.path.join(steam_root, *rel)
        if not os.path.isfile(path):
            continue
        try:
            folders = vdf.get(vdf.parse(_read_text(path)), "libraryfolders") or {}
        except (OSError, ValueError):
            continue
        for key, value in folders.items():
            if isinstance(value, dict):
                folder = vdf.get(value, "path")
            else:
                folder = value if key.isdigit() else None
            if folder:
                found.append(os.path.normpath(folder))
    unique, seen = [], set()
    for folder in found:
        norm = os.path.normcase(folder)
        if norm not in seen:
            seen.add(norm)
            unique.append(folder)
    return unique


def is_valid_dota(path):
    return bool(path) and os.path.isfile(os.path.join(path, "game", "dota", "pak01_dir.vpk"))


def find_dota(steam_root):
    for library in library_folders(steam_root):
        path = os.path.join(library, DOTA_REL)
        if is_valid_dota(path):
            return path
    return ""


def game_language(dota_path):
    """Язык Dota 2, выбранный в Steam (appmanifest_570.acf)."""
    steamapps = os.path.dirname(os.path.dirname(dota_path))
    try:
        data = vdf.parse(_read_text(os.path.join(steamapps, f"appmanifest_{DOTA_APPID}.acf")))
    except OSError:
        return ""
    return (vdf.get(data, "AppState", "UserConfig", "language") or "").lower()


def accounts(steam_root):
    userdata = os.path.join(steam_root, "userdata") if steam_root else ""
    if not os.path.isdir(userdata):
        return []
    try:
        users = vdf.get(vdf.parse(_read_text(os.path.join(steam_root, "config", "loginusers.vdf"))), "users") or {}
    except OSError:
        users = {}
    result = []
    for name in os.listdir(userdata):
        if not name.isdigit() or name == "0":
            continue
        localconfig = localconfig_path(steam_root, name)
        if not os.path.isfile(localconfig):
            continue
        info = users.get(str(int(name) + STEAM_ID64_BASE)) or {}
        persona = vdf.get(info, "PersonaName") if isinstance(info, dict) else None
        if not persona:
            try:
                with open(localconfig, encoding="utf-8", errors="replace") as f:
                    match = re.search(r'"PersonaName"\s+"([^"]*)"', f.read(300_000))
                persona = match.group(1) if match else ""
            except OSError:
                persona = ""
        result.append({
            "id": name,
            "name": persona or name,
            "login": (vdf.get(info, "AccountName") if isinstance(info, dict) else "") or "",
            "recent": str(vdf.get(info, "MostRecent") if isinstance(info, dict) else "0") == "1",
            "mtime": os.path.getmtime(localconfig),
        })
    result.sort(key=lambda acc: (not acc["recent"], -acc["mtime"]))
    return result


def localconfig_path(steam_root, account):
    return os.path.join(steam_root, "userdata", str(account), "config", "localconfig.vdf")


def get_launch_options(steam_root, account):
    path = localconfig_path(steam_root, account)
    if not os.path.isfile(path):
        return None
    return vdf.get_value(_read_text(path), APPS_BLOCK + (DOTA_APPID,), "LaunchOptions") or ""


def set_launch_options(steam_root, account, transform, backup_dir):
    """Меняет параметры запуска Dota 2: new = transform(old). Steam должен быть закрыт."""
    path = localconfig_path(steam_root, account)
    with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        text = f.read()
    old = vdf.get_value(text, APPS_BLOCK + (DOTA_APPID,), "LaunchOptions") or ""
    new = transform(old)
    if new == old:
        return old, new
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(path, os.path.join(backup_dir, f"localconfig-{account}-{time.strftime('%Y%m%d-%H%M%S')}.vdf"))
    text = vdf.set_value(text, APPS_BLOCK + (DOTA_APPID,), "LaunchOptions", new)
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(text)
    return old, new


def process_running(image):
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/NH", "/FO", "CSV"],
            capture_output=True, encoding="oem", errors="replace", timeout=15, creationflags=NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return f'"{image.lower()}"' in (result.stdout or "").lower()


def steam_running():
    return process_running("steam.exe")


def dota_running():
    return process_running("dota2.exe")


def shutdown_steam(steam_root, timeout=45):
    subprocess.Popen([os.path.join(steam_root, "steam.exe"), "-shutdown"], creationflags=NO_WINDOW)
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(1.5)
        if not steam_running():
            time.sleep(1.0)
            return True
    return False


def start_steam(steam_root):
    subprocess.Popen([os.path.join(steam_root, "steam.exe")], creationflags=NO_WINDOW)


def launch_dota():
    os.startfile(f"steam://rungameid/{DOTA_APPID}")
