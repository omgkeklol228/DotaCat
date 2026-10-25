"""Каталог Dota2PornFx: загрузка (как в Minify — из ветки data), кэш и плоский список модов."""

import gzip
import json
import os
import re
import threading
import time

from . import net, paths, sources
from .store import config, read_json, state, write_json

REPO_RAW = "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/"
DATA_URL = REPO_RAW + "data/data/"
MAIN_URL = REPO_RAW + "main/"
# официальное зеркало каталога (те же пути) — запасной вариант, если GitHub не отдал файл
MIRROR_URL = "https://huggingface.co/datasets/hrdq/Dota2PornFx/resolve/main/"
SITE_URL = "https://h6rd.github.io/Dota2PornFxWeb/"
REPO_URL = "https://github.com/h6rd/Dota2PornFxWeb"
CREDITS_URL = REPO_URL + "#credits"
REFRESH_SECONDS = 24 * 3600

# Разделы-гайды и ссылки: на сайте они ставятся вручную, здесь — кнопка «Открыть».
LINK_CATEGORIES = {"guides", "sites", "news", "tools", "fonts"}
HIDDEN_CATEGORIES = {"news"}
# Как в Minify: моды этих категорий по умолчанию перекрывают остальные.
HIGH_PRIORITY = {"trees", "river", "shaders", "herofx", "ranged-attack", "hero-items", "optimization"}
# Включённым может быть только один мод из категории (список из манифеста плагина Minify)…
EXCLUSIVE_CATEGORIES = {
    "ancient", "couriers", "cursors", "emblems", "high-five", "item-icons", "music", "pedestal",
    "ranged-attack", "ranks", "river", "roshan", "shaders", "ti-bp-effects", "tormentor",
    "versus-screens", "wards",
}
# …или один мод из группы: один скин на героя, крипы света/тьмы, башни, дагон и т.п.
GROUP_EXCLUSIVE = {"creeps", "creep-deny", "towers", "item-effects", "heroes", "hero-icons"}

