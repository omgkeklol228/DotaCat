"""Чтение и запись архивов Valve VPK (версии 1 и 2) без сторонних библиотек."""

import binascii
import hashlib
import os
import re
import struct
import threading

SIGNATURE = 0x55AA1234
EMBEDDED_ARCHIVE = 0x7FFF
DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024  # как в Minify: внешние архивы по 100 МБ
_ENTRY = struct.Struct("<IHHIIH")  # crc, preload, archive, offset, length, terminator
_MD5_ENTRY = struct.Struct("<III16s")
_CHUNK_RE = re.compile(r"_\d{3}\.vpk$", re.IGNORECASE)


def is_chunk_file(filename):
    """pak01_000.vpk и т.п. — части архива, а не самостоятельные VPK."""
    return bool(_CHUNK_RE.search(filename))


def archive_prefix(dir_path):
    base = dir_path[:-4] if dir_path.lower().endswith(".vpk") else dir_path
    return base[:-4] if base.lower().endswith("_dir") else base


def _cstr(tree, pos):
    end = tree.find(b"\0", pos)
    if end < 0:
        raise ValueError("повреждённое дерево VPK")
    return tree[pos:end].decode("utf-8", "replace"), end + 1


class Entry:
    __slots__ = ("path", "crc", "preload", "archive", "offset", "length")

    def __init__(self, path, crc, preload, archive, offset, length):
        self.path = path
        self.crc = crc
        self.preload = preload
        self.archive = archive
        self.offset = offset
        self.length = length

    @property
    def size(self):
        return len(self.preload) + self.length


class VPK:
    """Открытый VPK: entries — словарь {путь в нижнем регистре: Entry}."""

    def __init__(self, path):
        self.path = path
        self.prefix = archive_prefix(path)
        self.entries = {}
        self._handles = {}
        self._lock = threading.Lock()
        with open(path, "rb") as f:
            head = f.read(12)
            if len(head) < 12:
                raise ValueError("файл слишком мал для VPK")
            signature, version, tree_size = struct.unpack("<3I", head)
            if signature != SIGNATURE:
                raise ValueError("это не VPK-архив")
            if version == 2:
                f.read(16)
                header_size = 28
            elif version == 1:
                header_size = 12
            else:
                raise ValueError(f"неподдерживаемая версия VPK: {version}")
            tree = f.read(tree_size)
        if len(tree) != tree_size:
            raise ValueError("VPK обрезан")
        self.data_offset = header_size + tree_size
        self._parse_tree(tree)

    def _parse_tree(self, tree):
        pos = 0
        unpack = _ENTRY.unpack_from
        while True:
            ext, pos = _cstr(tree, pos)
            if not ext:
                break
            while True:
                directory, pos = _cstr(tree, pos)
                if not directory:
                    break
                while True:
                    name, pos = _cstr(tree, pos)
                    if not name:
                        break
                    crc, preload_size, archive, offset, length, _ = unpack(tree, pos)
                    pos += _ENTRY.size
                    preload = tree[pos:pos + preload_size]
                    pos += preload_size
                    filename = name if ext == " " else f"{name}.{ext}"
                    path = filename if directory.strip() == "" else f"{directory}/{filename}"
                    self.entries[path.lower()] = Entry(path, crc, preload, archive, offset, length)

    def read(self, entry):
        if not entry.length:
            return bytes(entry.preload)
        if entry.archive == EMBEDDED_ARCHIVE:
            path, offset = self.path, self.data_offset + entry.offset
        else:
            path, offset = f"{self.prefix}_{entry.archive:03d}.vpk", entry.offset
        with self._lock:
            handle = self._handles.get(path)
            if handle is None:
                handle = self._handles[path] = open(path, "rb")
            handle.seek(offset)
            data = handle.read(entry.length)
        if len(data) != entry.length:
            raise IOError(f"VPK обрезан: {entry.path}")
        return bytes(entry.preload) + data

    def close(self):
        with self._lock:
            for handle in self._handles.values():
                handle.close()
            self._handles.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __iter__(self):
        return (entry.path for entry in self.entries.values())

    def __len__(self):
        return len(self.entries)


