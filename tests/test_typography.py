import pytest
from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from receipt_designer.core.models import Element
from receipt_designer.core.models import Template
from types import SimpleNamespace
from receipt_designer.ui.items import GItem
from receipt_designer.ui.properties import PropertiesPanel


@pytest.fixture(scope='module')
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def ink_width(item):
    item._ensure_cache(for_screen=False)
    image = item._cache_qimage
    columns = [x for x in range(image.width()) if any(
        image.pixelColor(x, y).alpha() > 100 and image.pixelColor(x, y).red() < 100
        for y in range(image.height())
    )]
    return max(columns) - min(columns) + 1


def test_letter_spacing_changes_visible_text_and_invalidates_cache(qapp):
    element = Element(kind='text', x=0, y=0, w=400, h=80,
                      text='MMMM', font_family='Arial', font_size=22)
    element.letter_spacing_px = 0
    item = GItem(element)
    original = ink_width(item)
    element.letter_spacing_px = 5
    expanded = ink_width(item)
    element.letter_spacing_px = -2
    condensed = ink_width(item)
    assert expanded >= original + 10
    assert condensed <= original - 4


def test_spacing_control_updates_document_with_undo(qapp):
    element = Element(kind='text', x=0, y=0, w=300, h=80, text='Cinema')
    element.letter_spacing_px = 0
    item = GItem(element)
    panel = PropertiesPanel()
    undo = QtGui.QUndoStack(panel)
    panel.set_undo_stack(undo)
    panel.set_target_from_selection([item])
    control = panel.findChild(QtWidgets.QDoubleSpinBox, 'letterSpacing')
    assert control is not None
    control.setValue(-1.5)
    assert element.letter_spacing_px == -1.5
    undo.undo()
    assert element.letter_spacing_px == 0
    panel.close()


def test_editing_a_variable_refreshes_the_visible_text(qapp):
    template = Template()
    template.variable_manager.set_variable('film', 'I')
    item = GItem(Element(kind='text', x=0, y=0, w=400, h=80,
                         text='{{var:film}}', font_size=22))
    item._main_window = SimpleNamespace(template=template)
    narrow = ink_width(item)
    template.variable_manager.set_variable('film', 'MMMM')
    assert ink_width(item) > narrow + 40


def test_upside_down_text_is_rotated_not_mirrored(qapp):
    item = GItem(Element(kind='text', x=0, y=0, w=130, h=55, text='F7', font_size=22))
    item._ensure_cache(for_screen=False)
    def render(use_item):
        image = QtGui.QImage(180, 120, QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.white)
        painter = QtGui.QPainter(image)
        painter.translate(150, 90)
        painter.rotate(180)
        if use_item:
            item.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
        else:
            painter.drawImage(item.rect(), item._cache_qimage)
        painter.end()
        return bytes(image.constBits())
    assert render(True) == render(False)
