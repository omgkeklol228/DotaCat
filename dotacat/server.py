"""Локальный HTTP-сервер: отдаёт интерфейс из ui/ и JSON API для него.

Слушает только 127.0.0.1, а все запросы /api/ требуют токен из адреса окна,
поэтому другие сайты в браузере не могут управлять программой.
"""

import http.server
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
import urllib.parse
import webbrowser

from . import VERSION, catalog, library, net, optimize, patcher, paths, steam
from .catalog import CATALOG
from .store import config
from .tasks import TaskManager

MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".ico": "image/x-icon", ".mp4": "video/mp4",
    ".webm": "video/webm", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
}
CONFIG_TYPES = {
    "setup_done": bool, "steam_root": str, "dota_path": str, "language": str, "steam_account": str,
    "pak_number": int, "filter_adult": bool, "filter_anime": bool, "auto_refresh": bool,
    "restart_steam": bool, "theme": str, "theme_vars": dict, "ui": dict, "sources": dict,
}
BUILTIN_THEMES = {"violet", "minify", "light", "crimson", "glass"}
BACKGROUND_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
API = {}


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def route(method, name):
    def register(fn):
        API[(method, name)] = fn
        return fn
    return register


class App:
    def __init__(self):
        self.token = secrets.token_urlsafe(24)
        self.tasks = TaskManager(paths.LOG_FILE)
        self.port = 0
        self.httpd = None
        self.quit = threading.Event()
        self.last_seen = 0.0
        self.bye_at = 0.0
        self.download_slots = threading.Semaphore(6)
        self._file_locks = {}
        self._locks_guard = threading.Lock()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/?t={self.token}"

    def file_lock(self, path):
        with self._locks_guard:
            return self._file_locks.setdefault(path, threading.Lock())

    def start(self):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.httpd.app = self
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, name="http", daemon=True).start()
        threading.Thread(target=self._watchdog, name="watchdog", daemon=True).start()
        self.tasks.log(f"DotaCat {VERSION} запущен")
        self.tasks.submit("Загрузка каталога", load_catalog)

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    def request_quit(self):
        self.bye_at = time.time()

    def _watchdog(self):
        """Закрывает сервер, когда окно закрыто (нет опроса), но не посреди задачи."""
        while not self.quit.is_set():
            time.sleep(1)
            if self.tasks.busy():
                continue
            now = time.time()
            if self.bye_at and self.last_seen < self.bye_at and now - self.bye_at > 6:
                self.quit.set()
            elif self.last_seen and now - self.last_seen > 150:
                self.quit.set()


