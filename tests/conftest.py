"""
pytest configuration and fixtures.
"""

import os
from pathlib import Path
import pytest


@pytest.fixture(scope='session', autouse=True)
def isolated_editor_storage(tmp_path_factory):
    """UI tests must never recover/delete real drafts or change user profiles."""
    from PySide6 import QtCore
    root = tmp_path_factory.mktemp('editor-storage')
    temp = root / 'temp'
    temp.mkdir()
    original_location = QtCore.QStandardPaths.writableLocation
    original_format = QtCore.QSettings.defaultFormat()

    def writable_location(location):
        if location == QtCore.QStandardPaths.TempLocation:
            return str(temp)
        return original_location(location)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(QtCore.QStandardPaths, 'writableLocation', staticmethod(writable_location))
        patch.setenv('RECEIPT_DESIGNER_LIBRARY', str(root / 'library'))
        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
        QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, str(root / 'settings'))
        QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, QtCore.QSettings.SystemScope, str(root / 'system-settings'))
        try:
            yield
        finally:
            QtCore.QSettings.setDefaultFormat(original_format)


@pytest.fixture(scope='session', autouse=True)
def headless_windows_fonts():
    """Qt's offscreen Windows plugin has no system font database by default.

    Register installed test fonts so image tests check actual glyphs rather than
    fallback tofu boxes. Interactive builds use the regular Windows font engine.
    """
    if os.name != 'nt' or os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        yield
        return
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    app = QApplication.instance() or QApplication([])
    directory = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for name in ('arial.ttf', 'arialbd.ttf', 'ariblk.ttf', 'cour.ttf', 'courbd.ttf', 'seguisym.ttf'):
        path = directory / name
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    yield app
