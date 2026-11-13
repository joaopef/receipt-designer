"""Render a model snapshot once, using the editor's drawing primitives."""
import copy
import math
from datetime import datetime
from PIL import Image
from PySide6 import QtCore, QtGui, QtWidgets
from ..core.models import Template
from ..printing.jobs import ThermalProfile, PreparedPrintJob, PrintPart, monochrome
from .items import create_item_from_element


def pil_to_qimage(image: Image.Image) -> QtGui.QImage:
    rgba = image.convert('RGBA')
    return QtGui.QImage(rgba.tobytes(), rgba.width, rgba.height, rgba.width * 4,
                       QtGui.QImage.Format.Format_RGBA8888).copy()


def qimage_to_pil(image: QtGui.QImage) -> Image.Image:
    if image.isNull():
        raise ValueError('Cannot print a null image.')
    rgba = image.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    return Image.frombytes('RGBA', (rgba.width(), rgba.height()), bytes(rgba.constBits()),
                           'raw', 'RGBA', rgba.bytesPerLine()).copy()


def prepare_print_job(template: Template, profile: ThermalProfile) -> PreparedPrintJob:
    if QtWidgets.QApplication.instance() is None:
        raise RuntimeError('A QApplication is required to render a document.')
    template.validate_cuts()
    if not all(math.isfinite(v) and v > 0 for v in (template.width_mm, template.height_mm, template.dpi)):
        raise ValueError('Document dimensions and resolution must be positive.')
    dots_per_mm = profile.width_px / profile.printable_width_mm
    height = max(1, round(template.height_mm * dots_per_mm))
    cut_rows = [(round(m.position_mm * dots_per_mm), m.mode)
                for m in sorted(template.cut_markers, key=lambda m: m.position_mm)]
    last = 0
    for row, _ in cut_rows:
        if row <= last or row >= height:
            raise ValueError('Cuts collide at printer resolution or fall outside the printable rows.')
        last = row
    scene = QtWidgets.QGraphicsScene()
    render_now = datetime.now()
    scene.setSceneRect(0, 0, template.width_px, template.height_px)
    for original in template.elements:
        elem = copy.deepcopy(original)
        elem.text = template.variable_manager.resolve_text(elem.text)
        item = create_item_from_element(elem)
        item._render_now = render_now
        item.setZValue(elem.z)
        item.setVisible(elem.visible)
        item.setRotation(elem.rotation)
        item.setSelected(False)
        scene.addItem(item)
    # Source rect removes the paper's unprintable edges, preserving physical scale.
    inset_mm = (profile.paper_width_mm - profile.printable_width_mm) / 2
    source = QtCore.QRectF(inset_mm * template.px_per_mm, 0,
                          profile.printable_width_mm * template.px_per_mm, template.height_px)
    image = QtGui.QImage(profile.width_px, height, QtGui.QImage.Format.Format_RGBA8888)
    image.fill(QtCore.Qt.GlobalColor.white)
    painter = QtGui.QPainter(image)
    try:
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        scene.render(painter, QtCore.QRectF(image.rect()), source, QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)
    finally:
        painter.end()
    preview = monochrome(qimage_to_pil(image), profile)
    parts = []
    last = 0
    for row, mode in cut_rows + [(height, profile.cut_mode)]:
        parts.append(PrintPart(preview.crop((0, last, profile.width_px, row)), mode))
        last = row
    return PreparedPrintJob(preview, parts, profile)
