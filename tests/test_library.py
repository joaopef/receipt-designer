"""File-backed library behavior, including failed writes and portable resources."""

import json
import os
from pathlib import Path
import shutil
from uuid import UUID

import pytest
from PIL import Image

from receipt_designer.core.models import Element, GuideLine, Template


@pytest.fixture
def repository(tmp_path):
    from receipt_designer.library import LibraryRepository
    return LibraryRepository(tmp_path / "library")


def image_template(tmp_path, name="Image layout"):
    source = tmp_path / "picture.png"
    Image.new("RGB", (5, 7), "black").save(source)
    return Template(name=name, elements=[
        Element(kind="image", x=1, y=2, w=3, h=4, image_path=str(source))
    ])


def test_roundtrip_preserves_editable_document_and_does_not_mutate_source(repository):
    template = Template(name="Diário", height_mm=160, version="2.3")
    template.elements.append(Element(kind="text", x=5, y=8, w=70, h=20,
                                     text="Olá {{var:task}}", data={"custom": 12}))
    template.guides.append(GuideLine(0, 5, 60, 5))
    template.variable_manager.set_variable("task", "Walk")
    original = template.to_dict()
    info = repository.save(template, preview=Image.new("RGB", (20, 30), "white"))

    assert str(UUID(info.id)) == info.id
    assert info.name == "Diário"
    assert info.folder == repository.root / info.id
    assert info.thumbnail == info.folder / "preview.png"
    assert Image.open(info.thumbnail).size == (20, 30)
    assert info.updated_at
    assert (info.folder / "metadata.json").is_file()
    assert (info.folder / "document.json").is_file()
    assert (info.folder / "assets").is_dir()
    assert repository.load(info.id).to_dict() == original
    assert template.to_dict() == original


def test_search_uses_unicode_casefold_and_canonical_normalization(repository):
    first = repository.save(Template(name="Straße — Diário"))
    repository.save(Template(name="Cinema"))
    assert [row.id for row in repository.list_layouts("STRASSE")] == [first.id]
    assert [row.id for row in repository.list_layouts("DIA\u0301RIO")] == [first.id]
    assert repository.list_layouts("unknown") == []
    assert len(repository.list_layouts()) == 2


def test_assets_are_copied_and_load_after_library_moves(repository, tmp_path):
    template = image_template(tmp_path)
    source = Path(template.elements[0].image_path)
    info = repository.save(template)
    data = json.loads((info.folder / "document.json").read_text(encoding="utf-8"))
    stored_path = data["elements"][0]["image_path"]
    assert not Path(stored_path).is_absolute()
    assert stored_path.startswith("assets/")
    assert template.elements[0].image_path == str(source)
    source.unlink()
    moved = tmp_path / "moved"
    shutil.move(str(repository.root), moved)
    from receipt_designer.library import LibraryRepository
    loaded = LibraryRepository(moved).load(info.id)
    resolved = Path(loaded.elements[0].image_path)
    assert resolved.is_absolute()
    assert resolved.is_relative_to(moved)
    assert Image.open(resolved).size == (5, 7)


def test_same_named_assets_keep_distinct_contents(repository, tmp_path):
    first = image_template(tmp_path)
    second_dir = tmp_path / "other"
    second_dir.mkdir()
    second = image_template(second_dir)
    Image.new("RGB", (9, 11), "white").save(second.elements[0].image_path)
    first.elements.extend(second.elements)
    info = repository.save(first)
    loaded = repository.load(info.id)
    paths = [Path(element.image_path) for element in loaded.elements]
    assert paths[0] != paths[1]
    assert [Image.open(path).size for path in paths] == [(5, 7), (9, 11)]


