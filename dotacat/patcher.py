"""«Применить моды»: слияние включённых VPK в один pakNN_dir.vpk в game/dota_<язык>.

Повторяет схему Minify + плагина D2PFX:
  * обычные моды — файлы берутся по принципу «верхний в списке побеждает»;
  * моды с maps/dota.vpk (ландшафты) — кладутся в game/dota_<язык>/maps/;
  * курсоры — копируются в game/dota/resource/cursor с резервной копией;
  * английский язык — через папку dota_dutch + «English Fix» (как в Minify).
"""

import functools
import json
import os
import shutil
import time

from . import VERSION, catalog, library, optimize, paths, steam, vpk
from .store import config, state

LANGUAGES = [
    ("russian", "Русский"), ("english", "English"), ("ukrainian", "Українська"),
    ("schinese", "简体中文"), ("tchinese", "繁體中文"), ("koreana", "한국어"), ("japanese", "日本語"),
    ("brazilian", "Português (Brasil)"), ("portuguese", "Português"), ("latam", "Español (Latinoamérica)"),
    ("spanish", "Español"), ("french", "Français"), ("italian", "Italiano"), ("german", "Deutsch"),
    ("polish", "Polski"), ("czech", "Čeština"), ("hungarian", "Magyar"), ("romanian", "Română"),
    ("bulgarian", "Български"), ("greek", "Ελληνικά"), ("turkish", "Türkçe"), ("thai", "ไทย"),
    ("vietnamese", "Tiếng Việt"), ("danish", "Dansk"), ("dutch", "Nederlands"), ("finnish", "Suomi"),
    ("norwegian", "Norsk"), ("swedish", "Svenska"),
]
LANGUAGE_IDS = {code for code, _ in LANGUAGES}
# Папки, которые могут лежать в моде «россыпью» (без VPK) — их тоже упаковываем.
GAME_ROOTS = {"materials", "models", "particles", "panorama", "resource", "scripts", "sounds", "soundevents", "maps", "cfg"}
CURSOR_EXTENSIONS = {".ani", ".bmp", ".cur", ".res", ".png", ".jpg", ".jpeg"}
MARKER = "dotacat_info.json"
OLD_MARKERS = ("moddeck_info.json",)  # VPK, собранные до переименования в DotaCat
MINIFY_MARKERS = ("minify_mods.json", "minify_version.txt", "minify_vpk_mods.txt")


class PatchError(Exception):
    pass


def launch_language(lang):
    return "dutch" if lang == "english" else lang


def output_folder(lang):
    return f"dota_{launch_language(lang)}"


def current_language():
    lang = config.get("language")
    return lang if lang in LANGUAGE_IDS else "russian"


def game_dir():
    return os.path.join(config.get("dota_path") or "", "game")


def output_dir(lang=None):
    return os.path.join(game_dir(), output_folder(lang or current_language()))


def pak_name():
    number = min(99, max(2, int(config.get("pak_number") or 66)))
    return f"pak{number:02d}_dir.vpk"


def status():
    return {
        "patch": state.get("patch") or {},
        "output_dir": output_dir(),
        "output_folder": output_folder(current_language()),
        "pak": pak_name(),
        "launch_language": launch_language(current_language()),
        "dota_ok": steam.is_valid_dota(config.get("dota_path")),
        "tweaks": optimize.signature(),
    }


def files_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} файл"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} файла"
    return f"{n} файлов"


def _read_file(path):
    with open(path, "rb") as f:
        return f.read()


def _loose_game_path(rel):
    parts = rel.split("/")
    for index, part in enumerate(parts[:-1]):
        if part.lower() in GAME_ROOTS:
            return "/".join(parts[index:])
    return None


class _GamePak:
    """pak01_dir.vpk игры открывается, только если он действительно нужен (English Fix, пустышки)."""

    def __init__(self, opened):
        self._opened = opened
        self._pak = None
        self._paths = None

    def __call__(self):
        if self._pak is None:
            self._pak = vpk.VPK(os.path.join(game_dir(), "dota", "pak01_dir.vpk"))
            self._opened.append(self._pak)
        return self._pak

    def paths(self):
        if self._paths is None:
            self._paths = list(self().entries)
        return self._paths


