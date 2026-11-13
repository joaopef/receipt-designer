"""Prepared pixels and printer geometry, independent of Qt and transport."""
from dataclasses import dataclass, field, fields
import math
from PIL import Image


@dataclass(frozen=True)
class ThermalProfile:
    width_px: int = 576
    printable_width_mm: float = 72.0
    paper_width_mm: float = 80.0
    threshold: int = 170
    conversion: str = 'threshold'
    cut_mode: str = 'full'
    feed_lines: int = 4
    host: str = '192.168.1.10'
    port: int = 9100
    config: dict = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if type(self.width_px) is not int or self.width_px <= 0:
            raise ValueError('Printable dot width must be positive.')
        if not all(math.isfinite(v) and v > 0 for v in (self.paper_width_mm, self.printable_width_mm)):
            raise ValueError('Paper dimensions must be finite positive numbers.')
        if self.printable_width_mm > self.paper_width_mm:
            raise ValueError('Printable width cannot exceed paper width.')
        if type(self.threshold) is not int or not 0 <= self.threshold <= 255:
            raise ValueError('Bitmap threshold must be between 0 and 255.')
        if self.conversion not in ('threshold', 'dither'):
            raise ValueError('Unknown bitmap conversion mode.')
        if self.cut_mode not in ('full', 'partial', 'none'):
            raise ValueError('Unknown cut mode.')
        if type(self.feed_lines) is not int or not 0 <= self.feed_lines <= 255:
            raise ValueError('Feed lines must be between 0 and 255.')

    @classmethod
    def from_config(cls, config):
        cfg = dict(config or {})
        values = {f.name: cfg[f.name] for f in fields(cls) if f.name in cfg and f.name != 'config'}
        if 'threshold' not in values and 'darkness' in cfg:
            values['threshold'] = int(cfg['darkness'])
        # Older configs used zero to mean the default/current media width.
        if not values.get('width_px', 576):
            values.pop('width_px', None)
        return cls(**values, config=cfg)


@dataclass(frozen=True)
class PrintPart:
    image: Image.Image
    cut_after: str = 'none'


@dataclass(frozen=True)
class PreparedPrintJob:
    preview: Image.Image
    parts: list[PrintPart]
    profile: ThermalProfile = field(default_factory=ThermalProfile)


def monochrome(image: Image.Image, profile: ThermalProfile) -> Image.Image:
    rgba = image.convert('RGBA')
    white = Image.new('RGBA', rgba.size, 'white')
    white.alpha_composite(rgba)
    gray = white.convert('L')
    if profile.conversion == 'dither':
        return gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    return gray.point(lambda pixel: 255 if pixel > profile.threshold else 0).convert('1')
