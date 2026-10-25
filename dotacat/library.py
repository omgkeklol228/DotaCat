"""Установленные моды: скачивание, распаковка, включение, конфликты и порядок."""

import hashlib
import os
import shutil
import stat
import time
import urllib.parse
import uuid
import zipfile

from . import catalog, net, paths, sources
from .catalog import CATALOG
from .store import read_json, state, write_json

MANIFEST = "dotacat.json"
MANIFEST_OLD = "moddeck.json"  # так манифест назывался до переименования в DotaCat
_INVALID = '<>:"/\\|?*'


def sanitize(name):
    cleaned = "".join("_" if c in _INVALID or ord(c) < 32 else c for c in name).strip().rstrip(". ")
    return cleaned[:120] or "mod"


def title(mod):
    label = mod.get("label")
    return f"{mod.get('name')} ({label})" if label else str(mod.get("name"))


def _rmtree(path):
    def on_error(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if os.path.isdir(path):
        shutil.rmtree(path, onexc=on_error)


def _folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def _has_vpk(path):
    return any(name.lower().endswith(".vpk") for _, _, files in os.walk(path) for name in files)


def extract_zip(archive, dest):
    """Распаковка с защитой от путей вида ../../ (zip slip)."""
    dest = os.path.abspath(dest)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = os.path.abspath(os.path.join(dest, info.filename))
            if not target.startswith(dest + os.sep):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out, 1024 * 1024)


def _mod_dirs():
    if not os.path.isdir(paths.MODS_DIR):
        return []
    return [
        name for name in sorted(os.listdir(paths.MODS_DIR))
        if not name.startswith(".") and os.path.isdir(os.path.join(paths.MODS_DIR, name))
    ]


def read_manifests():
    """{id: манифест} для всех папок data/mods. Папка без манифеста — «свой мод»."""
    result = {}
    for folder in _mod_dirs():
        path = os.path.join(paths.MODS_DIR, folder)
        manifest = read_json(os.path.join(path, MANIFEST)) or read_json(os.path.join(path, MANIFEST_OLD))
        if not isinstance(manifest, dict) or not manifest.get("id"):
            manifest = {"id": f"local::{folder}", "cat": "local", "name": folder, "local": True, "size": _folder_size(path)}
        manifest["folder"] = folder
        result.setdefault(manifest["id"], manifest)
    return result


def installed():
    """Список установленных модов в порядке приоритета (верхний перекрывает нижние)."""
    manifests = read_manifests()
    snap = state.snapshot()
    enabled = snap.get("enabled") or {}
    order = [mid for mid in snap.get("order") or [] if mid in manifests]
    order += [mid for mid in manifests if mid not in order]
    result = []
    for mid in order:
        mod = dict(manifests[mid])
        mod["enabled"] = bool(enabled.get(mid, True))
        entry = CATALOG.get(mod.get("key") or catalog.mod_key(mod.get("cat", ""), mod.get("name", "")))
        mod["update"] = bool(
            entry and entry.get("date") and mod.get("source_date") and entry["date"] > mod["source_date"]
        )
        if entry:
            mod["group"] = entry.get("group")
            mod["hero"] = entry.get("hero")
            if not mod.get("preview"):
                mod["preview"] = entry.get("preview")
        result.append(mod)
    return result


def resolve(key, label=None):
    """(entry, style, id) для мода каталога; без label берётся первый стиль."""
    entry = CATALOG.get(key)
    if not entry:
        raise RuntimeError(f"Мод не найден в каталоге: {key}")
    style = None
    if entry["styles"]:
        style = next((s for s in entry["styles"] if s["label"] == label), entry["styles"][0])
    # id = ключ каталога (у модов других источников в нём есть префикс источника) + стиль
    label = style["label"] if style else None
    return entry, style, f"{entry['key']}::{label}" if label else entry["key"]


def _insert_position(order, cat, manifests):
    if cat in catalog.HIGH_PRIORITY:
        return 0
    position = 0
    for index, mid in enumerate(order):
        if (manifests.get(mid) or {}).get("cat") in catalog.HIGH_PRIORITY:
            position = index + 1
        else:
            break
    return position


