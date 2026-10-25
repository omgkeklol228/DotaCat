"""Сборка DotaCat.exe.

    pip install pyinstaller pillow
    python build.py [папка_для_exe]

По умолчанию exe кладётся в ../DotaCat рядом с папкой исходников. При первом запуске
exe раскладывает рядом с собой ui/ (интерфейс, правится без пересборки) и data/ (настройки и моды).
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from dotacat import APP_NAME, VERSION  # noqa: E402

WORK = os.path.join(ROOT, "build")
VERSION_TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041904B0', [
      StringStruct('CompanyName', 'DotaCat'),
      StringStruct('FileDescription', 'DotaCat — менеджер модов Dota 2'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'DotaCat'),
      StringStruct('OriginalFilename', 'DotaCat.exe'),
      StringStruct('ProductName', 'DotaCat'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [0x0419, 1200])])
  ]
)
"""


def stage_ui(target):
    """Копия ui/ без пользовательских файлов (фон, резервные копии)."""
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(
        os.path.join(ROOT, "ui"), target,
        ignore=lambda d, names: [n for n in names if n in ("user", "__pycache__") or n.startswith(".")],
    )
    os.makedirs(os.path.join(target, "user"), exist_ok=True)
    return target


def main():
    out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), APP_NAME)
    os.makedirs(WORK, exist_ok=True)
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "make_icon.py")])

    nums = tuple(int(x) for x in (VERSION.split(".") + ["0", "0", "0"])[:4])
    version_file = os.path.join(WORK, "version_info.txt")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(VERSION_TEMPLATE.format(nums=nums, version=VERSION))

    ui = stage_ui(os.path.join(WORK, "ui"))
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", APP_NAME,
        "--icon", os.path.join(ROOT, "assets", "dotacat.ico"),
        "--version-file", version_file,
        "--add-data", f"{ui}{os.pathsep}ui",
        "--exclude-module", "tkinter",
        "--distpath", out,
        "--workpath", os.path.join(WORK, "pyinstaller"),
        "--specpath", WORK,
        os.path.join(ROOT, "DotaCat.py"),
    ])
    shutil.copyfile(os.path.join(ROOT, "README.md"), os.path.join(out, "README.md"))
    print(f"\nГотово: {os.path.join(out, APP_NAME + '.exe')}")


if __name__ == "__main__":
    main()
