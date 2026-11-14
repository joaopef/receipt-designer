"""Integration tests for library navigation and document identity."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6 import QtCore, QtWidgets
from receipt_designer.ui.main_window_impl import MainWindow

@pytest.fixture(scope='module')
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    # Recovery is an external, process-wide temporary file; do not read user work.
    monkeypatch.setattr(MainWindow, '_load_crash_recovery', lambda self: None)
    settings = QtCore.QSettings(str(tmp_path / 'settings.ini'), QtCore.QSettings.IniFormat)
    w = MainWindow(settings=settings, library_root=tmp_path / 'library')
    yield w
    from receipt_designer.ui.library_page import set_clean
    w._inline_editor.cancelEdit()
    set_clean(w)
    if not getattr(w, '_closed_by_test', False):
        w.close()
    qapp.processEvents()


def test_startup_is_library_and_new_opens_editor(window):
    assert window.pages.currentWidget() is window.library_page
    assert window.new_layout('Primeiro')
    assert window.pages.currentWidget() is window.editor_page
    assert window.template.name == 'Primeiro'
    assert window.current_layout_id is None


def test_saved_scene_reopens_and_new_does_not_overwrite(window):
    window.new_layout('Primeiro')
    window.add_text()
    assert window.save_layout()
    first = window.current_layout_id
    assert len(window.library.load(first).elements) == 1
    assert window.new_layout('Segundo')
    window.add_rect()
    assert window.save_layout()
    second = window.current_layout_id
    assert first != second
    assert window.open_layout(first)
    assert window.template.name == 'Primeiro'
    assert [e['kind'] for e in window._snapshot_template().to_dict()['elements']] == ['text']


@pytest.mark.parametrize('reply,expected', [(QtWidgets.QMessageBox.Cancel, False), (QtWidgets.QMessageBox.Discard, True), (QtWidgets.QMessageBox.Save, True)])
def test_unsaved_navigation_respects_choice(window, monkeypatch, reply, expected):
    window.new_layout('Por guardar')
    window.add_text()
    monkeypatch.setattr(QtWidgets.QMessageBox, 'warning', lambda *args, **kwargs: reply)
    assert window.show_library() is expected
    if reply == QtWidgets.QMessageBox.Cancel:
        assert window.template.name == 'Por guardar'
        assert window.pages.currentWidget() is window.editor_page
    elif reply == QtWidgets.QMessageBox.Save:
        saved = window.library.list_layouts('Por guardar')
        assert len(saved) == 1
        assert len(window.library.load(saved[0].id).elements) == 1


def test_failed_save_keeps_current_document_and_blocks_navigation(window, monkeypatch):
    window.new_layout('Valioso')
    window.add_text()
    monkeypatch.setattr(QtWidgets.QMessageBox, 'warning', lambda *a, **kw: QtWidgets.QMessageBox.Save)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'critical', lambda *a, **kw: None)
    def fail(*a, **kw):
        raise OSError('full disk')
    monkeypatch.setattr(window.library, 'save', fail)
    assert not window.show_library()
    assert window.template.name == 'Valioso'
    assert window.current_layout_id is None
    assert window._has_unsaved_changes


def test_gallery_search_duplicate_rename_trash_restore(window):
    window.new_layout('Café')
    window.save_layout()
    first = window.current_layout_id
    copy = window.duplicate_layout(first, 'Cinema')
    assert window.rename_layout(copy.id, 'Sessão')
    window.library_page.search.setText('sessão')
    assert window.library_page.list.count() == 1
    assert window.library_page.list.item(0).text() == 'Sessão'
    assert window.trash_layout(copy.id)
    assert window.library_page.list.count() == 0
    assert window.restore_layout(copy.id)
    assert window.library_page.list.count() == 1
    assert window.library.load(first).name == 'Café'

def test_cut_markers_undo_and_overlay_adds_no_raster_ink(window):
    from receipt_designer.core.models import CutMarker
    from receipt_designer.ui.dialogs.cut_markers import SetCutMarkersCommand
    from receipt_designer.core.render import scene_to_image
    window.new_layout('Cortes')
    window.undo_stack.push(SetCutMarkersCommand(window, [CutMarker(20, 'partial')]))
    assert window._snapshot_template().cut_markers[0].position_mm == 20
    image = scene_to_image(window.scene)
    assert all(image.pixelColor(x, 159).value() == 255 for x in range(image.width()))
    window.undo_stack.undo()
    assert window.template.cut_markers == []
    window.undo_stack.redo()
    assert window.template.cut_markers[0].mode == 'partial'


def test_preview_submits_same_prepared_job_once(window, monkeypatch):
    from receipt_designer.ui import main_window_impl as main
    from receipt_designer.ui import print_render
    window.new_layout('Prévia')
    window.add_text()
    prepared, submitted = [], []
    real = print_render.prepare_print_job
    def prepare(*args):
        job = real(*args)
        prepared.append(job)
        return job
    monkeypatch.setattr(print_render, 'prepare_print_job', prepare)
    monkeypatch.setattr(main.PrintPreviewDialog, 'exec', lambda self: QtWidgets.QDialog.Accepted)
    monkeypatch.setattr(window, '_submit_print_job', lambda job: submitted.append(job))
    window.preview_print()
    assert len(prepared) == 1
    assert len(submitted) == 1
    assert submitted[0] is prepared[0]
    assert submitted[0].preview.width == 576


def test_import_clears_library_identity_and_preserves_original(window, tmp_path):
    import json
    window.new_layout('Original')
    window.add_text()
    window.save_layout()
    original = window.current_layout_id
    path = tmp_path / 'external.json'
    path.write_text(json.dumps({'name': 'Importado', 'elements': []}), encoding='utf-8')
    window._load_template_path(str(path))
    assert window.current_layout_id is None
    assert window.template.name == 'Importado'
    assert window.save_layout()
    assert window.current_layout_id != original
    assert window.library.load(original).name == 'Original'


def test_export_and_autosave_preserve_cut_metadata(window, monkeypatch, tmp_path):
    import json
    from receipt_designer.core.models import CutMarker
    from receipt_designer.ui import persistence
    window.new_layout('Metadados')
    window.template.cut_markers = [CutMarker(20, 'full')]
    window.add_text()
    path = tmp_path / 'export.json'
    monkeypatch.setattr(QtWidgets.QFileDialog, 'getSaveFileName', lambda *a, **kw: (str(path), ''))
    window.export_template()
    assert json.loads(path.read_text(encoding='utf-8'))['cut_markers'] == [{'position_mm': 20, 'mode': 'full'}]
    assert window.current_layout_id is None
    assert window._has_unsaved_changes
    monkeypatch.setattr(QtCore.QStandardPaths, 'writableLocation', lambda location: str(tmp_path))
    persistence.auto_save(window)
    assert json.loads((tmp_path / 'receipt_designer_autosave.json').read_text(encoding='utf-8'))['cut_markers'][0]['position_mm'] == 20

def test_printer_dialog_defaults_and_routing_are_explicit(qapp, monkeypatch):
    from receipt_designer.ui.dialogs.printer_config import show_printer_config_dialog
    def accept(dialog):
        source = dialog.findChild(QtWidgets.QLineEdit, 'source_ip')
        assert source is not None
        assert source.text() == ''
        buttons = dialog.findChild(QtWidgets.QDialogButtonBox)
        buttons.button(QtWidgets.QDialogButtonBox.Ok).click()
        return QtWidgets.QDialog.Accepted
    monkeypatch.setattr(QtWidgets.QDialog, 'exec', accept)
    cfg = show_printer_config_dialog({})
    assert cfg['host'] == '192.168.1.10'
    assert cfg['port'] == 9100
    assert cfg['width_px'] == 576
    assert cfg['threshold'] == 170
    assert cfg['source_ip'] == ''
    assert cfg['interface_index'] is None
    assert cfg['printable_width_mm'] == 72


def test_recovery_preserves_identity_only_for_same_library(window, monkeypatch, tmp_path):
    from receipt_designer.ui import persistence
    window.new_layout('Recuperado')
    window.add_text()
    window.save_layout()
    original = window.current_layout_id
    window.add_rect()
    window._has_unsaved_changes = True
    monkeypatch.setattr(QtCore.QStandardPaths, 'writableLocation', lambda location: str(tmp_path))
    persistence.auto_save(window)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question', lambda *a, **kw: QtWidgets.QMessageBox.Yes)
    # Simulate a freshly constructed editor with no assigned identity.
    window.current_layout_id = None
    persistence.load_crash_recovery(window)
    assert window.current_layout_id == original
    assert window.template.name == 'Recuperado'
    assert len(window._snapshot_template().elements) == 2
    assert window._has_unsaved_changes

def test_trash_is_visible_and_restorable_after_gallery_restart(window):
    from receipt_designer.ui.library_page import LibraryPage
    window.new_layout('A recuperar')
    window.save_layout()
    layout_id = window.current_layout_id
    window.trash_layout(layout_id)
    page = LibraryPage(window.library)
    try:
        page.show_trash.setChecked(True)
        assert page.list.count() == 1
        restored = []
        page.restore_requested.connect(lambda id: restored.append(id))
        page.list.setCurrentRow(0)
        page.restore_button.click()
        assert restored == [layout_id]
    finally:
        page.deleteLater()

def test_save_rebinds_open_image_to_owned_library_asset(window, tmp_path, monkeypatch):
    from PIL import Image
    from receipt_designer.core.models import Element
    from receipt_designer.ui.items import GItem
    source = tmp_path / 'source.png'
    Image.new('RGB', (20, 20), 'black').save(source)
    window.new_layout('Imagem portátil')
    item = GItem(Element(kind='image', x=40, y=20, image_path=str(source), w=20, h=20))
    window.scene.addItem(item)
    assert window.save_layout()
    source.unlink()
    assert item.elem.image_path != str(source)
    assert window.save_layout()
    assert window.library.load(window.current_layout_id).elements[0].image_path


def test_rename_current_document_keeps_unsaved_edits_dirty(window):
    window.new_layout('Antes')
    window.add_text()
    window.save_layout()
    window.add_rect()
    window._has_unsaved_changes = True
    window.rename_layout(window.current_layout_id, 'Depois')
    assert window._has_unsaved_changes
    assert len(window._snapshot_template().elements) == 2
    assert len(window.library.load(window.current_layout_id).elements) == 1


def test_gallery_disables_document_save_print_and_insert_shortcuts(window):
    from PySide6 import QtGui
    actions = {action.text(): action for action in window.findChildren(QtGui.QAction)}
    assert not actions['Guardar na biblioteca'].isEnabled()
    assert not actions['Print…'].isEnabled()
    assert not actions['Text'].isEnabled()
    window.new_layout('Editor')
    assert actions['Guardar na biblioteca'].isEnabled()
    assert actions['Print…'].isEnabled()
    assert actions['Text'].isEnabled()

@pytest.mark.parametrize('trigger', ['timer', 'close'])
def test_variable_edit_event_autosaves_even_if_dirty_flag_becomes_stale(window, qapp, monkeypatch, tmp_path, trigger):
    import json
    from PySide6 import QtTest
    from receipt_designer.ui.variables import VariableDialog
    window.new_layout('Só variáveis')
    window.template.variable_manager.set_variable('film', 'Antes')
    window._refresh_variable_panel()
    assert window.save_layout()
    original = window.current_layout_id
    qapp.processEvents()
    assert not window._has_unsaved_changes
    panel = window.variable_panel
    for row in range(panel.list_widget.count()):
        if panel.list_widget.item(row).data(QtCore.Qt.UserRole) == 'film':
            panel.list_widget.setCurrentRow(row)
            break
    def edit(dialog):
        dialog.value_edit.setPlainText('Depois')
        return QtWidgets.QDialog.Accepted
    monkeypatch.setattr(VariableDialog, 'exec', edit)
    edit_button = next(button for button in panel.findChildren(QtWidgets.QPushButton) if button.text() == 'Edit')
    QtTest.QTest.mouseClick(edit_button, QtCore.Qt.LeftButton)
    assert window.template.variable_manager.get_variable('film') == 'Depois'
    assert window._has_unsaved_changes
    # Autosave must not depend on every mutation remembering to set this cache.
    window._has_unsaved_changes = False
    monkeypatch.setattr(QtCore.QStandardPaths, 'writableLocation', lambda location: str(tmp_path))
    if trigger == 'timer':
        window._auto_save_timer.timeout.emit()
    else:
        window.close()
        window._closed_by_test = True
    data = json.loads((tmp_path / 'receipt_designer_autosave.json').read_text(encoding='utf-8'))
    assert data['variables']['variables']['film'] == 'Depois'
    assert data['_autosave_layout_id'] == original
    assert window.library.load(original).variable_manager.get_variable('film') == 'Antes'


def test_snapshot_preview_and_saved_layout_preserve_equal_z_stacking(window):
    from receipt_designer.core.models import Element
    from receipt_designer.ui.items import create_item_from_element
    from receipt_designer.core.render import scene_to_image
    window.new_layout('Camadas')
    for color in ['#000000', '#ffffff']:
        item = create_item_from_element(Element(kind='rect', x=80, y=80, w=80, h=80, fill_color=color, stroke_color=color, z=0))
        window.scene.addItem(item)
    canvas = scene_to_image(window.scene)
    assert canvas.pixelColor(120, 120).value() == 255
    # Paper crop removes 4mm from each side; 120 design pixels maps near 88 output pixels.
    job = window._prepare_print_job()
    assert job.preview.convert('L').getpixel((88, 120)) == 255
    assert window.save_layout()
    id = window.current_layout_id
    assert window.show_library()
    assert window.open_layout(id)
    assert scene_to_image(window.scene).pixelColor(120, 120).value() == 255
    assert window._prepare_print_job().preview.convert('L').getpixel((88, 120)) == 255


def test_repaint_does_not_commit_inline_edit_and_explicit_save_keeps_typed_text(window, qapp):
    from receipt_designer.ui.items import GItem
    window.new_layout('Texto em linha')
    window.add_text()
    item = next(item for item in window.scene.items() if isinstance(item, GItem))
    assert window._inline_editor.startEditing(item)
    assert window._inline_editor.isEditing()
    qapp.processEvents()
    assert window._inline_editor.isEditing()
    editor = window._inline_editor
    editor._editor.setPlainText('Texto preservado')
    assert window.save_layout()
    assert not editor.isEditing()
    assert window.library.load(window.current_layout_id).elements[0].text == 'Texto preservado'

def test_open_layout_binds_variable_text_to_loaded_document(window):
    from receipt_designer.core.models import Template, Element
    from receipt_designer.ui.items import GItem
    template = Template(name='Variáveis carregadas')
    template.variable_manager.set_variable('film', 'FILME RESOLVIDO')
    template.elements = [Element(kind='text', x=40, y=20, w=300, h=40, text='{{var:film}}')]
    info = window.library.save(template)
    assert window.open_layout(info.id)
    item = next(item for item in window.scene.items() if isinstance(item, GItem))
    assert item._resolve_text(item.elem.text) == 'FILME RESOLVIDO'
    assert item.elem.text == '{{var:film}}'


def test_light_theme_keeps_controls_readable_with_dark_system_palette(window, qapp):
    from PySide6 import QtGui
    inherited = QtGui.QPalette()
    inherited.setColor(QtGui.QPalette.Button, QtGui.QColor('#d4d0c8'))
    inherited.setColor(QtGui.QPalette.ButtonText, QtGui.QColor('#ffffff'))
    qapp.setStyle('Windows')
    qapp.setPalette(inherited)
    window._apply_theme_mode(False)
    assert qapp.style().objectName().lower() == 'fusion'
    palette = qapp.palette()
    for background, foreground in [
        (QtGui.QPalette.Button, QtGui.QPalette.ButtonText),
        (QtGui.QPalette.Window, QtGui.QPalette.WindowText),
        (QtGui.QPalette.Base, QtGui.QPalette.Text),
    ]:
        assert palette.color(background).lightness() > 220
        assert palette.color(foreground).lightness() < 70

def test_recovered_variable_edit_survives_repaint_close_and_second_relaunch(window, qapp, monkeypatch, tmp_path):
    from receipt_designer.ui import persistence, library_page
    window.new_layout('Recuperação persistente')
    window.template.variable_manager.set_variable('film', 'Título original')
    assert window.save_layout()
    layout_id = window.current_layout_id
    qapp.processEvents()
    window.template.variable_manager.set_variable('film', 'Título recuperado')
    monkeypatch.setattr(QtCore.QStandardPaths, 'writableLocation', lambda location: str(tmp_path))
    window._auto_save()
    autosave = tmp_path / 'receipt_designer_autosave.json'
    assert autosave.exists()
    monkeypatch.setattr(MainWindow, '_load_crash_recovery', persistence.load_crash_recovery)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'question', lambda *a, **kw: QtWidgets.QMessageBox.Yes)
    opened = []
    try:
        fresh = MainWindow(settings=window.settings, library_root=window.library.root)
        opened.append(fresh)
        fresh.show()
        qapp.processEvents()
        assert fresh.current_layout_id == layout_id
        assert fresh.template.variable_manager.get_variable('film') == 'Título recuperado'
        assert persistence.has_unsaved_changes(fresh)
        # A navigation Cancel must keep recovery work even after queued repaint signals.
        monkeypatch.setattr(QtWidgets.QMessageBox, 'warning', lambda *a, **kw: QtWidgets.QMessageBox.Cancel)
        assert not fresh.show_library()
        fresh.close()
        opened.remove(fresh)
        assert autosave.exists()
        assert window.library.load(layout_id).variable_manager.get_variable('film') == 'Título original'
        again = MainWindow(settings=window.settings, library_root=window.library.root)
        opened.append(again)
        again.show()
        qapp.processEvents()
        assert again.current_layout_id == layout_id
        assert again.template.variable_manager.get_variable('film') == 'Título recuperado'
        assert persistence.has_unsaved_changes(again)
        assert again.save_layout()
        qapp.processEvents()
        assert not persistence.has_unsaved_changes(again)
        assert window.library.load(layout_id).variable_manager.get_variable('film') == 'Título recuperado'
    finally:
        for candidate in opened:
            library_page.set_clean(candidate)
            candidate.close()


@pytest.mark.parametrize('source', ['new', 'import'])
def test_unsaved_document_requires_save_after_queued_repaint(window, qapp, tmp_path, monkeypatch, source):
    import json
    from receipt_designer.ui import persistence
    if source == 'new':
        assert window.new_layout('Documento novo sem elementos')
    else:
        path = tmp_path / 'external.json'
        path.write_text(json.dumps({'name': 'Importado sem elementos', 'elements': []}), encoding='utf-8')
        window._load_template_path(str(path))
    window.show()
    qapp.processEvents()
    assert window.current_layout_id is None
    assert persistence.has_unsaved_changes(window)
    monkeypatch.setattr(QtWidgets.QMessageBox, 'warning', lambda *a, **kw: QtWidgets.QMessageBox.Cancel)
    assert not window.show_library()
    assert window.pages.currentWidget() is window.editor_page
    assert window.save_layout()
    qapp.processEvents()
    assert not persistence.has_unsaved_changes(window)
