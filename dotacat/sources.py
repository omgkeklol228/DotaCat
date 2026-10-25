"""Дополнительные источники модов (кроме Dota2PornFx).

* Minify — моды из репозитория Minify, которые сделаны только готовыми файлами
  (files/) и списками пустышек (blacklist.txt): их можно собрать без инструментов Valve.
* Сообщество Minify — реестр Dota-Modding-Community: архивы релизов с SHA-512.

Остальные найденные площадки не подключены: на GameBanana моды под старый движок
(2014–2015), а исправления аркан из d2pfx-arcana-fixes завязаны на логику Dota 2 Mod Manager.
"""

import json
import os
import re
import time
import urllib.parse

from . import net, paths
from .store import read_json, write_json

MINIFY_REPO = "https://github.com/Egezenn/dota2-minify"
MINIFY_RAW = "https://raw.githubusercontent.com/Egezenn/dota2-minify/main/Minify/"
MINIFY_TREE_API = "https://api.github.com/repos/Egezenn/dota2-minify/git/trees/main?recursive=1"
COMMUNITY_REGISTRY = "https://raw.githubusercontent.com/Dota-Modding-Community/community/main/registry.json"
SOURCE_NAMES = {"d2pfx": "Dota2PornFx", "minify": "Minify", "community": "Сообщество Minify"}
CACHE_FILE = os.path.join(paths.CATALOG_CACHE, "sources.json")
TREE_CACHE = os.path.join(paths.CACHE_DIR, "minify", "tree.json")
REFRESH_SECONDS = 24 * 3600

MINIFY_MODS = [
    {"mod": "Dark Terrain", "cat": "terrains", "preview": True, "authors": ["robbyz512"],
     "desc": "Ради чистоты картинки: серые и тёмные плитки, линии тумана войны, без дымки, тёмная вода, "
             "свои логотипы команд и лавочники. Нужна стандартная карта."},
    {"mod": "Tree Mod", "cat": "trees", "preview": True, "authors": ["robbyz512"],
     "desc": "Превращает все деревья в маленькие круглые кусты. Нужна стандартная карта."},
    {"mod": "Remove River", "cat": "river", "preview": True, "authors": ["robbyz512"],
     "desc": "Убирает всё, что связано с рекой: покраску реки бутылками, звуки шагов по воде и брызги."},
    {"mod": "Revert Ping Sounds", "cat": "pings", "preview": False, "authors": ["Egezenn"],
     "desc": "Возвращает звуки пингов как до патча 7.39. Не сочетается с оптимизацией «Без пингов»."},
]
# в реестре нет категорий — раскладываем известные моды сами, остальные попадут в «Другое»
COMMUNITY_CATEGORIES = {"As-Is FoW": "other", "Simple Dark Terrain": "terrains", "Minimize Hero Spells": "optimization"}
# не показываем в каталоге служебные файлы Minify-модов
_SKIP_FILES = ("notes.md", "preview.jpg", "preview.png")


def make_item(source, cat, name, **extra):
    item = {
        "key": f"{source}:{cat}::{name}", "source": source, "cat": cat, "group": None, "hero": None, "slots": [],
        "name": name, "kind": "mod", "preview": None, "video": None, "file": "", "styles": [], "authors": [],
        "senders": [], "sources": [], "tags": [], "adult": False, "anime": False, "date": None, "new": False,
        "url": "", "pack": [], "description": "", "dupes": [],
    }
    item.update(extra)
    return item


def _https(url):
    return url if isinstance(url, str) and url.startswith("https://") else None


def minify_items():
    items = []
    for mod in MINIFY_MODS:
        folder = urllib.parse.quote(mod["mod"])
        items.append(make_item(
            "minify", mod["cat"], mod["mod"],
            preview=MINIFY_RAW + net.quote(f"mods/{mod['mod']}/preview.jpg") if mod["preview"] else None,
            authors=mod["authors"], sources=[f"{MINIFY_REPO}/tree/main/Minify/mods/{folder}"],
            description=mod["desc"], install={"type": "minify", "mod": mod["mod"]},
        ))
    return items


