"""Onefile cleanup must handle readonly directories without touching user files."""
import os
from pathlib import Path
import stat
import sys
import pytest


@pytest.mark.skipif(os.name != 'nt', reason='Windows directory attributes')
def test_readonly_extraction_directories_become_removable_without_changing_files(tmp_path):
    from receipt_designer.frozen_cleanup import prepare_extraction_cleanup
    root = tmp_path / '_MEItest123'
    child = root / 'assets' / 'icons'
    child.mkdir(parents=True)
    resource = child / 'keep.txt'
    resource.write_text('Unchanged resource', encoding='utf-8')
    resource.chmod(stat.S_IREAD)
    for directory in (root, root/'assets', child):
        directory.chmod(stat.S_IREAD)
    assert prepare_extraction_cleanup(root) == 3
    assert resource.read_text(encoding='utf-8') == 'Unchanged resource'
    assert resource.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    resource.chmod(stat.S_IWRITE)
    resource.unlink()
    child.rmdir()
    (root/'assets').rmdir()
    root.rmdir()


def test_unfrozen_app_and_onedir_bundle_do_not_register_cleanup(tmp_path, monkeypatch):
    from receipt_designer.frozen_cleanup import register_extraction_cleanup
    callbacks = []
    monkeypatch.setattr('atexit.register', callbacks.append)
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path/'_MEItest123'), raising=False)
    assert not register_extraction_cleanup()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path/'_internal'), raising=False)
    assert not register_extraction_cleanup()
    assert callbacks == []


@pytest.mark.skipif(os.name != 'nt', reason='Windows directory attributes')
def test_frozen_cleanup_runs_at_exit_and_is_scoped_to_own_extraction(tmp_path, monkeypatch):
    from receipt_designer.frozen_cleanup import register_extraction_cleanup
    own = tmp_path/'_MEIown123'
    unrelated = tmp_path/'_MEIother123'
    own.mkdir(); unrelated.mkdir()
    own.chmod(stat.S_IREAD); unrelated.chmod(stat.S_IREAD)
    callbacks = []
    monkeypatch.setattr('atexit.register', callbacks.append)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(own), raising=False)
    assert register_extraction_cleanup()
    assert own.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    assert len(callbacks) == 1
    callbacks[0]()
    assert not own.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    assert unrelated.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    unrelated.chmod(stat.S_IWRITE)


@pytest.mark.skipif(os.name != 'nt', reason='Windows directory attributes')
def test_cleanup_skips_directory_links(tmp_path):
    from receipt_designer.frozen_cleanup import prepare_extraction_cleanup
    root = tmp_path/'_MEItest123'
    root.mkdir()
    outside = tmp_path/'outside'
    outside.mkdir()
    try:
        (root/'link').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Creating directory symlinks is unavailable in this Windows session')
    outside.chmod(stat.S_IREAD)
    try:
        prepare_extraction_cleanup(root)
        assert outside.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
    finally:
        outside.chmod(stat.S_IWRITE)