def conflict_info(manifest):
    """Данные для проверки конфликтов; герой и слоты берутся из свежего каталога."""
    info = {k: manifest.get(k) for k in ("id", "key", "cat", "group", "slots")}
    entry = CATALOG.get(manifest.get("key") or "")
    if entry:
        info["group"] = entry.get("group")
        info["slots"] = entry.get("slots")
    return info


def _resolve_conflicts(data, manifest, manifests):
    """Выключает моды, которые не могут работать вместе с manifest. Возвращает [(id, название)]."""
    mine = conflict_info(manifest)
    enabled = data.setdefault("enabled", {})
    disabled = []
    for other_id, other in manifests.items():
        if other_id == manifest["id"] or not enabled.get(other_id, True):
            continue
        if catalog.conflicts(mine, conflict_info(other)):
            enabled[other_id] = False
            disabled.append((other_id, title(other)))
    return disabled


def would_replace(key, label=None):
    """Какие включённые моды выключатся, если поставить этот (для вопроса «заменить?»)."""
    CATALOG.ensure()
    entry, style, mid = resolve(key, label)
    candidate = {"id": mid, "key": entry["key"], "cat": entry["cat"], "group": entry.get("group"), "slots": entry.get("slots")}
    enabled = state.get("enabled") or {}
    dupes = set(entry.get("dupes") or [])
    replace, similar = [], []
    for other_id, other in read_manifests().items():
        if other_id == mid:
            continue
        if enabled.get(other_id, True) and catalog.conflicts(candidate, conflict_info(other)):
            replace.append({"id": other_id, "name": title(other)})
        elif other.get("key") in dupes:
            source = sources.SOURCE_NAMES.get(other.get("source") or "d2pfx", "")
            similar.append({"id": other_id, "name": title(other), "source": source})
    return {"replace": replace, "similar": similar}


def normalize_conflicts(ctx):
    """Если включены несовместимые моды (например, два скина на героя), оставляет верхний в списке."""
    mods = [m for m in installed() if m["enabled"]]
    kept, disabled = [], []
    for mod in mods:
        info = conflict_info(mod)
        winner = next((k for k in kept if catalog.conflicts(info, conflict_info(k))), None)
        if winner:
            disabled.append((mod, winner))
        else:
            kept.append(mod)
    if not disabled:
        return
    with state.edit() as data:
        for mod, _ in disabled:
            data.setdefault("enabled", {})[mod["id"]] = False
    for mod, winner in disabled:
        ctx.log(f"Выключен «{title(mod)}»: конфликтует с «{title(winner)}», который выше в списке", "warn")


def _sha(path, algorithm):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _has_game_files(folder):
    return any(name.lower().endswith("_c") for _, _, files in os.walk(folder) for name in files)


def _unpack(dest, tmp):
    if dest.lower().endswith(".zip"):
        extract_zip(dest, tmp)
        os.remove(dest)


def _download_d2pfx(ctx, entry, filename, tmp, name):
    """Файл из каталога D2PFX: GitHub, при сбое или битом файле — зеркало Hugging Face."""
    url = catalog.file_url(entry["cat"], filename)
    local_name = sanitize(urllib.parse.unquote(url.split("?")[0].rsplit("/", 1)[-1])) or "mod.vpk"
    dest = os.path.join(tmp, local_name)
    expected = CATALOG.expected_sha256(entry["cat"], filename)
    candidates = [u for u in (url, catalog.mirror_url(url)) if u]
    last_error = None
    for attempt, candidate in enumerate(candidates):
        if attempt:
            ctx.log("  пробую зеркало Hugging Face…", "warn")
        try:
            net.download(candidate, dest, progress=lambda done, total: ctx.progress(done, total, name))
        except Exception as e:
            last_error = e
            continue
        if expected and _sha(dest, "sha256") != expected:
            last_error = RuntimeError("файл не совпадает с контрольной суммой каталога")
            os.remove(dest)
            continue
        ctx.log("  контрольная сумма совпала с каталогом" if expected else "  в каталоге нет контрольной суммы для этого файла")
        _unpack(dest, tmp)
        return candidate
    raise RuntimeError(f"Не удалось скачать «{name}»: {last_error}")


