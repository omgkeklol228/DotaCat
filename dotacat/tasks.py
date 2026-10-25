"""Очередь фоновых задач (скачивание, патч) и журнал для интерфейса."""

import collections
import copy
import itertools
import queue
import threading
import time
import traceback


class Context:
    def __init__(self, manager, task):
        self._manager = manager
        self._task = task

    def log(self, text, level="info"):
        self._manager.log(text, level)

    def progress(self, done, total=0, label=""):
        with self._manager.lock:
            self._task["done"] = done
            self._task["total"] = total
            if label:
                self._task["label"] = label


class TaskManager:
    def __init__(self, log_file=None):
        self.lock = threading.Lock()
        self.logs = collections.deque(maxlen=3000)
        self.seq = 0
        self.rev = 0
        self.current = None
        self.pending = []
        self._queue = queue.Queue()
        self._ids = itertools.count(1)
        self._log_file = log_file
        threading.Thread(target=self._worker, name="tasks", daemon=True).start()

    def _write_file(self, line):
        if not self._log_file:
            return
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def log(self, text, level="info"):
        now = time.time()
        with self.lock:
            self.seq += 1
            self.logs.append({"id": self.seq, "t": now, "level": level, "text": str(text)})
        self._write_file(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))} [{level}] {text}")

    def log_exception(self, exc):
        self._write_file("".join(traceback.format_exception(exc)))

    def bump(self):
        with self.lock:
            self.rev += 1

    def busy(self):
        with self.lock:
            return self.current is not None or bool(self.pending)

    def submit(self, title, fn, *args, **kwargs):
        task = {"id": next(self._ids), "title": title, "done": 0, "total": 0, "label": ""}
        with self.lock:
            self.pending.append(task)
        self._queue.put((task, fn, args, kwargs))
        return task["id"]

    def _worker(self):
        while True:
            task, fn, args, kwargs = self._queue.get()
            with self.lock:
                self.pending.remove(task)
                self.current = task
            try:
                fn(Context(self, task), *args, **kwargs)
            except Exception as e:
                self.log(f"{task['title']}: {e}", "error")
                self.log_exception(e)
            finally:
                with self.lock:
                    self.current = None
                    self.rev += 1

    def poll(self, since):
        with self.lock:
            return {
                "seq": self.seq,
                "rev": self.rev,
                "logs": [entry for entry in self.logs if entry["id"] > since],
                "task": copy.copy(self.current),
                "queue": [t["title"] for t in self.pending],
            }
