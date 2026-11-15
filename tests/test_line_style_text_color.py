"""Line styles and text colour must survive save/reopen and reach the printed raster."""
import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from receipt_designer.core.models import Element, Template
from receipt_designer.printing.jobs import ThermalProfile
from receipt_designer.ui.items import GItem, create_item_from_element
from receipt_designer.ui.print_render import prepare_print_job
from receipt_designer.ui.properties import PropertiesPanel

INSET = 4 * 203 / 25.4


@pytest.fixture(scope='module')
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_new_fields_roundtrip_and_old_documents_keep_defaults():
    template = Template()
    template.elements = [
        Element(kind='line', x=0, y=0, w=100, h=0, line_style='perforation'),
        Element(kind='text', x=0, y=0, w=100, h=20, text='A', text_color='#ffffff'),
    ]
    loaded = Template.from_dict(template.to_dict())
    assert loaded.elements[0].line_style == 'perforation'
    assert loaded.elements[1].text_color == '#ffffff'
    old = Template.from_dict({'elements': [{'kind': 'line', 'x': 0, 'y': 0, 'w': 9, 'h': 0},
                                           {'kind': 'text', 'x': 0, 'y': 0, 'w': 9, 'h': 9}]})
    assert old.elements[0].line_style == 'solid'
    assert old.elements[1].text_color == ''
    assert '_unknown' not in old.elements[0].data


@pytest.mark.parametrize('kind', ['line', 'arrow', 'rect', 'ellipse', 'star', 'diamond'])
@pytest.mark.parametrize('style', ['dashed', 'dotted', 'dashdot', 'perforation'])
def test_shapes_restore_and_serialize_line_style(qapp, kind, style):
    item = create_item_from_element(Element(kind=kind, x=5, y=5, w=80, h=40,
                                            stroke_px=2, fill_color='', line_style=style))
    assert item.pen().style() != QtCore.Qt.SolidLine
    assert item.to_element().line_style == style


def test_solid_shape_serializes_as_solid(qapp):
    item = create_item_from_element(Element(kind='rect', x=0, y=0, w=50, h=20, fill_color=''))
    assert item.to_element().line_style == 'solid'


def test_line_style_control_is_saved_with_the_document(qapp):
    item = create_item_from_element(Element(kind='line', x=0, y=0, w=200, h=0, stroke_px=2))
    panel = PropertiesPanel()
    panel.set_undo_stack(QtGui.QUndoStack(panel))
    panel.set_target_from_selection([item])
    panel.combo_line_style.setCurrentText('Dashed')
    assert item.to_element().line_style == 'dashed'
    panel.set_target_from_selection([])
    panel.set_target_from_selection([item])
    assert panel.combo_line_style.currentText() == 'Dashed'
    panel.close()


def _row_runs(image, row):
    """Count black runs in one raster row."""
    runs, previous = 0, False
    for x in range(image.width):
        black = image.getpixel((x, row)) == 0
        if black and not previous:
            runs += 1
        previous = black
    return runs


def test_dashed_line_prints_with_gaps_and_solid_line_does_not(qapp):
    template = Template(height_mm=20)
    template.elements = [
        Element(kind='line', x=INSET + 40, y=40, w=400, h=0, stroke_px=3, line_style='dashed'),
        Element(kind='line', x=INSET + 40, y=100, w=400, h=0, stroke_px=3),
    ]
    preview = prepare_print_job(template, ThermalProfile()).preview
    assert _row_runs(preview, 40) >= 15
    assert _row_runs(preview, 100) == 1


def test_white_text_prints_inside_a_black_box(qapp):
    def white_pixels(text_color):
        template = Template(height_mm=20)
        template.elements = [
            Element(kind='rect', x=INSET + 20, y=20, w=400, h=90, fill_color='#000000', z=0),
            Element(kind='text', x=INSET + 40, y=30, w=360, h=70, text='MMMM', font_family='Arial',
                    font_size=40, bold=True, text_color=text_color, z=5),
        ]
        preview = prepare_print_job(template, ThermalProfile()).preview
        box = preview.crop((30, 30, 400, 100))
        return box.convert('L').histogram()[255]
    assert white_pixels('') < 50
    assert white_pixels('#ffffff') > 1500


def test_text_color_control_uses_undo_and_refreshes_cache(qapp):
    element = Element(kind='text', x=0, y=0, w=300, h=80, text='MMMM', font_size=22)
    item = GItem(element)
    item._ensure_cache(for_screen=False)
    black_cache = item._cache_qimage.copy()
    panel = PropertiesPanel()
    undo = QtGui.QUndoStack(panel)
    panel.set_undo_stack(undo)
    panel.set_target_from_selection([item])
    control = panel.findChild(QtWidgets.QComboBox, 'textColor')
    assert control is not None
    control.setCurrentIndex(control.findData('#ffffff'))
    assert element.text_color == '#ffffff'
    item._ensure_cache(for_screen=False)
    assert item._cache_qimage != black_cache
    undo.undo()
    assert element.text_color == ''
    panel.set_target_from_selection([item])
    assert control.currentData() == ''
    panel.close()
