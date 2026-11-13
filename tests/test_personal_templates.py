from receipt_designer.core.models import Element, Template
from receipt_designer.library import LibraryRepository
from receipt_designer.personal_templates import make_daily_template, make_cinema_template, ensure_personal_templates
import json
import os
from pathlib import Path
import pytest


def test_daily_is_editable_with_complete_chess_position():
    template = Template.from_dict(make_daily_template().to_dict())
    assert template.name == 'Diário de bordo'
    assert sum(e.data.get('role') == 'chess-square' for e in template.elements) == 64
    assert {e.data['square']: e.text for e in template.elements if e.data.get('role') == 'chess-piece'} == {'h8':'♚', 'f6':'♔', 'g6':'♕'}
    assert any(e.kind == 'text' and '{{var:task_1}}' in e.text for e in template.elements)
    assert any(e.letter_spacing_px > 0 for e in template.elements if e.kind == 'text')


def test_cinema_title_and_cut_are_native_editable_data():
    template = Template.from_dict(make_cinema_template().to_dict())
    assert template.variable_manager.get_variable('film') == 'INTERSTELLAR'
    assert len(template.cut_markers) == 1
    assert template.cut_markers[0].position_mm == 129.375
    assert template.cut_markers[0].mode == 'full'
    assert any(e.kind == 'text' and '{{var:film}}' in e.text for e in template.elements)
    assert not any(e.kind == 'image' for e in template.elements)


def test_seed_runs_once_and_preserves_renamed_modified_layout(tmp_path):
    repository = LibraryRepository(tmp_path / 'library')
    ensure_personal_templates(repository)
    entries = repository.list_layouts()
    assert len(entries) == 2
    entry = next(e for e in entries if e.name == 'Cinema no sofá')
    template = repository.load(entry.id)
    template.name = 'O meu cinema'
    template.variable_manager.set_variable('film', 'OUTRO FILME')
    repository.save(template, layout_id=entry.id)
    ensure_personal_templates(repository)
    reopened = repository.load(entry.id)
    assert len(repository.list_layouts()) == 2
    assert reopened.name == 'O meu cinema'
    assert reopened.variable_manager.get_variable('film') == 'OUTRO FILME'


def test_seed_does_not_recreate_deleted_personal_layouts(tmp_path):
    repository = LibraryRepository(tmp_path / 'library')
    ensure_personal_templates(repository)
    for entry in repository.list_layouts():
        repository.trash(entry.id)
    ensure_personal_templates(LibraryRepository(repository.root))
    assert repository.list_layouts() == []
    assert len(repository.list_trashed()) == 2


def test_failed_seed_rolls_back_partial_creations_and_can_retry(tmp_path, monkeypatch):
    repository = LibraryRepository(tmp_path / 'library')
    save = repository.save
    calls = 0
    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError('seed storage failure')
        return save(*args, **kwargs)
    monkeypatch.setattr(repository, 'save', fail_second)
    with pytest.raises(OSError, match='seed storage failure'):
        ensure_personal_templates(repository)
    assert repository.list_layouts() == []
    monkeypatch.setattr(repository, 'save', save)
    ensure_personal_templates(repository)
    assert len(repository.list_layouts()) == 2


def test_seed_marker_records_ids_and_write_failure_keeps_retry_safe(tmp_path, monkeypatch):
    repository = LibraryRepository(tmp_path / 'library')
    replace = os.replace
    def fail_marker(source, destination):
        if Path(destination).name == '.personal-layouts-v1.json':
            raise OSError('marker storage failure')
        return replace(source, destination)
    monkeypatch.setattr(os, 'replace', fail_marker)
    with pytest.raises(OSError, match='marker storage failure'):
        ensure_personal_templates(repository)
    assert repository.list_layouts() == []
    monkeypatch.setattr(os, 'replace', replace)
    ensure_personal_templates(repository)
    state = json.loads((repository.root / '.personal-layouts-v1.json').read_text(encoding='utf-8'))
    assert set(state['layouts'].values()) == {entry.id for entry in repository.list_layouts()}


def test_interrupted_seed_adopts_existing_native_layout_instead_of_duplicate(tmp_path):
    repository = LibraryRepository(tmp_path / 'library')
    template = make_daily_template()
    template.name = 'Já comecei a editar'
    template.variable_manager.set_variable('task_1', 'Preservar esta tarefa')
    partial = repository.save(template)
    ensure_personal_templates(LibraryRepository(repository.root))
    assert len(repository.list_layouts()) == 2
    assert repository.load(partial.id).name == 'Já comecei a editar'
    assert repository.load(partial.id).variable_manager.get_variable('task_1') == 'Preservar esta tarefa'


def test_seed_preserves_existing_legacy_elements_with_empty_extra_data(tmp_path):
    repository = LibraryRepository(tmp_path / 'library')
    user_layout = repository.save(Template(name='Existing', elements=[
        Element('text', 0, 0, 40, 20, text='Keep me', data=None)
    ]))
    ensure_personal_templates(repository)
    assert len(repository.list_layouts()) == 3
    assert repository.load(user_layout.id).elements[0].text == 'Keep me'


def test_daily_board_coordinates_and_portable_pattern(tmp_path):
    template = make_daily_template()
    squares = {e.data['square']: e for e in template.elements if e.data.get('role') == 'chess-square'}
    assert set(squares) == {file + str(rank) for file in 'abcdefgh' for rank in range(1, 9)}
    assert squares['a8'].x < squares['h8'].x
    assert squares['a8'].y < squares['a1'].y
    assert all(e.stroke_px * 203.2 / 203 >= 2 for e in squares.values())
    repository = LibraryRepository(tmp_path / 'library')
    info = repository.save(template)
    assert all(Path(e.image_path).is_file() for e in repository.load(info.id).elements if e.kind == 'image')
    assert not any(e.kind == 'image' and e.w > template.width_px / 2 for e in template.elements)


@pytest.mark.parametrize('factory,height', [(make_daily_template, 1835), (make_cinema_template, 1545)])
def test_native_render_preserves_print_size_and_content(factory, height):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6 import QtWidgets
    from receipt_designer.ui.print_render import prepare_print_job
    from receipt_designer.printing.jobs import ThermalProfile
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    template = factory()
    job = prepare_print_job(template, ThermalProfile())
    assert job.preview.size == (576, height)
    # The native masthead is visible; a missing title or clipped crop is detectable.
    region = job.preview.crop((100, 140, 485, 315 if height == 1545 else 245))
    assert region.convert('L').histogram()[0] > 4000
    if height == 1545:
        assert [part.image.height for part in job.parts] == [1035, 510]
        # A cut is physical metadata, without an imitation perforation in ink.
        assert job.preview.crop((0, 1024, 576, 1043)).getextrema() == (255, 255)
