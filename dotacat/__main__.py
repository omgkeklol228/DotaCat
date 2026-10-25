"""Запуск: python -m dotacat  (флаг --no-window — только сервер, без окна)."""

import os
import sys
import threading
import time
import urllib.request

from . import paths


def _fix_streams():
    # pythonw.exe запускается без консоли: sys.stdout/sys.stderr там равны None
    if sys.stdout is None or sys.stderr is None:
        log = open(paths.LOG_FILE, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def _running_instance():
    from .store import read_json

    data = read_json(paths.INSTANCE_FILE)
    if not isinstance(data, dict) or not data.get("port"):
        return None
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request = urllib.request.Request(
            f"http://127.0.0.1:{data['port']}/api/ping", headers={"X-Token": data.get("token", "")}
        )
        opener.open(request, timeout=1.5).read()
    except Exception:
        return None
    return f"http://127.0.0.1:{data['port']}/?t={data['token']}"


def _watch_window(process, app):
    started = time.time()
    process.wait()
    # Если процесс завершился сразу, браузер передал окно уже запущенному экземпляру —
    # тогда о закрытии окна узнаём по пропавшему опросу из интерфейса.
    if time.time() - started > 5:
        app.request_quit()


def main():
    paths.ensure()
    _fix_streams()
    from . import window

    url = _running_instance()
    if url:
        # программа уже запущена — просто показываем её окно
        if "--no-window" in sys.argv:
            print(f"DotaCat уже запущен: {url}", flush=True)
        else:
            window.open_window(url)
        return

    from .server import App
    from .store import write_json

    app = App()
    app.start()
    write_json(paths.INSTANCE_FILE, {"port": app.port, "token": app.token, "pid": os.getpid()})
    print(f"DotaCat: {app.url}", flush=True)
    if "--no-window" not in sys.argv:
        process = window.open_window(app.url)
        if process is not None:
            threading.Thread(target=_watch_window, args=(process, app), daemon=True).start()
    try:
        while not app.quit.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
        try:
            os.remove(paths.INSTANCE_FILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
