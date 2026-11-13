"""Cut metadata editor; guide paint is restricted to interactive views."""
from __future__ import annotations
import copy
from PySide6 import QtCore, QtGui, QtWidgets
from ...core.models import CutMarker


class CutGuideItem(QtWidgets.QGraphicsLineItem):
    def paint(self, painter, option, widget=None):
        if widget is not None:
            super().paint(painter, option, widget)


class SetCutMarkersCommand(QtGui.QUndoCommand):
    def __init__(self, window, markers):
        super().__init__('Alterar cortes')
        self.window = window
        self.before = copy.deepcopy(window.template.cut_markers)
        self.after = copy.deepcopy(markers)

    def _apply(self, markers):
        self.window.template.cut_markers = copy.deepcopy(markers)
        self.window._update_cut_guides()
        self.window._mark_unsaved()

    def redo(self):
        self._apply(self.after)

    def undo(self):
        self._apply(self.before)


class CutMarkersDialog(QtWidgets.QDialog):
    def __init__(self, markers, height_mm, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Cortes intermédios')
        self.height_mm = height_mm
        self.resize(450, 380)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel('Posição desde o topo do papel, em mm.\nOs cortes são guias: não imprimem linhas nem retiram conteúdo.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Posição (mm)', 'Tipo de corte'])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        row = QtWidgets.QHBoxLayout()
        add = QtWidgets.QPushButton('Adicionar corte')
        add.clicked.connect(lambda: self.add_row(min(20.0, height_mm / 2), 'full'))
        remove = QtWidgets.QPushButton('Remover selecionado')
        remove.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()) if self.table.currentRow() >= 0 else None)
        row.addWidget(add)
        row.addWidget(remove)
        layout.addLayout(row)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for marker in markers:
            self.add_row(marker.position_mm, marker.mode)

    def add_row(self, position, mode):
        row = self.table.rowCount()
        self.table.insertRow(row)
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(2)
        spin.setRange(0.01, max(0.01, self.height_mm - 0.01))
        spin.setValue(position)
        self.table.setCellWidget(row, 0, spin)
        combo = QtWidgets.QComboBox()
        combo.addItem('Total', 'full')
        combo.addItem('Parcial', 'partial')
        combo.setCurrentIndex(1 if mode == 'partial' else 0)
        self.table.setCellWidget(row, 1, combo)

    def markers(self):
        return sorted([CutMarker(self.table.cellWidget(row, 0).value(), self.table.cellWidget(row, 1).currentData()) for row in range(self.table.rowCount())], key=lambda marker: marker.position_mm)

    def _accept_valid(self):
        markers = self.markers()
        positions = [marker.position_mm for marker in markers]
        if len(positions) != len(set(positions)):
            QtWidgets.QMessageBox.warning(self, 'Posições repetidas', 'Cada corte deve ter uma posição diferente.')
            return
        self.accept()