# Разделы, где моды привязаны к герою: в интерфейсе для них есть выбор героя.
HERO_CATEGORIES = {"heroes", "hero-items", "hero-sounds", "herofx", "hero-icons"}
# Имя героя на сайте → внутреннее имя Valve (для портретов с cdn.cloudflare.steamstatic.com).
HERO_SLUGS = {
    "Anti-Mage": "antimage", "Axe": "axe", "Bane": "bane", "Bloodseeker": "bloodseeker",
    "Crystal Maiden": "crystal_maiden", "Drow Ranger": "drow_ranger", "Earthshaker": "earthshaker",
    "Juggernaut": "juggernaut", "Mirana": "mirana", "Morphling": "morphling", "Shadow Fiend": "nevermore",
    "Phantom Lancer": "phantom_lancer", "Puck": "puck", "Pudge": "pudge", "Razor": "razor",
    "Sand King": "sand_king", "Storm Spirit": "storm_spirit", "Sven": "sven", "Tiny": "tiny",
    "Vengeful Spirit": "vengefulspirit", "Windranger": "windrunner", "Zeus": "zuus", "Kunkka": "kunkka",
    "Lina": "lina", "Lion": "lion", "Shadow Shaman": "shadow_shaman", "Slardar": "slardar",
    "Tidehunter": "tidehunter", "Witch Doctor": "witch_doctor", "Lich": "lich", "Riki": "riki",
    "Enigma": "enigma", "Tinker": "tinker", "Sniper": "sniper", "Necrophos": "necrolyte",
    "Warlock": "warlock", "Beastmaster": "beastmaster", "Queen of Pain": "queenofpain",
    "Venomancer": "venomancer", "Faceless Void": "faceless_void", "Wraith King": "skeleton_king",
    "Death Prophet": "death_prophet", "Phantom Assassin": "phantom_assassin", "Pugna": "pugna",
    "Templar Assassin": "templar_assassin", "Viper": "viper", "Luna": "luna", "Dragon Knight": "dragon_knight",
    "Dazzle": "dazzle", "Clockwerk": "rattletrap", "Leshrac": "leshrac", "Natures Prophet": "furion",
    "Lifestealer": "life_stealer", "Dark Seer": "dark_seer", "Clinkz": "clinkz", "Omniknight": "omniknight",
    "Enchantress": "enchantress", "Huskar": "huskar", "Night Stalker": "night_stalker",
    "Broodmother": "broodmother", "Bounty Hunter": "bounty_hunter", "Weaver": "weaver", "Jakiro": "jakiro",
    "Batrider": "batrider", "Chen": "chen", "Spectre": "spectre", "Ancient Apparition": "ancient_apparition",
    "Doom": "doom_bringer", "Ursa": "ursa", "Spirit Breaker": "spirit_breaker", "Gyrocopter": "gyrocopter",
    "Alchemist": "alchemist", "Invoker": "invoker", "Silencer": "silencer",
    "Outworld Destroyer": "obsidian_destroyer", "Lycan": "lycan", "Brewmaster": "brewmaster",
    "Shadow Demon": "shadow_demon", "Lone Druid": "lone_druid", "Chaos Knight": "chaos_knight",
    "Meepo": "meepo", "Treant Protector": "treant", "Ogre Magi": "ogre_magi", "Undying": "undying",
    "Rubick": "rubick", "Disruptor": "disruptor", "Nyx Assassin": "nyx_assassin", "Naga Siren": "naga_siren",
    "Keeper of the Light": "keeper_of_the_light", "Io": "wisp", "Visage": "visage", "Slark": "slark",
    "Medusa": "medusa", "Troll Warlord": "troll_warlord", "Centaur": "centaur", "Magnus": "magnataur",
    "Timbersaw": "shredder", "Bristleback": "bristleback", "Tusk": "tusk", "Skywrath Mage": "skywrath_mage",
    "Abaddon": "abaddon", "Elder Titan": "elder_titan", "Legion Commander": "legion_commander",
    "Techies": "techies", "Ember Spirit": "ember_spirit", "Earth Spirit": "earth_spirit",
    "Underlord": "abyssal_underlord", "Terrorblade": "terrorblade", "Phoenix": "phoenix", "Oracle": "oracle",
    "Winter Wyvern": "winter_wyvern", "Arc Warden": "arc_warden", "Monkey King": "monkey_king",
    "Dark Willow": "dark_willow", "Pangolier": "pangolier", "Grimstroke": "grimstroke", "Hoodwink": "hoodwink",
    "Void Spirit": "void_spirit", "Snapfire": "snapfire", "Mars": "mars", "Dawnbreaker": "dawnbreaker",
    "Marci": "marci", "Primal Beast": "primal_beast", "Muerta": "muerta", "Ringmaster": "ringmaster",
    "Kez": "kez", "Largo": "largo",
}
# Другие написания имён в названиях модов.
HERO_ALIASES = [
    (r"\bkotl\b", "Keeper of the Light"), (r"\bqop\b", "Queen of Pain"),
    (r"\bnature'?s?\s+prophet\b", "Natures Prophet"), (r"\bphantom\s+assas+in\b", "Phantom Assassin"),
    (r"\btreant\b", "Treant Protector"), (r"\banti\s?mage\b", "Anti-Mage"), (r"\bwindrunner\b", "Windranger"),
    (r"\boutworld\s+devourer\b", "Outworld Destroyer"), (r"\bnecrolyte\b", "Necrophos"), (r"\bwisp\b", "Io"),
    (r"\blife\s+stealer\b", "Lifestealer"),
]
# Моды, в названии которых нет имени героя (герой определён по файлам внутри VPK).
HERO_OVERRIDES = {"Cosmic Cartographer": "Marci"}
HERO_PORTRAIT_URL = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{slug}.png"


def mod_key(cat, name):
    return f"{cat}::{name}"


def mod_id(cat, name, label=None):
    key = mod_key(cat, name)
    return f"{key}::{label}" if label else key


def preview_url(cat, preview):
    if not preview:
        return None
    if preview.startswith(("http://", "https://")):
        return preview
    path = preview if preview.startswith("assets/") else f"assets/previews/{cat}/{preview}"
    return "/cache?p=" + net.quote(path)


def file_url(cat, filename):
    if filename.startswith(("http://", "https://")):
        return filename
    return MAIN_URL + net.quote(f"assets/files/{cat}/{filename}")


def mirror_url(url):
    """Тот же файл на зеркале Hugging Face (или None, если это не файл каталога)."""
    return MIRROR_URL + url[len(MAIN_URL):] if url.startswith(MAIN_URL) else None


