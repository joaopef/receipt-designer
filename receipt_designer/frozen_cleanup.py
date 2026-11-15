"""Prepare this process's onefile directories for the bootloader's cleanup.

No files are removed here. PyInstaller retains responsibility for removing its
own extraction after the Python child exits and releases its DLLs.
"""
from __future__ import annotations
import atexit
import os
from pathlib import Path
import re
import stat
import sys


def _extraction_path(value):
    path = Path(value)
    if not path.is_absolute() or not re.fullmatch(r'_MEI[0-9A-Za-z]+', path.name):
        return None
    return path


def prepare_extraction_cleanup(root: Path) -> int:
    """Clear only ReadOnly flags on directories in this exact extraction."""
    root = _extraction_path(root)
    if os.name != 'nt' or root is None or not root.exists():
        return 0
    changed = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        info = directory.stat(follow_symlinks=False)
        if (info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
                or not stat.S_ISDIR(info.st_mode)):
            continue
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
            # Windows chmod clears this metadata flag without changing ACLs.
            directory.chmod(stat.S_IWRITE)
            changed += 1
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
    return changed


def register_extraction_cleanup() -> bool:
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        return False
    root = _extraction_path(getattr(sys, '_MEIPASS', ''))
    if root is None:
        return False

    def on_exit():
        try:
            prepare_extraction_cleanup(root)
        except OSError:
            # Genuine locks/ACL failures remain for the bootloader to report.
            pass

    atexit.register(on_exit)
    return True
