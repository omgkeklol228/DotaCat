"""Загрузка файлов по HTTP (только стандартная библиотека)."""

import os
import urllib.parse
import urllib.request

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DotaCat/1.0"


def quote(path):
    return urllib.parse.quote(path, safe="/")


def open_url(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def fetch(url, timeout=30):
    with open_url(url, timeout) as response:
        return response.read()


def download(url, dest, progress=None, timeout=60):
    """Скачивает url в dest через временный .part-файл. progress(done, total)."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = f"{dest}.part"
    try:
        with open_url(url, timeout) as response, open(part, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        os.replace(part, dest)
    except BaseException:
        try:
            os.remove(part)
        except OSError:
            pass
        raise