def _collect(mods, ctx, opened, game_pak):
    sources, maps, cursors = {}, [], []
    for mod in mods:
        folder = os.path.join(paths.MODS_DIR, mod["folder"])
        name = library.title(mod)
        if mod.get("cat") == "cursors":
            cursors.append(mod)
            continue
        added = shadowed = 0
        has_map = False
        for root, dirs, files in os.walk(folder):
            dirs.sort()
            for filename in sorted(files):
                full = os.path.join(root, filename)
                rel = os.path.relpath(full, folder).replace("\\", "/")
                low = filename.lower()
                if rel in (library.MANIFEST, library.MANIFEST_OLD) or low.endswith(".part"):
                    continue
                if low.endswith(".vpk"):
                    if vpk.is_chunk_file(low):
                        continue
                    if "maps" in rel.lower().split("/")[:-1]:
                        maps.append((mod, full))
                        has_map = True
                        continue
                    try:
                        pak = vpk.VPK(full)
                    except Exception as e:
                        ctx.log(f"  {name}: пропущен {rel} ({e})", "warn")
                        continue
                    opened.append(pak)
                    for entry in pak.entries.values():
                        key = entry.path.lower()
                        if key in sources:
                            shadowed += 1
                            continue
                        sources[key] = (entry.path, functools.partial(pak.read, entry))
                        added += 1
                else:
                    game_path = _loose_game_path(rel)
                    if not game_path:
                        continue
                    key = game_path.lower()
                    if key in sources:
                        shadowed += 1
                        continue
                    sources[key] = (game_path, functools.partial(_read_file, full))
                    added += 1
        blanks = 0
        parsed = optimize.mod_blacklist(folder)  # моды Minify и сообщества со списком пустышек
        if parsed:
            blanks = optimize.add_blanks(sources, optimize.resolve_blacklist(parsed, game_pak.paths()), game_pak())
        details = [files_word(added)] if added or not has_map else []
        if blanks:
            details.append(f"пустышек: {blanks}")
        if has_map:
            details.append("карта maps/dota.vpk")
        if shadowed:
            details.append(f"перекрыто модами выше: {shadowed}")
        ctx.log(f"  • {name}: {', '.join(details)}")
    return sources, maps, cursors


def _english_fix(sources, ctx, pak):
    """Английский текст в папке dota_dutch: копии *_english.txt под именами *_dutch.txt."""
    game = game_dir()
    count = 0
    for entry in pak.entries.values():
        low = entry.path.lower()
        for ext in ("txt", "vtt"):
            suffix = f"_english.{ext}"
            if low.endswith(suffix):
                path = entry.path[: -len(suffix)] + f"_dutch.{ext}"
                if path.lower() not in sources:
                    sources[path.lower()] = (path, functools.partial(pak.read, entry))
                    count += 1
    backup_root = os.path.join(paths.BACKUP_DIR, "english")
    disk = 0
    for sub in ("core", "dota_addons"):
        for root, _, files in os.walk(os.path.join(game, sub)):
            for filename in files:
                low = filename.lower()
                if not low.endswith(("_dutch.txt", "_dutch.vtt")):
                    continue
                dutch = os.path.join(root, filename)
                english = os.path.join(root, filename[:-10] + "_english" + filename[-4:])
                if not os.path.isfile(english):
                    continue
                backup = os.path.join(backup_root, os.path.relpath(dutch, game))
                if not os.path.exists(backup):
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copy2(dutch, backup)
                shutil.copyfile(english, dutch)
                disk += 1
    ctx.log(f"  • English Fix: локализация — {files_word(count)} (+{disk} на диске)")


def _restore_backup(name, game):
    backup_root = os.path.join(paths.BACKUP_DIR, name)
    restored = 0
    if os.path.isdir(backup_root):
        for root, _, files in os.walk(backup_root):
            for filename in files:
                saved = os.path.join(root, filename)
                dest = os.path.join(game, os.path.relpath(saved, backup_root))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(saved, dest)
                restored += 1
        shutil.rmtree(backup_root, ignore_errors=True)
    return restored


