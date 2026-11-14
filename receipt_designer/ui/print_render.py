"""Render a model snapshot once, using the editor's drawing primitives."""
import copy
import math
from datetime import datetime
from PIL import Image, ImageChops
from PySide6 import QtCore, QtGui, QtWidgets
from ..core.models import Template
from ..printing.jobs import ThermalProfile, PreparedPrintJob, PrintPart, monochrome
from .items import create_item_from_element


class EmptyPrintableContentError(ValueError):
    """The final printable raster has no ink to fit."""


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


def _fit_content(preview, cut_rows, margins_mm, dots_per_mm):
    """Trim only outside ink/cuts, then add the document's vertical padding."""
    ink = ImageChops.invert(preview.convert('L')).getbbox()
    if ink is None:
        raise EmptyPrintableContentError('Não é possível ajustar: o documento não tem tinta visível na área imprimível.')
    try:
        _, top_mm, _, bottom_mm = margins_mm
        top_mm, bottom_mm = float(top_mm), float(bottom_mm)
    except (TypeError, ValueError) as exc:
        raise ValueError('Vertical margins must be finite nonnegative millimetres.') from exc
    if not all(math.isfinite(value) and value >= 0 for value in (top_mm, bottom_mm)):
        raise ValueError('Vertical margins must be finite nonnegative millimetres.')
    top, bottom = ink[1], ink[3]
    if cut_rows:
        # Preserve a source row on both sides of the outermost cuts, even if
        # these rows are white. All rows between cuts remain untouched.
        top = min(top, cut_rows[0][0] - 1)
        bottom = max(bottom, cut_rows[-1][0] + 1)
    padding_top = round(top_mm * dots_per_mm)
    padding_bottom = round(bottom_mm * dots_per_mm)
    cropped = preview.crop((0, top, preview.width, bottom))
    fitted = Image.new('1', (preview.width, cropped.height + padding_top + padding_bottom), 255)
    fitted.paste(cropped, (0, padding_top))
    shifted_cuts = [(row - top + padding_top, mode) for row, mode in cut_rows]
    return fitted, shifted_cuts


def prepare_print_job(template: Template, profile: ThermalProfile) -> PreparedPrintJob:
    if QtWidgets.QApplication.instance() is None:
        raise RuntimeError('A QApplication is required to render a document.')
    template.validate_cuts()
    template.validate_fit_to_content()
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
    if template.fit_to_content:
        preview, cut_rows = _fit_content(preview, cut_rows, template.margins_mm, dots_per_mm)
        height = preview.height
    parts = []
    last = 0
    for row, mode in cut_rows + [(height, profile.cut_mode)]:
        parts.append(PrintPart(preview.crop((0, last, profile.width_px, row)), mode))
        last = row
    return PreparedPrintJob(preview, parts, profile)