_NAME_STOP = {"minify", "mod", "mods", "the", "by", "v1", "v2", "v3"}


def name_tokens(name):
    return frozenset(w for w in re.findall(r"[a-zа-яё0-9]+", name.lower()) if w not in _NAME_STOP)


def same_mod_name(a, b):
    """Похожи ли названия модов из разных источников («Dark Terrain» и «Dark Terrain Minify»)."""
    ta, tb = a.get("_tokens") or name_tokens(a["name"]), b.get("_tokens") or name_tokens(b["name"])
    if not ta or ta != tb:
        return False
    return len(ta) >= 2 or a.get("cat") == b.get("cat")


def conflicts(a, b):
    """Могут ли два мода (словари с key, cat, group, slots) работать одновременно — False, если могут."""
    if a.get("key") and a.get("key") == b.get("key"):
        return True  # разные стили одного мода
    cat = a.get("cat")
    if cat != b.get("cat"):
        return False
    if cat in EXCLUSIVE_CATEGORIES:
        return True
    if cat in GROUP_EXCLUSIVE:
        return bool(a.get("group")) and a.get("group") == b.get("group")
    if cat == "hero-items":
        # предметы одного героя конфликтуют, только если заменяют один и тот же слот
        return a.get("group") == b.get("group") and bool(set(a.get("slots") or []) & set(b.get("slots") or []))
    return False


class HeroMatcher:
    """Определяет героя по названию мода — так же, как сайт: побеждает самое раннее совпадение."""

    def __init__(self, names):
        self.names = list(names)
        patterns = []
        for name in self.names:
            # у «Kez» на сайте нет границ слова (Kezzer и т.п.)
            body = re.escape(name) if name == "Kez" else rf"\b{re.escape(name)}\b"
            patterns.append((re.compile(body, re.IGNORECASE), name))
        known = set(self.names)
        patterns += [(re.compile(rx, re.IGNORECASE), name) for rx, name in HERO_ALIASES if name in known]
        self.patterns = patterns

    def __call__(self, text):
        if not text:
            return None
        if text in HERO_OVERRIDES:
            return HERO_OVERRIDES[text]
        best = None
        for regex, name in self.patterns:
            match = regex.search(text)
            if match and (best is None or match.start() < best[0] or (match.start() == best[0] and len(match.group()) > best[1])):
                best = (match.start(), len(match.group()), name)
        return best[2] if best else None


def _is_mod_file(filename):
    return filename.lower().split("?")[0].endswith((".vpk", ".zip"))


