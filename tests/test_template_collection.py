"""Installing an ideas pack must preserve the user's edited documents."""
from pathlib import Path
import pytest
from PySide6 import QtWidgets
from receipt_designer.library import LibraryRepository


def test_install_is_repeatable_and_never_replaces_user_edits(tmp_path):
    from receipt_designer.template_collection.collection import install_collection
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    root = tmp_path / 'library'
    created = install_collection(root)
    assert len(created) == 18
    repo = LibraryRepository(root)
    assert len(repo.list_layouts()) == 18
    first_id = created[0].id
    edited = repo.load(first_id)
    edited.name = 'O meu modelo alterado'
    edited.elements[0].text = 'O meu texto'
    repo.save(edited, layout_id=first_id)
    assert install_collection(root) == []
    assert len(repo.list_layouts()) == 18
    assert repo.load(first_id).name == 'O meu modelo alterado'
    assert repo.load(first_id).elements[0].text == 'O meu texto'


def test_collection_survives_copy_without_source_checkout(tmp_path):
    import shutil
    from receipt_designer.template_collection.collection import install_collection
    from receipt_designer.ui.print_render import prepare_print_job
    from receipt_designer.printing.jobs import ThermalProfile
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    original = tmp_path / 'original'
    install_collection(original)
    copied = tmp_path / 'copied'
    shutil.copytree(original, copied)
    repo = LibraryRepository(copied)
    for info in repo.list_layouts():
        template = repo.load(info.id)
        job = prepare_print_job(template, ThermalProfile())
        assert job.preview.width == 576
        assert job.preview.height > 0
        assert all(part.image.height > 0 for part in job.parts)
        assert info.thumbnail and Path(info.thumbnail).is_file()
        assert any(element.kind == 'text' for element in template.elements)
        for element in template.elements:
            if element.kind == 'image' and element.image_path:
                assert Path(element.image_path).is_relative_to(copied)


def test_reinstall_recovers_manifest_without_recreating_trashed_layout(tmp_path):
    from receipt_designer.template_collection.collection import install_collection, MANIFEST
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    created = install_collection(tmp_path)
    repo = LibraryRepository(tmp_path)
    removed = created[0].id
    repo.trash(removed)
    (tmp_path / MANIFEST).unlink()
    assert install_collection(tmp_path) == []
    assert len(repo.list_layouts()) == 17
    assert [info.id for info in repo.list_trashed()] == [removed]


@pytest.mark.parametrize('metadata', [None, [], {'collection': 'thermal-ideas-v1'},
                                    {'collection': 'thermal-ideas-v1', 'slug': {}},
                                    {'collection': 'thermal-ideas-v1', 'slug': ''}])
def test_existing_legacy_metadata_does_not_block_install(tmp_path, metadata):
    from receipt_designer.template_collection.collection import install_collection
    from receipt_designer.core.models import Template
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    repo = LibraryRepository(tmp_path)
    old = repo.save(Template.from_dict({'name': 'O meu antigo', 'elements': [
        {'kind': 'text', 'text': 'Preservar', 'data': metadata}]}))
    assert len(install_collection(tmp_path)) == 18
    assert len(repo.list_layouts()) == 19
    assert repo.load(old.id).elements[0].data == metadata
