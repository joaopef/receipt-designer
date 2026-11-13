"""ESC/POS GS v 0 raster bands. Black dots are one bits, MSB first."""
from .jobs import PreparedPrintJob


def cut_command(mode: str, feed_lines: int = 4) -> bytes:
    if mode == 'none' or mode is None:
        return b''
    if mode not in ('full', 'partial'):
        raise ValueError('Unknown cut mode.')
    return bytes((0x1b, 0x64, feed_lines, 0x1d, 0x56, 0 if mode == 'full' else 1))


def raster_bands(image, max_rows=48):
    if not 1 <= max_rows <= 48:
        raise ValueError('Raster bands must contain 1 through 48 rows.')
    if image.mode != '1' or image.width <= 0 or image.height <= 0:
        raise ValueError('Raster image must contain prepared monochrome pixels.')
    width_bytes = (image.width + 7) // 8
    if width_bytes > 65535:
        raise ValueError('Raster width exceeds ESC/POS command range.')
    for top in range(0, image.height, max_rows):
        rows = min(max_rows, image.height - top)
        pixels = image.crop((0, top, image.width, top + rows)).tobytes()
        packed = bytearray(value ^ 255 for value in pixels)
        if image.width % 8:
            mask = 255 << (8 - image.width % 8) & 255
            for end in range(width_bytes - 1, len(packed), width_bytes):
                packed[end] &= mask
        yield b'\x1dv0\x00' + width_bytes.to_bytes(2, 'little') + rows.to_bytes(2, 'little') + packed


def iter_job_bytes(job: PreparedPrintJob):
    if not job.parts:
        raise ValueError('Print job has no image parts.')
    yield b'\x1b@'
    for part in job.parts:
        yield from raster_bands(part.image)
        command = cut_command(part.cut_after, job.profile.feed_lines)
        if command:
            yield command


def encode_job(job: PreparedPrintJob) -> bytes:
    return b''.join(iter_job_bytes(job))