class Catalog:
    def __init__(self):
        self.lock = threading.RLock()
        self.items = []
        self.by_key = {}
        self.categories = []
        self.heroes = []
        self.hashes = {}
        self.refreshed = 0
        self._hero_of = HeroMatcher(HERO_SLUGS)
        self._slot_tags = set()

    @staticmethod
    def _fetch(name):
        try:
            return json.loads(gzip.decompress(net.fetch(DATA_URL + name + ".gz")))
        except Exception:
            return json.loads(net.fetch(MAIN_URL + "assets/data/" + name))

    def load(self, force=False, log=None):
        with self.lock:
            mods_cache = os.path.join(paths.CATALOG_CACHE, "mods.json")
            consts_cache = os.path.join(paths.CATALOG_CACHE, "constants.json")
            have_cache = os.path.isfile(mods_cache) and os.path.isfile(consts_cache)
            stale = time.time() - (state.get("catalog_refreshed") or 0) > REFRESH_SECONDS
            hashes_cache = os.path.join(paths.CATALOG_CACHE, "mod-hashes.json")
            mods = consts = None
            refresh = force or not have_cache or (stale and config.get("auto_refresh"))
            if refresh:
                try:
                    mods, consts = self._fetch("mods.json"), self._fetch("constants.json")
                    write_json(mods_cache, mods)
                    write_json(consts_cache, consts)
                    state.set("catalog_refreshed", int(time.time()))
                    if log:
                        log("Каталог Dota2PornFx обновлён", "done" if force else "success")
                except Exception as e:
                    mods = consts = None
                    if log:
                        log(f"Не удалось скачать каталог ({e}) — используется сохранённая копия", "warn")
            if mods is None:
                mods, consts = read_json(mods_cache), read_json(consts_cache)
                if not isinstance(mods, dict) or not isinstance(consts, dict):
                    raise RuntimeError("Каталог недоступен: нет интернета и нет сохранённой копии.")
            # SHA-256 файлов каталога: по ним проверяется, что мод скачался целым
            if refresh or not os.path.isfile(hashes_cache):
                try:
                    write_json(hashes_cache, json.loads(net.fetch(MAIN_URL + "assets/data/mod-hashes.json")))
                except Exception:
                    pass
            hashes = read_json(hashes_cache)
            self.hashes = hashes if isinstance(hashes, dict) else {}
            self._build(mods, consts)
            enabled = {"minify": True, "community": True, **(config.get("sources") or {})}
            extra = sources.load(force=force, log=log)
            self._add_sources([it for src, items in extra.items() if enabled.get(src) for it in items])
            self.refreshed = state.get("catalog_refreshed") or 0

    def expected_sha256(self, cat, filename):
        return self.hashes.get(f"{cat}/{filename}")

    def ensure(self):
        if not self.items:
            self.load()

    def get(self, key):
        return self.by_key.get(key)

    def find_by_name(self, name):
        low = name.strip().lower()
        return next((it for it in self.items if it["kind"] == "mod" and it["name"].lower() == low), None)

    def public(self):
        with self.lock:
            return {
                "categories": self.categories,
                "items": self.items,
                "heroes": self.heroes,
                "refreshed": self.refreshed,
                "site": SITE_URL,
                "repo": REPO_URL,
                "credits": CREDITS_URL,
            }

    # --- приведение mods.json к плоскому списку ---

    def _build(self, mods, consts):
        recent = {(r.get("category"), r.get("name")) for r in mods.get("recentlyAddedMods") or [] if isinstance(r, dict)}
        data = mods.get("modsData") or {}
        translations = consts.get("translations") or {}
        order = [c for c in consts.get("categories") or [] if isinstance(c, dict) and c.get("id")]
        known = {c["id"] for c in order}
        order += [{"id": cid} for cid in data if cid not in known]

        hero_names = [h for h in consts.get("HEROES_LIST") or [] if isinstance(h, str)] or list(HERO_SLUGS)
        self._hero_of = HeroMatcher(hero_names)
        self._slot_tags = set((consts.get("slotTags") or {}).get("hero-items") or [])

        items, categories = [], []
        for cat in order:
            cid = cat["id"]
            if cat.get("hidden") or cid in HIDDEN_CATEGORIES:
                continue
            entries = []
            self._walk(data.get(cid), cid, None, entries, recent)
            if not entries:
                continue
            groups = []
            for entry in entries:
                if entry["group"] and entry["group"] not in groups:
                    groups.append(entry["group"])
            name_en = translations.get(cid)
            if cid in HERO_CATEGORIES:
                groups.sort()
            categories.append({
                "id": cid,
                "emoji": cat.get("emoji") or "",
                "name_en": name_en if isinstance(name_en, str) else cid.replace("-", " ").title(),
                "kind": "pack" if cid == "packs" else ("link" if cid in LINK_CATEGORIES else "mod"),
                "count": len(entries),
                "groups": groups,
                "heroes": cid in HERO_CATEGORIES,
            })
            items.extend(entries)
        for index, item in enumerate(items):
            item["i"] = index
        self.items = items
        self.by_key = {}
        for item in items:
            self.by_key.setdefault(item["key"], item)
        self.categories = categories
        self.heroes = [
            {"name": name, "slug": HERO_SLUGS.get(name, ""),
             "portrait": HERO_PORTRAIT_URL.format(slug=HERO_SLUGS[name]) if name in HERO_SLUGS else None}
            for name in sorted(hero_names)
        ]

    def hero_of(self, text):
        return self._hero_of(text)

    def _add_sources(self, extra):
        """Добавляет моды других источников и отмечает похожие на моды из разных источников."""
        cats = {c["id"]: c for c in self.categories}
        for item in extra:
            cat = cats.get(item["cat"])
            if cat is None:
                cat = cats[item["cat"]] = {"id": item["cat"], "emoji": "🧩", "name_en": item["cat"].title(),
                                           "kind": "mod", "count": 0, "groups": [], "heroes": False}
                self.categories.append(cat)
            cat["count"] += 1
            item = dict(item, dupes=[])
            self.items.append(item)
            self.by_key.setdefault(item["key"], item)
        mods = [it for it in self.items if it["kind"] == "mod"]
        for item in mods:
            item["_tokens"] = name_tokens(item["name"])
        outsiders = [it for it in mods if it.get("source") != "d2pfx"]
        for item in outsiders:
            for other in mods:
                if other is not item and other.get("source") != item.get("source") and same_mod_name(item, other):
                    if other["key"] not in item["dupes"]:
                        item["dupes"].append(other["key"])
                    if item["key"] not in other["dupes"]:
                        other["dupes"].append(item["key"])
        for item in mods:
            item.pop("_tokens", None)
        for index, item in enumerate(self.items):
            item["i"] = index

    def _walk(self, node, cid, group, out, recent):
        if isinstance(node, list):
            for child in node:
                self._walk(child, cid, group, out, recent)
        elif isinstance(node, dict):
            mods = node.get("mods")
            if node.get("type") == "pack" or (cid == "packs" and "name" in node):
                out.append(self._entry(node, cid, group, recent))
            elif "groups" in node:
                self._walk(node["groups"], cid, group, out, recent)
            elif isinstance(mods, list) and "name" in node:
                self._walk(mods, cid, node.get("name"), out, recent)
            elif "name" in node:
                out.append(self._entry(node, cid, group, recent))

    def _entry(self, m, cid, group, recent):
        links = [l for l in m.get("links") or [] if isinstance(l, dict)]

        def link_names(*types):
            return [l.get("name") or l.get("url") for l in links if l.get("type") in types and (l.get("name") or l.get("url"))]

        tags = m.get("tags") or {}
        if isinstance(tags, dict):
            tag_list = [str(k) for k, v in tags.items() if v]
        elif isinstance(tags, list):
            tag_list = [str(t) for t in tags]
        else:
            tag_list = []
        lowered = {t.lower() for t in tag_list}

        name = str(m.get("name") or "")
        file = str(m.get("file") or "")
        styles = []
        for style in m.get("styles") or []:
            if isinstance(style, dict) and style.get("file"):
                styles.append({
                    # у первого стиля на сайте часто пустое имя
                    "label": str(style.get("label") or ("Обычный" if not styles else f"Style {len(styles) + 1}")),
                    "color": str(style.get("color") or ""),
                    "preview": preview_url(cid, style.get("preview") or m.get("preview")),
                    "file": str(style["file"]),
                })

        if m.get("type") == "pack" or cid == "packs":
            kind = "pack"
        elif cid in LINK_CATEGORIES or m.get("type") == "guide" or not (styles or _is_mod_file(file)):
            kind = "link"
        else:
            kind = "mod"

        hero = None
        if cid in HERO_CATEGORIES:
            # у предметов герой — это группа на сайте, у остальных — имя внутри названия мода
            hero = (self._hero_of(group) if group else None) or self._hero_of(name)
            if cid == "hero-items" and not hero:
                hero = group
            group = hero

        video = next((l.get("url") for l in links if l.get("type") == "preview" and l.get("url")), None)
        meta = m.get("meta") if isinstance(m.get("meta"), dict) else {}
        return {
            "key": mod_key(cid, name),
            "cat": cid,
            "group": group,
            "hero": hero,
            "slots": [t for t in tag_list if t in self._slot_tags] if cid == "hero-items" else [],
            "name": name,
            "kind": kind,
            "preview": preview_url(cid, m.get("preview")),
            "video": preview_url(cid, video) if video else None,
            "file": file,
            "styles": styles,
            "authors": link_names("author", "modded"),
            "senders": link_names("sender"),
            "sources": [l["url"] for l in links if l.get("type") == "source" and str(l.get("url", "")).startswith("http")],
            "tags": tag_list,
            "adult": "adult" in lowered,
            "anime": "anime" in lowered,
            "date": meta.get("date"),
            "new": (cid, name) in recent,
            "url": file if file.startswith(("http://", "https://")) and kind == "link" else "",
            "pack": [str(x) for x in m.get("mods") or [] if isinstance(x, str)] if kind == "pack" else [],
            "description": str(m.get("description") or ""),
            "source": "d2pfx",
            "dupes": [],
        }


CATALOG = Catalog()