def _apply_cursors(mods, ctx):
    if len(mods) > 1:
        ctx.log("Включено несколько курсоров — применяется верхний в списке", "warn")
    mod = mods[0]
    folder = os.path.join(paths.MODS_DIR, mod["folder"])
    source = folder
    for root, dirs, _ in os.walk(folder):
        hit = next((d for d in dirs if d.lower() == "cursor"), None)
        if hit:
            source = os.path.join(root, hit)
            break
    game = game_dir()
    backup_root = os.path.join(paths.BACKUP_DIR, "cursors")
    created, count = [], 0
    for root, _, files in os.walk(source):
        for filename in files:
            if os.path.splitext(filename)[1].lower() not in CURSOR_EXTENSIONS:
                continue
            src = os.path.join(root, filename)
            rel = os.path.join("dota", "resource", "cursor", os.path.relpath(src, source))
            dest = os.path.join(game, rel)
            backup = os.path.join(backup_root, rel)
            if os.path.isfile(dest):
                if not os.path.exists(backup):
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copy2(dest, backup)
            else:
                created.append(dest)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            count += 1
    ctx.log(f"  • курсор «{library.title(mod)}»: заменено файлов: {count}")
    return created


def _cleanup(ctx):
    """Откатывает всё, что сделал предыдущий патч (файлы, курсоры, English Fix)."""
    patch = state.get("patch") or {}
    removed = 0
    for path in patch.get("files") or []:
        try:
            os.remove(path)
            removed += 1
        except FileNotFoundError:
            pass
        except OSError as e:
            raise PatchError(f"Не удалось удалить {path}: {e}. Закройте Dota 2 и повторите.")
        parent = os.path.dirname(path)
        if os.path.basename(parent).lower() == "maps":
            try:
                os.rmdir(parent)
            except OSError:
                pass
    game = patch.get("game_dir") or game_dir()
    cursors = _restore_backup("cursors", game)
    for path in patch.get("cursor_created") or []:
        try:
            os.remove(path)
        except OSError:
            pass
    english = _restore_backup("english", game)
    if cursors:
        ctx.log(f"Восстановлены стандартные курсоры ({cursors})")
    if english:
        ctx.log(f"Восстановлены файлы локализации ({english})")
    state.set("patch", {})
    return removed


def _pak_owner(pak_path):
    try:
        with vpk.VPK(pak_path) as pak:
            if MARKER in pak.entries or any(marker in pak.entries for marker in OLD_MARKERS):
                return "dotacat"
            if any(marker in pak.entries for marker in MINIFY_MARKERS):
                return "minify"
    except Exception:
        pass
    return "other"


def _free_pak_slot(pak_path, ctx):
    if not os.path.isfile(pak_path):
        return
    owner = _pak_owner(pak_path)
    if owner == "minify":
        ctx.log(f"{os.path.basename(pak_path)} был создан Minify — он будет заменён", "warn")
    elif owner == "other":
        ctx.log(f"{os.path.basename(pak_path)} уже существует (не DotaCat) — он будет заменён. "
                "Сменить номер VPK можно в Настройках.", "warn")
    vpk.remove_set(pak_path)


def _without_conflicts(mods, ctx):
    """Страховка: из несовместимых включённых модов (два скина на героя и т.п.) берётся верхний."""
    kept = []
    for mod in mods:
        info = library.conflict_info(mod)
        winner = next((k for k in kept if catalog.conflicts(info, library.conflict_info(k))), None)
        if winner:
            ctx.log(f"  • {library.title(mod)}: пропущен — конфликтует с «{library.title(winner)}»", "warn")
        else:
            kept.append(mod)
    return kept


def current_launch_options():
    root, account = config.get("steam_root"), config.get("steam_account")
    if not (root and account):
        return None
    try:
        return steam.get_launch_options(root, account)
    except OSError:
        return None


def launch_options_info():
    current = current_launch_options()
    desired = optimize.desired_tokens(launch_language(current_language()), current)
    info = {"account": config.get("steam_account"), "expected": " ".join(desired), "current": current,
            "result": None, "available": False, "ok": False}
    if current is None:
        return info
    result = optimize.merge_launch_options(current, desired)
    info.update(current=current, result=result, available=True, ok=result == " ".join(current.split()))
    return info