def _download_community(ctx, entry, tmp, name):
    """Релиз из реестра сообщества Minify — только с совпавшим SHA-512."""
    info = entry.get("install") or {}
    dest = os.path.join(tmp, "release.zip")
    net.download(info["url"], dest, progress=lambda done, total: ctx.progress(done, total, name))
    if _sha(dest, "sha512") != info.get("sha512"):
        raise RuntimeError("архив не совпадает с контрольной суммой из реестра — установка отменена")
    ctx.log(f"  SHA-512 совпал с реестром (версия {info.get('tag')})")
    _unpack(dest, tmp)
    return info["url"]


def _download_minify(ctx, entry, tmp, name):
    """Мод из репозитория Minify: файлы files/ и blacklist.txt по одному."""
    mod = (entry.get("install") or {}).get("mod") or entry["name"]
    files = sources.minify_files(mod)
    if not files:
        raise RuntimeError(f"В репозитории Minify нет мода «{mod}»")
    total = sum(size for _, size in files) or 1
    done = 0
    for rel, size in files:
        target = os.path.abspath(os.path.join(tmp, *rel.split("/")))
        if not target.startswith(os.path.abspath(tmp) + os.sep):
            continue
        net.download(sources.minify_file_url(mod, rel), target)
        done += size
        ctx.progress(done, total, name)
    ctx.log(f"  скачано файлов: {len(files)}")
    return f"{sources.MINIFY_REPO}/tree/main/Minify/mods/{urllib.parse.quote(mod)}"


def install(ctx, key, label=None, remove_replaced=False):
    CATALOG.ensure()
    entry, style, mid = resolve(key, label)
    if entry["kind"] != "mod":
        raise RuntimeError(f"«{entry['name']}» нельзя установить автоматически — откройте его на сайте.")
    source = entry.get("source") or "d2pfx"
    filename = style["file"] if style else entry["file"]
    label = style["label"] if style else None
    if source == "d2pfx" and not filename:
        raise RuntimeError(f"У «{entry['name']}» нет файла для скачивания.")
    name = title({"name": entry["name"], "label": label})
    manifests = read_manifests()
    prefix = "" if source == "d2pfx" else f"{source} "
    folder = manifests[mid]["folder"] if mid in manifests else sanitize(f"{prefix}{entry['cat']} - {name}")

    tmp = os.path.join(paths.MODS_DIR, f".tmp-{uuid.uuid4().hex[:8]}")
    os.makedirs(tmp)
    try:
        ctx.log(f"Скачиваю «{name}» ({sources.SOURCE_NAMES.get(source, source)})…", "step")
        if source == "minify":
            url = _download_minify(ctx, entry, tmp, name)
        elif source == "community":
            url = _download_community(ctx, entry, tmp, name)
        else:
            url = _download_d2pfx(ctx, entry, filename, tmp, name)
        if not _has_vpk(tmp) and not _has_game_files(tmp) and entry["cat"] != "cursors":
            ctx.log(f"  в «{name}» нет VPK — будут взяты только файлы игры (materials, particles…)", "warn")
        manifest = {
            "id": mid,
            "key": entry["key"],
            "cat": entry["cat"],
            "group": entry.get("group"),
            "hero": entry.get("hero"),
            "slots": entry.get("slots") or [],
            "name": entry["name"],
            "label": label,
            "source": source,
            "file": filename,
            "url": url,
            "preview": (style or entry).get("preview"),
            "authors": entry["authors"],
            "senders": entry["senders"],
            "sources": entry["sources"],
            "tags": entry["tags"],
            "source_date": entry.get("date"),
            "installed_at": int(time.time()),
            "size": _folder_size(tmp),
        }
        write_json(os.path.join(tmp, MANIFEST), manifest)
        final = os.path.join(paths.MODS_DIR, folder)
        _rmtree(final)
        os.replace(tmp, final)
    except BaseException:
        _rmtree(tmp)
        raise

    manifest["folder"] = folder
    with state.edit() as data:
        order = data.setdefault("order", [])
        enabled = data.setdefault("enabled", {})
        if mid not in order:
            order.insert(_insert_position(order, entry["cat"], manifests), mid)
            enabled[mid] = True
        disabled = _resolve_conflicts(data, manifest, manifests) if enabled.get(mid, True) else []
    ctx.log(f"Установлен «{name}»", "success")
    for other_id, other in disabled:
        if remove_replaced:
            uninstall(ctx, other_id)
        else:
            ctx.log(f"  выключен «{other}» — вместе они не работают", "warn")
    return mid


