"""Personal library gallery and document navigation, independent of MainWindow."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from ..core.models import Element, Template
from ..library import LibraryRepository
from . import persistence


class LibraryPage(QtWidgets.QWidget):
    open_requested = QtCore.Signal(str)
    new_requested = QtCore.Signal()
    duplicate_requested = QtCore.Signal(str)
    rename_requested = QtCore.Signal(str)
    trash_requested = QtCore.Signal(str)
    restore_requested = QtCore.Signal(str)
    root_requested = QtCore.Signal()

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._last_trashed = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QtWidgets.QLabel('A minha biblioteca')
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(QtWidgets.QLabel('Modelos editáveis, guardados neste computador.'))
        row = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText('Pesquisar modelos…')
        self.search.setClearButtonEnabled(True)
        row.addWidget(self.search, 1)
        self.show_trash = QtWidgets.QCheckBox('Lixo')
        row.addWidget(self.show_trash)
        new = QtWidgets.QPushButton('Novo modelo')
        new.clicked.connect(self.new_requested)
        row.addWidget(new)
        choose = QtWidgets.QPushButton('Pasta da biblioteca…')
        choose.clicked.connect(self.root_requested)
        row.addWidget(choose)
        layout.addLayout(row)
        self.root_label = QtWidgets.QLabel()
        self.root_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.root_label)
        self.list = QtWidgets.QListWidget()
        self.list.setViewMode(QtWidgets.QListView.IconMode)
        self.list.setResizeMode(QtWidgets.QListView.Adjust)
        self.list.setMovement(QtWidgets.QListView.Static)
        self.list.setIconSize(QtCore.QSize(140, 180))
        self.list.setGridSize(QtCore.QSize(180, 220))
        self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(lambda item: self.open_requested.emit(item.data(QtCore.Qt.UserRole)) if not self.show_trash.isChecked() else None)
        layout.addWidget(self.list, 1)
        self.empty_label = QtWidgets.QLabel('Ainda não há modelos. Crie o primeiro ou importe um ficheiro JSON no editor.')
        layout.addWidget(self.empty_label)
        buttons = QtWidgets.QHBoxLayout()
        self._normal_buttons = []
        for label, signal in [('Abrir', self.open_requested), ('Duplicar', self.duplicate_requested), ('Mudar nome…', self.rename_requested), ('Mover para o lixo', self.trash_requested)]:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda checked=False, s=signal: self._emit_selected(s))
            buttons.addWidget(button)
            self._normal_buttons.append(button)
        self.restore_button = QtWidgets.QPushButton('Restaurar último eliminado')
        self.restore_button.setEnabled(False)
        self.restore_button.clicked.connect(self._restore_selected)
        buttons.addWidget(self.restore_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.search.textChanged.connect(self.refresh)
        self.show_trash.toggled.connect(self.refresh)
        self.list.itemSelectionChanged.connect(self._update_buttons)
        self.refresh()

    def _emit_selected(self, signal):
        item = self.list.currentItem()
        if item:
            signal.emit(item.data(QtCore.Qt.UserRole))

    def _restore_selected(self):
        item = self.list.currentItem()
        id = item.data(QtCore.Qt.UserRole) if self.show_trash.isChecked() and item else self._last_trashed
        if id:
            self.restore_requested.emit(id)

    def _update_buttons(self):
        selected = self.list.currentItem() is not None
        for button in self._normal_buttons:
            button.setEnabled(selected and not self.show_trash.isChecked())
        self.restore_button.setEnabled((self.show_trash.isChecked() and selected) or (not self.show_trash.isChecked() and self._last_trashed is not None))

    def refresh(self, *_):
        selected = self.list.currentItem()
        selected_id = selected.data(QtCore.Qt.UserRole) if selected else None
        self.list.clear()
        self.root_label.setText(str(self.repository.root))
        infos = self.repository.list_trashed(self.search.text()) if self.show_trash.isChecked() else self.repository.list_layouts(self.search.text())
        for info in infos:
            item = QtWidgets.QListWidgetItem(info.name)
            item.setData(QtCore.Qt.UserRole, info.id)
            item.setToolTip(f'{info.name}\n{info.updated_at}')
            if info.thumbnail and Path(info.thumbnail).exists():
                item.setIcon(QtGui.QIcon(str(info.thumbnail)))
            self.list.addItem(item)
            if info.id == selected_id:
                self.list.setCurrentItem(item)
        self.empty_label.setText('O lixo está vazio.' if self.show_trash.isChecked() else 'Ainda não há modelos. Crie o primeiro ou importe um ficheiro JSON no editor.')
        self.empty_label.setVisible(self.list.count() == 0)
        self._update_buttons()


def snapshot(mw, *, commit=True):
    """Copy the full model, replacing only the scene-owned elements."""
    if commit and mw._inline_editor.isEditing():
        mw._inline_editor.commitEdit()
    template = copy.deepcopy(mw.template)
    template.elements = [Element.from_dict(e) for e in persistence._collect_elements(mw)]
    return template


def signature(mw):
    return json.dumps(snapshot(mw, commit=False).to_dict(), sort_keys=True, ensure_ascii=False)


def set_clean(mw):
    mw._clean_document_signature = signature(mw)
    mw._has_unsaved_changes = False
    mw.undo_stack.setClean()


def set_pending_save(mw):
    """No saved baseline exists for this new, imported or recovered state.

    An empty signature cannot match a serialized document, so queued scene
    repaints cannot clear this state before an explicit save or discard.
    """
    mw._clean_document_signature = ''
    mw._has_unsaved_changes = True
    mw.undo_stack.resetClean()


def initialize(mw, root=None):
    default = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)) / 'Receipt Designer' / 'Biblioteca'
    root = root or os.environ.get('RECEIPT_DESIGNER_LIBRARY') or mw.settings.value('library/root', str(default))
    mw.library = LibraryRepository(Path(root))
    try:
        from ..personal_templates import ensure_personal_templates
    except ImportError:
        pass
    else:
        ensure_personal_templates(mw.library)
    mw.current_layout_id = None
    mw.editor_page = mw.takeCentralWidget()
    mw.pages = QtWidgets.QStackedWidget(mw)
    mw.library_page = LibraryPage(mw.library)
    mw.pages.addWidget(mw.library_page)
    mw.pages.addWidget(mw.editor_page)
    mw.setCentralWidget(mw.pages)
    p = mw.library_page
    p.open_requested.connect(mw.open_layout)
    p.new_requested.connect(lambda: mw.new_layout())
    p.duplicate_requested.connect(lambda id: mw.duplicate_layout(id))
    p.rename_requested.connect(lambda id: mw.rename_layout(id))
    p.trash_requested.connect(mw.trash_layout)
    p.restore_requested.connect(mw.restore_layout)
    p.root_requested.connect(mw.choose_library_root)
    set_clean(mw)
    show_page(mw, False)


def show_page(mw, editor):
    if not editor and mw.pages.currentWidget() is mw.editor_page:
        mw._editor_dock_visibility = {d: d.isVisible() for d in mw.findChildren(QtWidgets.QDockWidget)}
    mw.pages.setCurrentWidget(mw.editor_page if editor else mw.library_page)
    for action in mw._editor_only_actions:
        action.setEnabled(editor)
    mw._document_undo_action.setEnabled(editor and mw.undo_stack.canUndo())
    mw._document_redo_action.setEnabled(editor and mw.undo_stack.canRedo())
    for dock in mw.findChildren(QtWidgets.QDockWidget):
        dock.setVisible(getattr(mw, '_editor_dock_visibility', {}).get(dock, True) if editor else False)
    for toolbar in mw.findChildren(QtWidgets.QToolBar):
        toolbar.setVisible(editor)
    mw.setWindowTitle(f'{mw.template.name} — Receipt Lab' if editor else 'Biblioteca — Receipt Lab')
    if not editor:
        mw.library_page.refresh()


def guard(mw):
    if mw._inline_editor.isEditing():
        mw._inline_editor.commitEdit()
    if not mw._has_unsaved_changes and signature(mw) == getattr(mw, '_clean_document_signature', ''):
        return True
    reply = QtWidgets.QMessageBox.warning(mw, 'Alterações por guardar', 'Guardar as alterações antes de continuar?', QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Save)
    if reply == QtWidgets.QMessageBox.Save:
        return save(mw)
    if reply == QtWidgets.QMessageBox.Discard:
        mw._has_unsaved_changes = False
        mw._delete_autosave_file()
        return True
    return False


def install_template(mw, template, layout_id=None, path=None, *, saved=True):
    mw._inline_editor.cancelEdit()
    mw._clear_alignment_guides()
    mw._clear_column_guides()
    mw.undo_stack.clear()
    mw._cut_guides = []
    mw.template = template
    mw.current_layout_id = layout_id
    mw._current_file_path = path
    persistence._build_scene_from_template(mw)
    for widget, value in [(mw.cb_w_mm, template.width_mm), (mw.cb_h_mm, template.height_mm)]:
        with QtCore.QSignalBlocker(widget):
            widget.setCurrentText(f'{value:g} mm')
    mw._update_cut_guides()
    if saved:
        set_clean(mw)
    else:
        set_pending_save(mw)
    show_page(mw, True)


def new(mw, name=None):
    if not guard(mw):
        return False
    if name is None:
        name, ok = QtWidgets.QInputDialog.getText(mw, 'Novo modelo', 'Nome:', text='Sem título')
        if not ok or not name.strip():
            return False
    install_template(mw, Template(name=name.strip()), saved=False)
    return True


def open_layout(mw, id):
    if not guard(mw):
        return False
    try:
        template = mw.library.load(id)
    except Exception as exc:
        QtWidgets.QMessageBox.critical(mw, 'Não foi possível abrir', str(exc))
        return False
    install_template(mw, template, id)
    return True


def save(mw):
    try:
        template = snapshot(mw)
        from .print_render import prepare_print_job
        from ..printing.jobs import ThermalProfile
        preview = prepare_print_job(template, ThermalProfile.from_config(mw.printer_cfg)).preview
        info = mw.library.save(template, layout_id=mw.current_layout_id, preview=preview)
    except Exception as exc:
        QtWidgets.QMessageBox.critical(mw, 'Não foi possível guardar', str(exc))
        return False
    # Rebind scene resources to owned copies; the external source may disappear.
    stored = mw.library.load(info.id)
    scene_items = [item for item in mw.scene.items(QtCore.Qt.AscendingOrder) if isinstance(item, persistence.SERIALIZABLE_ITEM_TYPES)]
    for item, element in zip(scene_items, stored.elements):
        if hasattr(item, 'elem') and element.image_path:
            item.elem.image_path = element.image_path
            item.update()
    mw.template = stored
    mw.current_layout_id = info.id
    # Subsequent image imports resolve against the library document.
    mw._current_file_path = str(info.folder / 'document.json')
    set_clean(mw)
    mw._delete_autosave_file()
    mw.library_page.refresh()
    mw.statusBar().showMessage('Modelo guardado na biblioteca', 3000)
    return True


def show_library(mw):
    if not guard(mw):
        return False
    # Discard actually abandons the document: gallery actions must never save it later.
    install_template(mw, Template())
    show_page(mw, False)
    return True


def library_operation(mw, operation, id, name=None):
    try:
        if operation in ('rename', 'duplicate'):
            if name is None:
                old = mw.library.load(id).name
                name, ok = QtWidgets.QInputDialog.getText(mw, 'Mudar nome' if operation == 'rename' else 'Duplicar modelo', 'Nome:', text=old if operation == 'rename' else f'{old} — cópia')
                if not ok or not name.strip():
                    return None
            result = getattr(mw.library, operation)(id, name.strip())
            if operation == 'rename' and mw.current_layout_id == id:
                was_dirty = mw._has_unsaved_changes or signature(mw) != mw._clean_document_signature
                mw.template.name = name.strip()
                if not was_dirty:
                    set_clean(mw)
                else:
                    mw._has_unsaved_changes = True
        else:
            result = getattr(mw.library, operation)(id)
            if operation == 'trash':
                mw.library_page._last_trashed = id
                mw.library_page.restore_button.setEnabled(True)
            elif operation == 'restore':
                if mw.library_page._last_trashed == id:
                    mw.library_page._last_trashed = None
                mw.library_page.restore_button.setEnabled(False)
        mw.library_page.refresh()
        return result if result is not None else True
    except Exception as exc:
        QtWidgets.QMessageBox.critical(mw, 'Biblioteca', str(exc))
        return None


def choose_root(mw):
    if os.environ.get('RECEIPT_DESIGNER_LIBRARY'):
        QtWidgets.QMessageBox.information(mw, 'Pasta da biblioteca', 'A pasta está definida pela variável RECEIPT_DESIGNER_LIBRARY.')
        return False
    path = QtWidgets.QFileDialog.getExistingDirectory(mw, 'Escolher pasta da biblioteca', str(mw.library.root))
    if not path or not guard(mw):
        return False
    try:
        repository = LibraryRepository(Path(path))
        repository.list_layouts()
    except Exception as exc:
        QtWidgets.QMessageBox.critical(mw, 'Pasta indisponível', str(exc))
        return False
    mw.library = repository
    mw.library_page.repository = repository
    mw.library_page._last_trashed = None
    mw.library_page.restore_button.setEnabled(False)
    mw.settings.setValue('library/root', str(path))
    install_template(mw, Template())
    show_page(mw, False)
    return True
