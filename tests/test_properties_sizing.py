"""Properties keep usable controls and scroll when the dock is too short."""
import pytest
from PySide6 import QtGui, QtWidgets

from receipt_designer.core.models import Element
from receipt_designer.ui.items import GItem
from receipt_designer.ui.properties import PropertiesPanel


@pytest.mark.parametrize('height', [480, 900])
def test_properties_scroll_instead_of_squashing_numeric_fields(height):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyle('Fusion')
    panel = PropertiesPanel()
    font = QtGui.QFont(panel.font())
    font.setPointSize(11)
    panel.setFont(font)
    item = GItem(Element(kind='text', x=10, y=10, w=200, h=80, text='Texto'))
    panel.set_target_from_selection([item])
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(panel)
    area.resize(340, height)
    area.show()
    try:
        app.processEvents()
        fields = panel.findChildren(QtWidgets.QAbstractSpinBox)
        fields += panel.findChildren(QtWidgets.QComboBox)
        fields = [field for field in fields if not field.isHidden() and field.isVisibleTo(panel)]
        assert fields
        for field in fields:
            assert field.height() >= field.minimumSizeHint().height(), (
                field, field.height(), field.minimumSizeHint().height())
            assert field.height() >= field.fontMetrics().height() + 4
        assert area.verticalScrollBar().maximum() > 0
        area.ensureWidgetVisible(panel.sp_h)
        app.processEvents()
        assert area.verticalScrollBar().value() > 0
    finally:
        area.close()