def notes_text(markdown):
    """Текст из notes.md Minify: русский раздел, если есть, иначе английский."""
    parts = re.split(r"<!--\s*lang:(\w+)\s*-->", markdown)
    sections = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    text = sections.get("ru") or sections.get("en") or markdown
    lines = []
    for line in text.splitlines():
        line = line.strip().lstrip("#>*- ").strip()
        if line and not line.startswith("[!") and not line.startswith("http"):
            lines.append(line)
    return " ".join(lines)[:500]


def _version_key(tag):
    numbers = re.findall(r"\d+", tag)
    return tuple(int(n) for n in numbers) if numbers else (-1,)


def _latest_release(entry):
    checksums = entry.get("sha512") if isinstance(entry.get("sha512"), dict) else {}
    releases = entry.get("releases") if isinstance(entry.get("releases"), dict) else {}
    tags = list(checksums) or list(releases)
    template = entry.get("asset-url")
    if not tags or not isinstance(template, str) or "{tag}" not in template:
        return None
    tag = max(tags, key=_version_key)
    url = _https(template.replace("{tag}", urllib.parse.quote(tag, safe="")))
    checksum = checksums.get(tag)
    if not url or not (isinstance(checksum, str) and re.fullmatch(r"[0-9a-fA-F]{128}", checksum)):
        return None  # без контрольной суммы не ставим
    return {"tag": tag, "url": url, "sha512": checksum.lower()}


def community_items():
    registry = json.loads(net.fetch(COMMUNITY_REGISTRY, timeout=20))
    if not isinstance(registry, list):
        raise ValueError("реестр сообщества — не список")
    items = []
    for entry in registry:
        if not isinstance(entry, dict) or entry.get("type") != "mod" or not isinstance(entry.get("name"), str):
            continue
        release = _latest_release(entry)
        if not release:
            continue
        description = ""
        if _https(entry.get("notes")):
            try:
                description = notes_text(net.fetch(entry["notes"], timeout=15).decode("utf-8", "replace"))
            except Exception:
                pass
        repo = _https(entry.get("repo")) or ""
        owner = urllib.parse.urlparse(repo).path.strip("/").split("/")[0] if repo else ""
        name = entry["name"].strip()
        items.append(make_item(
            "community", COMMUNITY_CATEGORIES.get(name, "other"), name,
            preview=_https(entry.get("preview")), authors=[owner] if owner else [],
            sources=[repo] if repo else [], description=description,
            tags=[f"v{release['tag']}"], install={"type": "community", **release},
        ))
    return items


def load(force=False, log=None):
    """Моды дополнительных источников (кэш на сутки; без сети — сохранённая копия)."""
    cached = read_json(CACHE_FILE) or {}
    fresh = time.time() - (cached.get("time") or 0) < REFRESH_SECONDS
    if fresh and not force and isinstance(cached.get("community"), list):
        community = cached["community"]
    else:
        try:
            community = community_items()
            write_json(CACHE_FILE, {"time": int(time.time()), "community": community})
        except Exception as e:
            community = cached.get("community") or []
            if log:
                log(f"Реестр сообщества Minify недоступен ({e}) — используется сохранённая копия", "warn")
    return {"minify": minify_items(), "community": community}


def minify_files(mod):
    """Файлы Minify-мода в репозитории: [(путь внутри мода, размер)]. Список кэшируется на сутки."""
    tree = None
    if os.path.isfile(TREE_CACHE) and time.time() - os.path.getmtime(TREE_CACHE) < REFRESH_SECONDS:
        tree = read_json(TREE_CACHE)
    if not isinstance(tree, list):
        data = json.loads(net.fetch(MINIFY_TREE_API, timeout=30))
        tree = [[t["path"], t.get("size", 0)] for t in data.get("tree", []) if t.get("type") == "blob"]
        write_json(TREE_CACHE, tree)
    prefix = f"Minify/mods/{mod}/"
    return [(path[len(prefix):], size) for path, size in tree
            if path.startswith(prefix) and path[len(prefix):] not in _SKIP_FILES]


def minify_file_url(mod, rel):
    return MINIFY_RAW + net.quote(f"mods/{mod}/{rel}")