def remove_set(dir_path):
    """Удаляет pakNN_dir.vpk и все его части pakNN_000.vpk…"""
    folder = os.path.dirname(dir_path) or "."
    prefix = os.path.basename(archive_prefix(dir_path)).lower()
    removed = []
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            low = name.lower()
            is_dir_file = low == f"{prefix}_dir.vpk"
            is_part = low.startswith(f"{prefix}_") and is_chunk_file(low) and len(low) == len(prefix) + 8
            if is_dir_file or is_part:
                path = os.path.join(folder, name)
                os.remove(path)
                removed.append(path)
    return removed


def _split(path):
    path = path.replace("\\", "/").strip("/")
    directory, _, filename = path.rpartition("/")
    name, dot, ext = filename.rpartition(".")
    if not dot or not name:
        name, ext = filename, ""
    return ext or " ", directory or " ", name


def write(dir_path, files, chunk_size=DEFAULT_CHUNK_SIZE, progress=None):
    """Пишет VPK v2: pakNN_dir.vpk + pakNN_000.vpk, pakNN_001.vpk…

    files — список пар (путь внутри VPK, функция без аргументов, возвращающая bytes).
    Возвращает список созданных файлов.
    """
    files = list(files)
    prefix = archive_prefix(dir_path)
    remove_set(dir_path)

    tree = {}
    for path, reader in files:
        ext, directory, name = _split(path)
        tree.setdefault(ext, {}).setdefault(directory, []).append([name, reader, None])

    created = []
    index, written = 0, 0
    archive = f"{prefix}_{index:03d}.vpk"
    out = open(archive, "wb")
    created.append(archive)
    done, total = 0, len(files)
    try:
        for directories in tree.values():
            for items in directories.values():
                for item in items:
                    data = item[1]()
                    if written and written + len(data) > chunk_size:
                        out.close()
                        index += 1
                        written = 0
                        archive = f"{prefix}_{index:03d}.vpk"
                        out = open(archive, "wb")
                        created.append(archive)
                    item[2] = (binascii.crc32(data) & 0xFFFFFFFF, index, written, len(data))
                    out.write(data)
                    written += len(data)
                    done += 1
                    if progress and (done % 64 == 0 or done == total):
                        progress(done, total)
    finally:
        out.close()

    tree_bytes = bytearray()
    for ext, directories in tree.items():
        tree_bytes += ext.encode("utf-8") + b"\0"
        for directory, items in directories.items():
            tree_bytes += directory.encode("utf-8") + b"\0"
            for name, _, (crc, archive_index, offset, length) in items:
                tree_bytes += name.encode("utf-8") + b"\0"
                tree_bytes += _ENTRY.pack(crc, 0, archive_index, offset, length, 0xFFFF)
            tree_bytes += b"\0"
        tree_bytes += b"\0"
    tree_bytes += b"\0"

    md5_section = bytearray()
    for archive_index in range(index + 1):
        with open(f"{prefix}_{archive_index:03d}.vpk", "rb") as part:
            offset = 0
            while block := part.read(1024 * 1024):
                md5_section += _MD5_ENTRY.pack(archive_index, offset, len(block), hashlib.md5(block).digest())
                offset += len(block)

    header = struct.pack("<7I", SIGNATURE, 2, len(tree_bytes), 0, len(md5_section), 48, 0)
    body = header + bytes(tree_bytes) + bytes(md5_section)
    tree_md5 = hashlib.md5(tree_bytes).digest()
    md5_section_md5 = hashlib.md5(md5_section).digest()
    file_md5 = hashlib.md5(body + tree_md5 + md5_section_md5).digest()
    with open(dir_path, "wb") as f:
        f.write(body + tree_md5 + md5_section_md5 + file_md5)
    created.insert(0, dir_path)
    return created