def install_pack(ctx, key):
    CATALOG.ensure()
    pack = CATALOG.get(key)
    if not pack or pack["kind"] != "pack":
        raise RuntimeError("Пак не найден")
    have = {m.get("key") for m in read_manifests().values()}
    ctx.log(f"Пак «{pack['name']}»: {len(pack['pack'])} модов", "step")
    for name in pack["pack"]:
        entry = CATALOG.find_by_name(name)
        if not entry:
            ctx.log(f"  «{name}» не найден в каталоге — пропущен", "warn")
        elif entry["key"] in have:
            ctx.log(f"  «{name}» уже установлен")
        else:
            try:
                install(ctx, entry["key"])
            except Exception as e:
                ctx.log(f"  «{name}»: {e}", "error")
    ctx.log(f"Пак «{pack['name']}» установлен", "done")


def uninstall(ctx, mid):
    mod = read_manifests().get(mid)
    if not mod:
        raise RuntimeError("Мод не найден")
    _rmtree(os.path.join(paths.MODS_DIR, mod["folder"]))
    with state.edit() as data:
        data["order"] = [x for x in data.get("order") or [] if x != mid]
        (data.get("enabled") or {}).pop(mid, None)
    ctx.log(f"Удалён «{title(mod)}»", "success")


def update(ctx, mid):
    mod = read_manifests().get(mid)
    if not mod or mod.get("local"):
        raise RuntimeError("Этот мод нельзя обновить из каталога")
    install(ctx, mod.get("key") or catalog.mod_key(mod["cat"], mod["name"]), mod.get("label"))


def update_all(ctx):
    CATALOG.ensure()
    mods = [m for m in installed() if m["update"]]
    if not mods:
        ctx.log("Все моды актуальны", "done")
        return
    for mod in mods:
        try:
            update(ctx, mod["id"])
        except Exception as e:
            ctx.log(f"  «{title(mod)}»: {e}", "error")
    ctx.log(f"Обновлено модов: {len(mods)}", "done")


def set_enabled(mid, enabled):
    manifests = read_manifests()
    if mid not in manifests:
        raise RuntimeError("Мод не найден")
    with state.edit() as data:
        data.setdefault("enabled", {})[mid] = bool(enabled)
        disabled = _resolve_conflicts(data, manifests[mid], manifests) if enabled else []
    return [name for _, name in disabled]


def set_order(ids):
    existing = read_manifests()
    with state.edit() as data:
        order = [mid for mid in ids if mid in existing]
        data["order"] = order + [mid for mid in data.get("order") or [] if mid in existing and mid not in order]


def import_local(filename, temp_path):
    """Свой .vpk или .zip с VPK внутри — попадает в начало списка (самый высокий приоритет)."""
    low = filename.lower()
    stem = sanitize(os.path.splitext(os.path.basename(filename))[0])
    folder = base = sanitize(f"local - {stem}")
    counter = 2
    while os.path.exists(os.path.join(paths.MODS_DIR, folder)):
        folder = f"{base} ({counter})"
        counter += 1
    final = os.path.join(paths.MODS_DIR, folder)
    os.makedirs(final)
    try:
        if low.endswith(".zip"):
            extract_zip(temp_path, final)
        elif low.endswith(".vpk"):
            shutil.copyfile(temp_path, os.path.join(final, sanitize(os.path.basename(filename))))
        else:
            raise RuntimeError("Поддерживаются только .vpk и .zip")
        if not _has_vpk(final):
            raise RuntimeError("Внутри нет VPK-файлов")
    except BaseException:
        _rmtree(final)
        raise
    mid = f"local::{folder}"
    write_json(os.path.join(final, MANIFEST), {
        "id": mid, "cat": "local", "name": stem, "local": True,
        "installed_at": int(time.time()), "size": _folder_size(final),
    })
    with state.edit() as data:
        data.setdefault("order", []).insert(0, mid)
        data.setdefault("enabled", {})[mid] = True
    return mid