def load_catalog(ctx, force=False):
    CATALOG.load(force=force, log=ctx.log)
    # после загрузки известны герои и слоты — выключаем несовместимые моды, если такие включены
    library.normalize_conflicts(ctx)
    optimize.prefetch(ctx)


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "DotaCat"

    def log_message(self, fmt, *args):
        pass

    @property
    def app(self):
        return self.server.app

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        try:
            host = (self.headers.get("Host") or "").lower()
            if host not in (f"127.0.0.1:{self.app.port}", f"localhost:{self.app.port}"):
                return self.send_json({"error": "forbidden"}, 403)
            parsed = urllib.parse.urlsplit(self.path)
            path = urllib.parse.unquote(parsed.path)
            query = urllib.parse.parse_qs(parsed.query)
            if path.startswith("/api/"):
                name = path[5:]
                if name == "bye":
                    if secrets.compare_digest((query.get("t") or [""])[0], self.app.token):
                        self.app.request_quit()
                    return self.send_json({"ok": True})
                if not secrets.compare_digest(self.headers.get("X-Token") or "", self.app.token):
                    return self.send_json({"error": "Нет доступа: откройте программу через DotaCat.exe"}, 403)
                handler = API.get((method, name))
                if handler is None:
                    return self.send_json({"error": f"Неизвестный запрос: {name}"}, 404)
                result = handler(self, query)
                return self.send_json({"ok": True} if result is None else result)
            if method != "GET":
                return self.send_json({"error": "Метод не поддерживается"}, 405)
            if path == "/cache":
                return self._serve_cache(query)
            return self._serve_static(path)
        except ApiError as e:
            self.send_json({"error": str(e)}, e.status)
        except ConnectionError:
            pass
        except Exception as e:
            self.app.tasks.log_exception(e)
            try:
                self.send_json({"error": str(e) or type(e).__name__}, 500)
            except Exception:
                pass

    # --- ответы ---

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, cache):
        size = os.path.getsize(path)
        start, end, status = 0, size - 1, 200
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        if match and size:
            first, last = match.groups()
            if first:
                start, end = int(first), min(int(last) if last else size - 1, size - 1)
            elif last:
                start = max(0, size - int(last))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        self.send_header("Content-Type", MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(end - start + 1 if size else 0))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", cache)
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1 if size else 0
            while remaining > 0:
                chunk = f.read(min(256 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _serve_static(self, path):
        root = os.path.abspath(paths.UI_DIR)
        target = os.path.abspath(os.path.join(root, path.lstrip("/") or "index.html"))
        if not target.startswith(root + os.sep) or not os.path.isfile(target):
            return self.send_json({"error": "Не найдено"}, 404)
        # no-store: правки в ui/ видны сразу после Ctrl+R
        self.send_file(target, "no-store")

    def _serve_cache(self, query):
        """Превью модов: качаются с GitHub один раз и дальше берутся из data/cache."""
        rel = (query.get("p") or [""])[0].replace("\\", "/")
        parts = rel.split("/")
        if not rel.startswith("assets/previews/") or any(p in ("", ".", "..") for p in parts):
            return self.send_json({"error": "Не найдено"}, 404)
        local = os.path.join(paths.PREVIEW_CACHE, *parts[2:])
        if not os.path.isfile(local):
            with self.app.file_lock(local):
                if not os.path.isfile(local):
                    with self.app.download_slots:
                        for base in (catalog.MAIN_URL, catalog.MIRROR_URL):
                            try:
                                net.download(base + net.quote(rel), local, timeout=30)
                                break
                            except Exception:
                                continue
                        else:
                            return self.send_json({"error": "Превью недоступно"}, 404)
        self.send_file(local, "max-age=604800")

    # --- чтение тела запроса ---

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 8 * 1024 * 1024:
            raise ApiError("Слишком большой запрос", 413)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            raise ApiError("Некорректный JSON")
        if not isinstance(data, dict):
            raise ApiError("Ожидался объект JSON")
        return data

    def read_to_file(self, suffix, limit=4 * 1024 ** 3):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > limit:
            raise ApiError("Пустой или слишком большой файл")
        fd, tmp = tempfile.mkstemp(suffix=suffix, dir=paths.DATA_DIR)
        remaining = length
        with os.fdopen(fd, "wb") as out:
            while remaining:
                chunk = self.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                out.write(chunk)
                remaining -= len(chunk)
        if remaining:
            os.remove(tmp)
            raise ApiError("Загрузка файла прервана")
        return tmp


# --- темы ---

_THEME_META = re.compile(r"@theme([^*]*)\*/")
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')
_VAR = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")


def list_themes():
    themes = []
    for filename in sorted(os.listdir(paths.THEMES_DIR)):
        if not filename.lower().endswith(".css"):
            continue
        theme_id = filename[:-4]
        try:
            with open(os.path.join(paths.THEMES_DIR, filename), encoding="utf-8") as f:
                text = f.read(20000)
        except OSError:
            continue
        meta = _THEME_META.search(text)
        attrs = dict(_ATTR.findall(meta.group(1))) if meta else {}
        values = dict(_VAR.findall(text))
        themes.append({
            "id": theme_id,
            "name": attrs.get("name") or theme_id,
            "author": attrs.get("author", ""),
            "builtin": theme_id in BUILTIN_THEMES,
            "colors": [values.get(v, "").strip() for v in ("--bg", "--panel", "--card", "--accent", "--accent-2", "--text")],
        })
    themes.sort(key=lambda t: (not t["builtin"], t["name"].lower()))
    return themes


def theme_slug(name):
    slug = re.sub(r"[^\w-]+", "-", name.strip().lower()).strip("-")[:40] or f"theme-{int(time.time())}"
    return f"{slug}-my" if slug in BUILTIN_THEMES else slug


# --- API ---

def _body_id(h):
    data = h.read_json()
    if not data.get("id"):
        raise ApiError("Не указан мод")
    return data


@route("GET", "ping")
def api_ping(h, q):
    return {"ok": True, "version": VERSION}


@route("GET", "state")
def api_state(h, q):
    return {
        "version": VERSION,
        "config": config.snapshot(),
        "languages": [{"id": c, "name": n, "folder": patcher.output_folder(c)} for c, n in patcher.LANGUAGES],
        "status": patcher.status(),
        "themes": list_themes(),
        "site": catalog.SITE_URL,
        "repo": catalog.REPO_URL,
        "credits": catalog.CREDITS_URL,
        "paths": {"data": paths.DATA_DIR, "ui": paths.UI_DIR, "mods": paths.MODS_DIR},
    }


@route("GET", "catalog")
def api_catalog(h, q):
    try:
        CATALOG.ensure()
    except Exception as e:
        raise ApiError(str(e), 503)
    return CATALOG.public()


@route("GET", "installed")
def api_installed(h, q):
    return {"mods": library.installed(), "status": patcher.status()}


@route("GET", "poll")
def api_poll(h, q):
    h.app.last_seen = time.time()
    try:
        since = int((q.get("since") or ["0"])[0] or 0)
    except ValueError:
        since = 0
    result = h.app.tasks.poll(since)
    result["catalog"] = CATALOG.refreshed
    return result


@route("GET", "detect")
def api_detect(h, q):
    root = config.get("steam_root")
    if not root or not os.path.isfile(os.path.join(root, "steam.exe")):
        root = steam.find_steam_root()
    dota = config.get("dota_path")
    if not steam.is_valid_dota(dota):
        dota = steam.find_dota(root) if root else ""
    language = steam.game_language(dota) if dota else ""
    return {
        "steam_root": root,
        "dota_path": dota,
        "dota_ok": steam.is_valid_dota(dota),
        "language": language if language in patcher.LANGUAGE_IDS else "",
        "accounts": steam.accounts(root) if root else [],
    }


@route("GET", "check-dota")
def api_check_dota(h, q):
    return {"ok": steam.is_valid_dota((q.get("path") or [""])[0])}


@route("GET", "launch-options")
def api_launch_options(h, q):
    info = patcher.launch_options_info()
    info["steam_running"] = steam.steam_running()
    return info


@route("POST", "config")
def api_config(h, q):
    clean = {}
    for key, value in h.read_json().items():
        expected = CONFIG_TYPES.get(key)
        if expected is None:
            continue
        if expected is int:
            value = int(value)
        elif expected is bool:
            value = bool(value)
        elif not isinstance(value, expected):
            raise ApiError(f"Неверное значение: {key}")
        clean[key] = value
    if "language" in clean and clean["language"] not in patcher.LANGUAGE_IDS:
        raise ApiError("Неизвестный язык")
    if "pak_number" in clean:
        clean["pak_number"] = min(99, max(2, clean["pak_number"]))
    for key in ("dota_path", "steam_root"):
        if key in clean:
            value = clean[key].strip().strip('"')
            clean[key] = os.path.normpath(value) if value else ""
    config.update(clean)
    return {"config": config.snapshot(), "status": patcher.status()}


@route("POST", "catalog/refresh")
def api_catalog_refresh(h, q):
    return {"task": h.app.tasks.submit("Обновление каталога", load_catalog, True)}


@route("GET", "conflicts")
def api_conflicts(h, q):
    try:
        return library.would_replace((q.get("key") or [""])[0], (q.get("label") or [None])[0] or None)
    except RuntimeError as e:
        raise ApiError(str(e), 404)


@route("POST", "install")
def api_install(h, q):
    data = h.read_json()
    try:
        entry, style, mid = library.resolve(data.get("key") or "", data.get("label"))
    except RuntimeError as e:
        raise ApiError(str(e), 404)
    label = style["label"] if style else None
    task = h.app.tasks.submit(f"Установка «{entry['name']}»", library.install, entry["key"], label,
                              bool(data.get("remove_replaced")))
    return {"task": task, "id": mid}


@route("POST", "install-pack")
def api_install_pack(h, q):
    key = h.read_json().get("key") or ""
    pack = CATALOG.get(key)
    if not pack:
        raise ApiError("Пак не найден", 404)
    return {"task": h.app.tasks.submit(f"Пак «{pack['name']}»", library.install_pack, key)}


@route("POST", "uninstall")
def api_uninstall(h, q):
    return {"task": h.app.tasks.submit("Удаление мода", library.uninstall, _body_id(h)["id"])}


@route("POST", "update")
def api_update(h, q):
    return {"task": h.app.tasks.submit("Обновление мода", library.update, _body_id(h)["id"])}


@route("POST", "update-all")
def api_update_all(h, q):
    return {"task": h.app.tasks.submit("Обновление модов", library.update_all)}


@route("POST", "toggle")
def api_toggle(h, q):
    data = _body_id(h)
    try:
        disabled = library.set_enabled(data["id"], bool(data.get("enabled")))
    except RuntimeError as e:
        raise ApiError(str(e), 404)
    h.app.tasks.bump()
    return {"disabled": disabled}


@route("POST", "order")
def api_order(h, q):
    ids = h.read_json().get("ids")
    if not isinstance(ids, list):
        raise ApiError("Ожидался список")
    library.set_order([str(i) for i in ids])
    h.app.tasks.bump()


@route("POST", "import")
def api_import(h, q):
    name = os.path.basename((q.get("name") or [""])[0])
    ext = os.path.splitext(name)[1].lower()
    if ext not in (".vpk", ".zip"):
        raise ApiError("Поддерживаются только .vpk и .zip")
    tmp = h.read_to_file(ext)
    try:
        mid = library.import_local(name, tmp)
    except RuntimeError as e:
        raise ApiError(str(e))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    h.app.tasks.log(f"Добавлен свой мод «{name}»", "success")
    h.app.tasks.bump()
    return {"id": mid}


@route("POST", "patch")
def api_patch(h, q):
    return {"task": h.app.tasks.submit("Применение модов", patcher.patch)}


@route("POST", "unpatch")
def api_unpatch(h, q):
    return {"task": h.app.tasks.submit("Удаление модов из игры", patcher.unpatch)}


@route("POST", "launch-options/apply")
def api_launch_apply(h, q):
    restart = bool(h.read_json().get("restart", True))
    return {"task": h.app.tasks.submit("Параметры запуска", patcher.apply_launch_options, restart)}


@route("POST", "open")
def api_open(h, q):
    data = h.read_json()
    target = data.get("target")
    if target == "url":
        url = str(data.get("url") or "")
        if not url.startswith(("https://", "http://")):
            raise ApiError("Можно открывать только веб-ссылки")
        webbrowser.open(url)
        return None
    folders = {
        "game": patcher.output_dir() if os.path.isdir(patcher.output_dir()) else patcher.game_dir(),
        "mods": paths.MODS_DIR,
        "themes": paths.THEMES_DIR,
        "ui": paths.UI_DIR,
        "data": paths.DATA_DIR,
    }
    folder = folders.get(target)
    if not folder or not os.path.isdir(folder):
        raise ApiError("Папка не найдена")
    os.startfile(folder)


@route("POST", "play")
def api_play(h, q):
    steam.launch_dota()


@route("GET", "check-matches")
def api_check_matches(h, q):
    from . import checks

    CATALOG.ensure()
    return checks.run()


@route("GET", "optimize")
def api_optimize(h, q):
    result = optimize.overview(patcher.current_launch_options())
    result["launch"].update(patcher.launch_options_info())
    return result


@route("POST", "optimize/tweak")
def api_optimize_tweak(h, q):
    data = h.read_json()
    try:
        optimize.set_tweak(str(data.get("id")), data.get("enabled"), data.get("settings"))
    except KeyError:
        raise ApiError("Неизвестная оптимизация", 404)
    if data.get("enabled"):
        h.app.tasks.submit("Списки оптимизаций", optimize.prefetch)
    return {"tweaks": optimize.tweaks_state(), "status": patcher.status()}


@route("POST", "optimize/launch")
def api_optimize_launch(h, q):
    current = patcher.current_launch_options()
    optimize.set_launch_choices(h.read_json(), current)
    info = patcher.launch_options_info()
    info["choices"] = optimize.launch_choices(current)
    return info


@route("POST", "optimize/graphics")
def api_optimize_graphics(h, q):
    data = h.read_json()
    changes = data.get("changes") if isinstance(data.get("changes"), dict) else {}
    fps = {k: data.get(k) for k in ("fps_max", "fps_max_ui") if isinstance(data.get(k), (int, float))}
    return {"task": h.app.tasks.submit("Настройки графики", optimize.write_graphics, changes, fps.get("fps_max"), fps.get("fps_max_ui"))}


@route("POST", "optimize/graphics/restore")
def api_optimize_graphics_restore(h, q):
    return {"task": h.app.tasks.submit("Настройки графики", optimize.restore_graphics)}


@route("POST", "open-system")
def api_open_system(h, q):
    try:
        optimize.open_system(str(h.read_json().get("target")))
    except KeyError:
        raise ApiError("Неизвестный раздел настроек")


@route("GET", "themes")
def api_themes(h, q):
    return {"themes": list_themes()}


@route("POST", "themes/save")
def api_theme_save(h, q):
    data = h.read_json()
    name, css = str(data.get("name") or "").strip(), str(data.get("css") or "")
    if not name or not css:
        raise ApiError("Нужны название и CSS темы")
    theme_id = theme_slug(name)
    with open(os.path.join(paths.THEMES_DIR, f"{theme_id}.css"), "w", encoding="utf-8") as f:
        f.write(css)
    return {"id": theme_id, "themes": list_themes()}


@route("POST", "themes/delete")
def api_theme_delete(h, q):
    theme_id = str(h.read_json().get("id") or "")
    if theme_id in BUILTIN_THEMES or not re.fullmatch(r"[\w-]+", theme_id):
        raise ApiError("Встроенную тему удалить нельзя")
    path = os.path.join(paths.THEMES_DIR, f"{theme_id}.css")
    if os.path.isfile(path):
        os.remove(path)
    return {"themes": list_themes()}


@route("POST", "custom-css")
def api_custom_css(h, q):
    css = h.read_json().get("css")
    if not isinstance(css, str):
        raise ApiError("Ожидался текст CSS")
    with open(paths.CUSTOM_CSS, "w", encoding="utf-8") as f:
        f.write(css)


@route("POST", "background")
def api_background(h, q):
    ext = os.path.splitext((q.get("name") or [""])[0])[1].lower()
    if ext not in BACKGROUND_EXT:
        raise ApiError("Поддерживаются JPG, PNG, WEBP и GIF")
    tmp = h.read_to_file(ext, limit=64 * 1024 * 1024)
    for filename in os.listdir(paths.USER_UI_DIR):
        if filename.startswith("background."):
            os.remove(os.path.join(paths.USER_UI_DIR, filename))
    shutil.move(tmp, os.path.join(paths.USER_UI_DIR, f"background{ext}"))
    return {"url": f"/user/background{ext}?v={int(time.time())}"}


@route("POST", "quit")
def api_quit(h, q):
    h.app.quit.set()