def test_duplicate_assets_are_independent_of_original(repository, tmp_path):
    original = repository.save(image_template(tmp_path), preview=Image.new("RGB", (5, 7)))
    duplicate = repository.duplicate(original.id, "Second")
    assert duplicate.id != original.id
    assert repository.load(original.id).name == "Image layout"
    assert repository.load(duplicate.id).name == "Second"
    assert duplicate.thumbnail and duplicate.thumbnail.exists()
    original_asset = Path(repository.load(original.id).elements[0].image_path)
    duplicate_asset = Path(repository.load(duplicate.id).elements[0].image_path)
    assert duplicate_asset != original_asset
    original_asset.write_bytes(b"changed")
    assert Image.open(duplicate_asset).size == (5, 7)


def test_rename_updates_document_without_changing_id(repository):
    info = repository.save(Template(name="First"), preview=Image.new("RGB", (3, 4)))
    renamed = repository.rename(info.id, "Novo nome")
    assert renamed.id == info.id
    assert renamed.name == "Novo nome"
    assert repository.load(info.id).name == "Novo nome"
    assert Image.open(renamed.thumbnail).size == (3, 4)
    assert len(repository.list_layouts()) == 1


def test_trash_and_restore_keep_document_assets_and_thumbnail(repository, tmp_path):
    info = repository.save(image_template(tmp_path), preview=Image.new("RGB", (3, 4)))
    repository.trash(info.id)
    assert repository.list_layouts() == []
    assert (repository.root / ".trash" / info.id / "document.json").is_file()
    with pytest.raises(FileNotFoundError):
        repository.load(info.id)
    repository.restore(info.id)
    loaded = repository.load(info.id)
    assert loaded.name == "Image layout"
    assert Image.open(loaded.elements[0].image_path).size == (5, 7)
    assert info.thumbnail.exists()


def test_missing_asset_does_not_replace_existing_layout(repository, tmp_path):
    info = repository.save(Template(name="Original"))
    replacement = image_template(tmp_path, "Replacement")
    Path(replacement.elements[0].image_path).unlink()
    with pytest.raises(FileNotFoundError):
        repository.save(replacement, layout_id=info.id)
    assert repository.load(info.id).name == "Original"
    assert len(repository.list_layouts()) == 1


@pytest.mark.parametrize("resource", ["../outside.png", "assets/../../outside.png",
                                      "..\\outside.png", "/outside.png", "C:/outside.png"])
def test_loading_rejects_resources_outside_layout(repository, resource):
    info = repository.save(Template(name="Valid"))
    path = info.folder / "document.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["elements"] = [{"kind": "image", "image_path": resource}]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        repository.load(info.id)
    assert json.loads(path.read_text(encoding="utf-8"))["elements"][0]["image_path"] == resource


def test_loading_missing_internal_asset_reports_error(repository, tmp_path):
    info = repository.save(image_template(tmp_path))
    asset = Path(repository.load(info.id).elements[0].image_path)
    asset.unlink()
    with pytest.raises(FileNotFoundError):
        repository.load(info.id)


def test_failed_publish_rolls_back_whole_previous_layout(repository, tmp_path, monkeypatch):
    info = repository.save(image_template(tmp_path, "Original"), preview=Image.new("RGB", (3, 4)))
    before = {str(p.relative_to(info.folder)): p.read_bytes()
              for p in info.folder.rglob("*") if p.is_file()}
    replace = os.replace

    def fail_publish(source, destination):
        if Path(destination) == info.folder and Path(source).name.startswith(".staging-"):
            raise OSError("simulated storage failure")
        return replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_publish)
    with pytest.raises(OSError, match="storage failure"):
        repository.save(Template(name="Replacement"), layout_id=info.id,
                        preview=Image.new("RGB", (9, 9)))
    after = {str(p.relative_to(info.folder)): p.read_bytes()
             for p in info.folder.rglob("*") if p.is_file()}
    assert after == before
    assert repository.load(info.id).name == "Original"
    assert sorted(p.name for p in repository.root.iterdir()) == [info.id]


