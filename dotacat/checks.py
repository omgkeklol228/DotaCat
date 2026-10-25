"""Проверка совпадений между установленными модами.

Для каждого мода собирается список файлов игры, которые он подменяет, с CRC32 содержимого
(у файлов внутри VPK CRC32 уже записан в заголовке, данные читать не нужно). Дальше:
  * одинаковые моды — одни и те же файлы с тем же содержимым (например, один мод из двух источников);
  * конфликты — общие файлы с разным содержимым: в игре будет файл мода, который выше в списке;
  * пересечения без вреда — общие файлы с одинаковым содержимым;
  * похожие по каталогу — моды из разных источников с одинаковым названием.
"""

import binascii
import itertools
import os

from . import paths, sources, vpk
from .catalog import CATALOG
from .library import MANIFEST, MANIFEST_OLD, conflict_info, installed, title

_IGNORED = {MANIFEST, MANIFEST_OLD, "manifest.json", "notes.md", "preview.jpg", "preview.png", "blacklist.txt"}
_cache = {}


def _crc_file(path):
    crc = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            crc = binascii.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def _game_path(rel, cursors):
    from .patcher import _loose_game_path  # тот же разбор путей, что и при сборке

    if cursors:
        return f"resource/cursor/{os.path.basename(rel)}"
    return _loose_game_path(rel)


def mod_files(mod):
    """{путь в игре: crc32} для мода (с кэшем по времени изменения папки)."""
    folder = os.path.join(paths.MODS_DIR, mod["folder"])
    stamp = (os.path.getmtime(folder), mod.get("installed_at"))
    cached = _cache.get(folder)
    if cached and cached[0] == stamp:
        return cached[1]
    files = {}
    cursors = mod.get("cat") == "cursors"
    for root, _, names in os.walk(folder):
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, folder).replace("\\", "/")
            low = name.lower()
            if rel in _IGNORED or low.endswith(".part"):
                continue
            if low.endswith(".vpk"):
                if vpk.is_chunk_file(low):
                    continue
                if "maps" in rel.lower().split("/")[:-1]:
                    files["maps/dota.vpk"] = _crc_file(full)
                    continue
                try:
                    with vpk.VPK(full) as pak:
                        for key, entry in pak.entries.items():
                            files.setdefault(key, entry.crc)
                except Exception:
                    continue
            else:
                game_path = _game_path(rel, cursors)
                if game_path:
                    files.setdefault(game_path.lower(), _crc_file(full))
    _cache[folder] = (stamp, files)
    return files


def _brief(mod, order):
    return {
        "id": mod["id"], "name": title(mod), "enabled": mod["enabled"], "position": order[mod["id"]] + 1,
        "source": sources.SOURCE_NAMES.get(mod.get("source") or ("local" if mod.get("local") else "d2pfx"), "свой мод"),
    }


def run():
    mods = installed()
    order = {m["id"]: index for index, m in enumerate(mods)}
    files = {m["id"]: mod_files(m) for m in mods}

    # одинаковые моды: полностью совпадающие наборы файлов
    groups = {}
    for mod in mods:
        if files[mod["id"]]:
            groups.setdefault(frozenset(files[mod["id"]].items()), []).append(mod)
    identical = [
        {"mods": [_brief(m, order) for m in group], "files": len(files[group[0]["id"]])}
        for group in groups.values() if len(group) > 1
    ]
    identical_pairs = {frozenset((a["id"], b["id"])) for g in groups.values() if len(g) > 1 for a, b in itertools.combinations(g, 2)}

    # пересечения по файлам
    overlaps = []
    for a, b in itertools.combinations(mods, 2):
        if frozenset((a["id"], b["id"])) in identical_pairs:
            continue
        fa, fb = files[a["id"]], files[b["id"]]
        shared = fa.keys() & fb.keys()
        if not shared:
            continue
        different = sorted(p for p in shared if fa[p] != fb[p])
        winner, loser = (a, b) if order[a["id"]] < order[b["id"]] else (b, a)
        overlaps.append({
            "a": _brief(winner, order), "b": _brief(loser, order),
            "shared": len(shared), "different": len(different), "same": len(shared) - len(different),
            "examples": (different or sorted(shared))[:6],
            "active": a["enabled"] and b["enabled"],
            "rule": bool(CATALOG.items) and _same_rule(a, b),
        })
    overlaps.sort(key=lambda o: (not o["active"], -o["different"], -o["shared"]))

    # похожие по названию моды из разных источников
    keys = {m.get("key"): m for m in mods if m.get("key")}
    similar, seen = [], set()
    for mod in mods:
        entry = CATALOG.get(mod.get("key") or "")
        for other_key in (entry or {}).get("dupes") or []:
            other = keys.get(other_key)
            pair = frozenset((mod["id"], other["id"])) if other else None
            if other and pair not in seen:
                seen.add(pair)
                similar.append({"a": _brief(mod, order), "b": _brief(other, order),
                                "identical": pair in identical_pairs})

    conflicts = [o for o in overlaps if o["different"] and o["active"]]
    return {
        "mods": len(mods),
        "identical": identical,
        "overlaps": overlaps,
        "similar": similar,
        "summary": {
            "identical": len(identical),
            "conflicts": len(conflicts),
            "harmless": len([o for o in overlaps if not o["different"]]),
            "similar": len(similar),
        },
    }


def _same_rule(a, b):
    """Отмечает пары, которые и так не могут быть включены вместе (один скин на героя и т.п.)."""
    from .catalog import conflicts

    return conflicts(conflict_info(a), conflict_info(b))
