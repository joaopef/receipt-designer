"""
pytest configuration and fixtures.
"""

import os
from pathlib import Path
import pytest


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