def test_nonserializable_document_leaves_original_unchanged(repository):
    info = repository.save(Template(name="Original"))
    replacement = Template(name="Replacement", elements=[
        Element(kind="text", x=0, y=0, w=1, h=1, data={"unsupported": object()})
    ])
    with pytest.raises(TypeError):
        repository.save(replacement, layout_id=info.id)
    assert repository.load(info.id).name == "Original"
    assert sorted(p.name for p in repository.root.iterdir()) == [info.id]


@pytest.mark.parametrize("identifier", ["../escape", "", "not-a-uuid"])
def test_invalid_ids_cannot_read_or_change_outside_library(repository, identifier):
    for operation in (repository.load, repository.trash, repository.restore):
        with pytest.raises(ValueError):
            operation(identifier)
    with pytest.raises(ValueError):
        repository.save(Template(), layout_id=identifier)


def test_update_reuses_assets_and_keeps_only_current_document(repository, tmp_path):
    info = repository.save(image_template(tmp_path))
    template = repository.load(info.id)
    template.name = "Changed"
    replacement = repository.save(template, layout_id=info.id)
    assert replacement.id == info.id
    assert repository.load(info.id).name == "Changed"
    assert Image.open(repository.load(info.id).elements[0].image_path).size == (5, 7)
    assert sorted(p.name for p in repository.root.iterdir()) == [info.id]


def test_empty_preview_is_supported(repository):
    info = repository.save(Template())
    assert info.thumbnail is None
    assert repository.list_layouts()[0].thumbnail is None


def test_opening_library_recovers_interrupted_replacement(repository, tmp_path):
    info = repository.save(image_template(tmp_path, "Last valid document"))
    backup = repository.root / f".backup-{info.id}-{'a' * 32}"
    os.replace(info.folder, backup)
    # Equivalent to interruption between moving the old folder aside and
    # publishing the prepared replacement.
    from receipt_designer.library import LibraryRepository
    reopened = LibraryRepository(repository.root)
    assert reopened.load(info.id).name == "Last valid document"
    assert Image.open(reopened.load(info.id).elements[0].image_path).size == (5, 7)
    assert not backup.exists()


def test_opening_library_discards_finished_save_backup_without_reverting(repository):
    info = repository.save(Template(name="Old"))
    backup = repository.root / f".backup-{info.id}-{'b' * 32}"
    shutil.copytree(info.folder, backup)
    repository.rename(info.id, "New")
    from receipt_designer.library import LibraryRepository
    reopened = LibraryRepository(repository.root)
    assert reopened.load(info.id).name == "New"
    assert not backup.exists()


@pytest.mark.parametrize("malformed", [[], None, {"name": 23}, {"updated_at": 23}])
def test_damaged_metadata_does_not_hide_other_layouts(repository, malformed):
    healthy = repository.save(Template(name="Healthy"))
    damaged = repository.save(Template(name="Damaged"))
    if isinstance(malformed, dict):
        metadata = json.loads((damaged.folder / "metadata.json").read_text(encoding="utf-8"))
        metadata.update(malformed)
    else:
        metadata = malformed
    (damaged.folder / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert [row.name for row in repository.list_layouts()] == ["Healthy"]
    assert repository.load(healthy.id).name == "Healthy"
    assert (damaged.folder / "document.json").exists()


def test_list_trashed_search_survives_restart_and_supports_restore(repository):
    info = repository.save(Template(name="Straße Diário"))
    repository.trash(info.id)
    from receipt_designer.library import LibraryRepository
    reopened = LibraryRepository(repository.root)
    assert reopened.list_layouts() == []
    trashed = reopened.list_trashed("STRASSE")
    assert [entry.id for entry in trashed] == [info.id]
    assert trashed[0].folder == repository.root / ".trash" / info.id
    assert reopened.list_trashed("cinema") == []
    reopened.restore(trashed[0].id)
    assert reopened.list_trashed() == []
    assert reopened.load(info.id).name == "Straße Diário"


def test_list_trashed_before_first_deletion_is_empty(repository):
    assert repository.list_trashed() == []
