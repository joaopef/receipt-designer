"""Small native-document drawing vocabulary, in millimetres (not bitmaps)."""
from __future__ import annotations
from ..core.models import Element, Template, CutMarker

PPM = 203 / 25.4


class Ticket:
    def __init__(self, slug, name, *, height=180, fit=True):
        self.slug = slug
        self.template = Template(name=name, width_mm=80, height_mm=height,
                                 margins_mm=(4, 1, 4, 1), fit_to_content=fit)
        self.template.variable_manager.variables.clear()

    def var(self, name, sample):
        self.template.variable_manager.set_variable(name, sample)
        return '{{var:' + name + '}}'

    def text(self, text, y, *, x=8, w=64, h=None, size=12,
             family='Courier New', bold=False, align='left', spacing=0, role=None):
        self.template.elements.append(Element(
            'text', x*PPM, y*PPM, w*PPM, (h or size*.27)*PPM,
            text=text, font_family=family, font_size=size, bold=bold,
            halign=align, wrap=True, shrink_to_fit=False,
            letter_spacing_px=spacing, z=5,
            data={'collection': 'thermal-ideas-v1', 'slug': self.slug, 'role': role or 'text'}))
        return self

    def rect(self, x, y, w, h, *, fill='', stroke='#000000', role='shape'):
        self.template.elements.append(Element(
            'rect', x*PPM, y*PPM, w*PPM, h*PPM, fill_color=fill,
            stroke_color=stroke, stroke_px=2, z=0,
            data={'collection': 'thermal-ideas-v1', 'slug': self.slug, 'role': role}))
        return self

    def line(self, y, *, x=8, w=64, dash=False):
        starts = range(0, round(w*4), 12) if dash else [0]
        for start in starts:
            offset = start/4
            length = min(2, w-offset) if dash else w
            self.template.elements.append(Element(
                'line', (x+offset)*PPM, y*PPM, length*PPM, 0,
                stroke_px=2, z=2,
                data={'collection': 'thermal-ideas-v1', 'slug': self.slug, 'role': 'rule'}))
        return self

    def header(self, eyebrow, title, *, subtitle=None):
        self.text(eyebrow, 3, size=10, bold=True, spacing=.6)
        self.line(8)
        self.text(title, 11, size=25, family='Arial Black', h=9)
        if subtitle:
            self.text(subtitle, 21, size=11, family='Arial', h=6)
            self.line(29)
        else:
            self.line(23)
        return self

    def section(self, label, y):
        self.text(label, y, size=11, bold=True, spacing=.5)
        return self

    def check(self, label, y, *, x=8, w=64):
        self.rect(x, y+.35, 2.7, 2.7, role='checkbox')
        self.text(label, y, x=x+5, w=w-5, size=12, h=4.7)
        return self

    def writing(self, y, *, count=3, gap=6, x=8, w=64):
        for i in range(count):
            self.line(y+i*gap, x=x, w=w)
        return self

    def footer(self, label, y):
        self.line(y)
        self.text(label, y+2, size=9, family='Arial', h=4.5, align='center')
        return self

    def cut(self, y, mode='full'):
        self.template.cut_markers.append(CutMarker(y, mode))
        return self

    def build(self):
        self.template.validate_cuts()
        return self.template
