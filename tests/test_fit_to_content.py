"""Vertical fitting preserves final printer dots, margins and cut boundaries."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from dataclasses import replace
import pytest
from PIL import Image, ImageChops
from PySide6 import QtWidgets
from receipt_designer.core.models import Template, Element, CutMarker
from receipt_designer.printing.jobs import ThermalProfile
from receipt_designer.ui.print_render import prepare_print_job


@pytest.fixture(scope='module')
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def ink_bbox(image):
    return ImageChops.invert(image.convert('L')).getbbox()


def block(template, y_mm=10, h_mm=5, **kwargs):
    ppm = template.px_per_mm
    return Element('rect', 10*ppm, y_mm*ppm, 2*ppm, h_mm*ppm,
                   stroke_px=0.01, **kwargs)


def test_fit_option_is_schema2_additive_and_roundtrips():
    assert hasattr(Template(), 'fit_to_content'), 'fit document option is missing'
    for enabled in [False, True]:
        t = Template(fit_to_content=enabled, version='user version')
        saved = t.to_dict()
        assert saved['schema_version'] == 2
        assert saved['fit_to_content'] is enabled
        assert Template.from_dict(saved).fit_to_content is enabled
    assert Template.from_dict({}).fit_to_content is False
    assert Template.from_dict({'schema_version': 1}).fit_to_content is False
    assert Template.from_dict({'schema_version': 2}).fit_to_content is False


@pytest.mark.parametrize('value', [0, 1, 'false', 'true', None, [], {}])
def test_fit_option_rejects_non_boolean(value):
    with pytest.raises(ValueError, match='fit_to_content'):
        Template.from_dict({'fit_to_content': value})


def test_fit_trims_both_ends_adds_only_declared_margins_and_preserves_scale(qapp):
    fixed = Template(height_mm=75, margins_mm=(4, 1.25, 4, 2.5))
    fixed.elements = [block(fixed)]
    full = prepare_print_job(fixed, ThermalProfile()).preview
    bbox = ink_bbox(full)
    assert bbox[1] > 0 and bbox[3] < full.height
    fit = replace(fixed, fit_to_content=True)
    job = prepare_print_job(fit, ThermalProfile())
    cropped_height = bbox[3]-bbox[1]
    assert job.preview.size == (576, cropped_height+10+20)
    expected = Image.new('1', job.preview.size, 255)
    expected.paste(full.crop((0, bbox[1], 576, bbox[3])), (0, 10))
    assert job.preview.tobytes() == expected.tobytes()
    assert ink_bbox(job.preview) == (bbox[0], 10, bbox[2], 10+cropped_height)
    assert job.parts[0].image.tobytes() == job.preview.tobytes()
    assert fit.elements[0].y == fixed.elements[0].y
    assert prepare_print_job(fixed, ThermalProfile()).preview.tobytes() == full.tobytes()


@pytest.mark.parametrize('y_mm', [0, 74])
def test_fit_retains_ink_touching_page_top_or_bottom(qapp, y_mm):
    fixed = Template(height_mm=75)
    fixed.elements = [block(fixed, y_mm, 1)]
    full = prepare_print_job(fixed, ThermalProfile()).preview
    bbox = ink_bbox(full)
    if y_mm == 0:
        assert bbox[1] == 0
    else:
        assert bbox[3] == full.height
    image = prepare_print_job(replace(fixed, fit_to_content=True), ThermalProfile()).preview
    assert image.height == bbox[3]-bbox[1]
    assert image.tobytes() == full.crop((0, bbox[1], 576, bbox[3])).tobytes()


@pytest.mark.parametrize('kind', ['empty', 'hidden', 'left-margin', 'outside-page', 'white', 'cuts-only'])
def test_fit_rejects_no_visible_printable_ink(qapp, kind):
    t = Template()
    if kind == 'hidden': t.elements = [block(t, visible=False)]
    elif kind == 'left-margin': t.elements = [replace(block(t), x=0, w=t.px_per_mm)]
    elif kind == 'outside-page': t.elements = [block(t, y_mm=100)]
    elif kind == 'white': t.elements = [block(t, fill_color='#ffffff', stroke_color='#ffffff')]
    elif kind == 'cuts-only': t.cut_markers = [CutMarker(25)]
    t.fit_to_content = True
    with pytest.raises(ValueError, match='documento não tem tinta visível na área imprimível'):
        prepare_print_job(t, ThermalProfile())


def test_fixed_blank_document_retains_full_paper(qapp):
    assert prepare_print_job(Template(), ThermalProfile()).preview.size == (576, 600)


def test_empty_fit_has_typed_error_for_draft_thumbnail_fallback(qapp):
    from receipt_designer.ui import print_render
    assert hasattr(print_render, 'EmptyPrintableContentError')
    assert issubclass(print_render.EmptyPrintableContentError, ValueError)
    with pytest.raises(print_render.EmptyPrintableContentError):
        prepare_print_job(Template(fit_to_content=True), ThermalProfile())


def test_fit_keeps_all_cuts_including_before_and_after_ink(qapp):
    fixed = Template(height_mm=75, margins_mm=(4, .5, 4, .75),
                     cut_markers=[CutMarker(5, 'partial'), CutMarker(12, 'full'), CutMarker(70, 'partial')])
    fixed.elements = [block(fixed, 10, 5)]
    full = prepare_print_job(fixed, ThermalProfile()).preview
    fit = replace(fixed, fit_to_content=True)
    job = prepare_print_job(fit, ThermalProfile())
    # First/last cuts bound retained rows [39,561); padding is 4 + 6 dots.
    assert job.preview.size == (576, 532)
    assert [part.image.height for part in job.parts] == [5, 56, 464, 7]
    assert [part.cut_after for part in job.parts] == ['partial', 'full', 'partial', 'full']
    expected = Image.new('1', (576, 532), 255)
    expected.paste(full.crop((0, 39, 576, 561)), (0, 4))
    assert job.preview.tobytes() == expected.tobytes()
    joined = Image.new('1', job.preview.size, 255)
    row = 0
    for part in job.parts:
        assert part.image.height >= 1
        joined.paste(part.image, (0, row)); row += part.image.height
    assert joined.tobytes() == job.preview.tobytes()
    assert fit.cut_markers == fixed.cut_markers


def test_fit_edge_cuts_retain_one_row_minimum(qapp):
    t = Template(height_mm=10, cut_markers=[CutMarker(.125), CutMarker(9.875)])
    t.elements = [block(t, 4, 1)]
    t.fit_to_content = True
    job = prepare_print_job(t, ThermalProfile())
    assert [part.image.height for part in job.parts] == [1, 78, 1]


@pytest.mark.parametrize('margins', [(4,-1,4,0), (4,0,4,float('nan')), (4,float('inf'),4,0), (4,0,4)])
def test_fit_rejects_invalid_vertical_margins(qapp, margins):
    t = Template(margins_mm=margins)
    t.elements = [block(t)]
    t.fit_to_content = True
    with pytest.raises(ValueError, match='(?i)margin'):
        prepare_print_job(t, ThermalProfile())