def patch(ctx):
    dota = config.get("dota_path")
    if not steam.is_valid_dota(dota):
        raise PatchError("Не найдена папка Dota 2 — укажите её в Настройках.")
    if steam.dota_running():
        raise PatchError("Dota 2 запущена — закройте игру и повторите.")
    lang = current_language()
    out = output_dir(lang)
    pak_path = os.path.join(out, pak_name())
    ctx.log(f"Применение модов → {out}", "step")
    _cleanup(ctx)

    mods = _without_conflicts([m for m in library.installed() if m["enabled"]], ctx)
    tweaks = optimize.enabled_tweaks()
    opened, files, cursor_created = [], [], []
    try:
        game_pak = _GamePak(opened)
        sources, maps, cursors = _collect(mods, ctx, opened, game_pak)
        if lang == "english" or tweaks:
            if lang == "english":
                _english_fix(sources, ctx, game_pak())
            # оптимизации идут последними: файлы модов пользователя они не трогают
            for name, count, error in optimize.apply_tweaks(sources, game_pak()):
                if error:
                    ctx.log(f"  • оптимизация «{name}»: {error}", "warn")
                else:
                    ctx.log(f"  • оптимизация «{name}»: {files_word(count)}")
        os.makedirs(out, exist_ok=True)
        _free_pak_slot(pak_path, ctx)
        if sources:
            info = json.dumps({
                "app": "DotaCat", "version": VERSION, "time": int(time.time()),
                "catalog": "https://h6rd.github.io/Dota2PornFxWeb/",
                "mods": [library.title(m) for m in mods],
            }, ensure_ascii=False, indent=2).encode("utf-8")
            sources[MARKER] = (MARKER, lambda: info)
            ctx.log(f"Сборка {pak_name()}: {files_word(len(sources))}…")
            files += vpk.write(pak_path, sources.values(), progress=lambda d, t: ctx.progress(d, t, "Сборка VPK"))
        if maps:
            if len(maps) > 1:
                ctx.log("Включено несколько модов с картой — используется верхний в списке", "warn")
            dest = os.path.join(out, "maps", "dota.vpk")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(maps[0][1], dest)
            files.append(dest)
        if cursors:
            cursor_created = _apply_cursors(cursors, ctx)
    finally:
        for pak in opened:
            pak.close()
        state.set("patch", {
            "files": files, "lang": lang, "game_dir": game_dir(), "time": int(time.time()),
            "mods": [m["id"] for m in mods], "cursor_created": cursor_created, "tweaks": optimize.signature(),
        })

    if not mods and not tweaks:
        ctx.log("Нет включённых модов — игра возвращена к стандартному виду", "done")
        return
    extra = f" и оптимизаций: {len(tweaks)}" if tweaks else ""
    ctx.log(f"Готово! Применено модов: {len(mods)}{extra}", "done")
    info = launch_options_info()
    if info["ok"]:
        ctx.log(f"Параметры запуска в порядке ({info['expected']}) — можно играть")
    else:
        ctx.log(f"Нужны параметры запуска «{info['expected']}» — кнопка «Прописать» в Настройках", "warn")


def unpatch(ctx):
    if steam.dota_running():
        raise PatchError("Dota 2 запущена — закройте игру и повторите.")
    removed = _cleanup(ctx)
    if steam.is_valid_dota(config.get("dota_path")):
        pak_path = os.path.join(output_dir(), pak_name())
        if os.path.isfile(pak_path) and _pak_owner(pak_path) == "dotacat":
            removed += len(vpk.remove_set(pak_path))
    ctx.log(f"Моды удалены из игры (файлов: {removed}). Установленные моды остались в DotaCat.", "done")


def apply_launch_options(ctx, restart=True):
    root, account = config.get("steam_root"), config.get("steam_account")
    if not root or not account:
        raise PatchError("Выберите аккаунт Steam в Настройках.")
    language = launch_language(current_language())
    was_running = steam.steam_running()
    if was_running:
        ctx.log("Закрываю Steam, иначе он перезапишет настройки…", "step")
        if not steam.shutdown_steam(root):
            raise PatchError("Steam не закрылся. Закройте его вручную и повторите.")
    old, new = steam.set_launch_options(
        root, account,
        lambda current: optimize.merge_launch_options(current, optimize.desired_tokens(language, current)),
        os.path.join(paths.BACKUP_DIR, "steam"),
    )
    if old != new:
        ctx.log(f"Параметры запуска: «{old}» → «{new}»", "done")
    else:
        ctx.log(f"Параметры запуска уже верные: «{new}»", "done")
    if was_running and restart:
        ctx.log("Запускаю Steam…")
        steam.start_steam(root)
