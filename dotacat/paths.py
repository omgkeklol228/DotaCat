"""Пути программы.

Из исходников всё лежит рядом с кодом. В собранном DotaCat.exe интерфейс (ui/) и данные (data/)
лежат рядом с exe: при первом запуске ui/ распаковывается из exe, и дальше её можно
свободно править — пересобирать программу для смены дизайна не нужно.
"""

import hashlib
import json
import os
import shutil
import sys

from . import VERSION

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    ROOT = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLED_UI = os.path.join(getattr(sys, "_MEIPASS", ROOT), "ui")
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUNDLED_UI = None

# Интерфейс: обычные HTML/CSS/JS — правьте их и обновляйте окно (Ctrl+R).
UI_DIR = os.path.join(ROOT, "ui")
THEMES_DIR = os.path.join(UI_DIR, "themes")
USER_UI_DIR = os.path.join(UI_DIR, "user")
CUSTOM_CSS = os.path.join(UI_DIR, "custom.css")
UI_VERSION_FILE = os.path.join(UI_DIR, ".dotacat-version")
UI_FILES_MANIFEST = os.path.join(UI_DIR, ".dotacat-files.json")

# DOTACAT_DATA позволяет держать данные в другом месте (удобно для тестов).
DATA_DIR = os.path.abspath(
    os.environ.get("DOTACAT_DATA") or os.environ.get("MODDECK_DATA") or os.path.join(ROOT, "data")
)
MODS_DIR = os.path.join(DATA_DIR, "mods")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
CATALOG_CACHE = os.path.join(CACHE_DIR, "catalog")
PREVIEW_CACHE = os.path.join(CACHE_DIR, "previews")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
BROWSER_PROFILE = os.path.join(DATA_DIR, "browser")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
INSTANCE_FILE = os.path.join(DATA_DIR, "instance.json")
LOG_FILE = os.path.join(DATA_DIR, "dotacat.log")


def _user_owned(rel):
    """Темы и custom.css — файлы пользователя: при обновлении программы их не перезаписываем."""
    rel = rel.replace("\\", "/")
    return rel == "custom.css" or rel.startswith(("themes/", "user/"))


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_ui():
    """Раскладывает ui/ из exe рядом с программой; при новой версии обновляет файлы интерфейса.

    Хеши установленных файлов запоминаются в ui/.dotacat-files.json: при обновлении в
    ui/.backup-<версия> попадают только файлы, которые пользователь действительно менял."""
    if not BUNDLED_UI or not os.path.isdir(BUNDLED_UI):
        return
    try:
        with open(UI_VERSION_FILE, encoding="utf-8") as f:
            installed = f.read().strip()
    except OSError:
        installed = None
    fresh = not os.path.isfile(os.path.join(UI_DIR, "index.html"))
    if installed == VERSION and not fresh:
        return
    try:
        with open(UI_FILES_MANIFEST, encoding="utf-8") as f:
            recorded = json.load(f)
    except (OSError, ValueError):
        recorded = {}
    backup = os.path.join(UI_DIR, f".backup-{installed or 'old'}")
    manifest = {}
    for root, _, files in os.walk(BUNDLED_UI):
        for name in files:
            src = os.path.join(root, name)
            rel = os.path.relpath(src, BUNDLED_UI).replace("\\", "/")
            dst = os.path.join(UI_DIR, rel)
            src_hash = _sha256(src)
            if os.path.exists(dst):
                if _user_owned(rel):
                    continue
                dst_hash = _sha256(dst)
                if dst_hash != src_hash and recorded.get(rel) != dst_hash:
                    # файл правили вручную — копия остаётся в ui/.backup-<версия>
                    saved = os.path.join(backup, rel)
                    os.makedirs(os.path.dirname(saved), exist_ok=True)
                    shutil.copy2(dst, saved)
            if not os.path.exists(dst) or _sha256(dst) != src_hash:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            manifest[rel] = src_hash
    with open(UI_FILES_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    with open(UI_VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(VERSION)


def ensure():
    install_ui()
    for path in (DATA_DIR, MODS_DIR, CATALOG_CACHE, PREVIEW_CACHE, BACKUP_DIR, THEMES_DIR, USER_UI_DIR):
        os.makedirs(path, exist_ok=True)
