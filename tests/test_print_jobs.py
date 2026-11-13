"""Document-to-wire regressions; all transport tests use loopback only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import socket
import threading
import struct
from datetime import datetime
import pytest
from PIL import Image
from PySide6 import QtWidgets
from receipt_designer.core import models


@pytest.fixture(scope='module')
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def test_schema_and_spacing_roundtrip():
    assert hasattr(models, 'CutMarker'), 'cut metadata is missing'
    t = models.Template(cut_markers=[models.CutMarker(20)], version='custom')
    t.elements = [models.Element('text', 0, 0, 10, 10, letter_spacing_px=-1.5)]
    loaded = models.Template.from_dict(t.to_dict())
    assert loaded.schema_version == 2
    assert loaded.version == 'custom'
    assert loaded.cut_markers[0].position_mm == 20
    assert loaded.elements[0].letter_spacing_px == -1.5
    assert models.Template.from_dict({}).cut_markers == []
    assert models.Element.from_dict({}).letter_spacing_px == 0


def test_editor_aliases_survive_save():
    e = models.Element('text', 0, 0, 100, 30)
    e.h_align = 'center'; e.v_align = 'middle'; e.wrap_mode = 'any'; e.font_point = 19
    saved = models.Element.from_dict(e.to_dict())
    assert saved.halign == 'center'
    assert saved.valign == 'middle'
    assert not saved.wrap
    assert saved.font_size == 19
    old = models.Element.from_dict({'h_align': 'right', 'v_align': 'bottom', 'wrap_mode': 'any', 'font_point': 18})
    assert (old.halign, old.valign, old.wrap, old.font_size) == ('right', 'bottom', False, 18)


@pytest.mark.parametrize('document', [
    {'schema_version': 3}, {'schema_version': '2'},
    {'cut_markers': [{'position_mm': -1}]},
    {'cut_markers': [{'position_mm': float('nan')}]},
    {'cut_markers': [{'position_mm': 75}]},
    {'cut_markers': [{'position_mm': 10}, {'position_mm': 10}]},
    {'cut_markers': [{'position_mm': 10, 'mode': 'bogus'}]},
])
def test_invalid_document_refused(document):
    with pytest.raises(ValueError):
        models.Template.from_dict(document)


def test_crop_printable_region_and_split_without_dropping_rows(qapp):
    from receipt_designer.printing.jobs import ThermalProfile
    from receipt_designer.ui.print_render import prepare_print_job
    t = models.Template(height_mm=20, cut_markers=[models.CutMarker(7.5)])
    ppm = t.px_per_mm
    # 4mm-side margin must disappear; 1mm solid block must remain 8 dots wide.
    t.elements = [models.Element('rect', 0, 0, 2*ppm, 20*ppm),
                  models.Element('rect', 10*ppm, 0, ppm, 20*ppm, stroke_px=0.01)]
    t.guides = [models.GuideLine(0, 40, t.width_px, 40)]
    t.grid = models.GuideGrid(visible=True)
    job = prepare_print_job(t, ThermalProfile())
    assert job.preview.size == (576, 160)
    assert job.preview.getpixel((0, 20)) == 255
    assert job.preview.getpixel((49, 20)) == 0
    assert job.preview.getpixel((57, 20)) == 255
    assert job.preview.getpixel((400, 40)) == 255
    assert [p.image.height for p in job.parts] == [60, 100]
    joined = Image.new('1', job.preview.size)
    row = 0
    for part in job.parts:
        joined.paste(part.image, (0, row)); row += part.image.height
    assert joined.tobytes() == job.preview.tobytes()
    assert [p.cut_after for p in job.parts] == ['full', 'full']
    assert t.elements[0].x == 0


def test_render_uses_variables_visibility_z_and_rotation(qapp):
    from receipt_designer.printing.jobs import ThermalProfile
    from receipt_designer.ui.print_render import prepare_print_job
    t = models.Template(height_mm=20)
    t.variable_manager.set_variable('message', 'ABC')
    t.elements = [models.Element('text', 40, 20, 100, 30, text='{{var:message}}'),
                  models.Element('rect', 200, 20, 50, 50, visible=False),
                  models.Element('rect', 300, 30, 30, 10, rotation=90)]
    first = prepare_print_job(t, ThermalProfile()).preview
    t.elements[0].text = 'ABC'
    assert first.tobytes() == prepare_print_job(t, ThermalProfile()).preview.tobytes()
    assert first.getpixel((180, 30)) == 255
    assert first.getpixel((266, 50)) == 0
    t.elements += [models.Element('rect', 40, 20, 100, 30, fill_color='#ffffff', stroke_color='#ffffff', z=10)]
    assert first.tobytes() != prepare_print_job(t, ThermalProfile()).preview.tobytes()


def decode_raster(data):
    assert data[:2] == b'\x1b@'
    cursor = 2; bands = []; events = []
    while cursor < len(data):
        if data[cursor:cursor+4] == b'\x1dv0\x00':
            width = int.from_bytes(data[cursor+4:cursor+6], 'little')
            rows = int.from_bytes(data[cursor+6:cursor+8], 'little')
            pixels = data[cursor+8:cursor+8+width*rows]
            assert len(pixels) == width*rows
            bands.append((width, rows, pixels)); events.append('image')
            cursor += 8 + width*rows
        else:
            assert data[cursor:cursor+3] == b'\x1bd\x04'
            assert data[cursor+3:cursor+5] == b'\x1dV'
            events.append('cut'); cursor += 6
    return bands, events


def test_raster_polarity_padding_bands_and_cut_order():
    from receipt_designer.printing.jobs import ThermalProfile, PreparedPrintJob, PrintPart
    from receipt_designer.printing.escpos_raster import encode_job
    image = Image.new('1', (9, 97), 255); image.putpixel((0, 0), 0); image.putpixel((8, 96), 0)
    job = PreparedPrintJob(image, [PrintPart(image, 'full'), PrintPart(image, 'partial')], ThermalProfile())
    bands, events = decode_raster(encode_job(job))
    assert [b[1] for b in bands] == [48, 48, 1, 48, 48, 1]
    assert all(b[0] == 2 for b in bands)
    assert bands[0][2][:2] == b'\x80\x00'
    assert bands[2][2] == b'\x00\x80'
    assert events == ['image']*3 + ['cut'] + ['image']*3 + ['cut']


def test_real_loopback_receives_exact_prepared_job(qapp):
    from receipt_designer.printing.jobs import ThermalProfile, PreparedPrintJob, PrintPart
    from receipt_designer.printing.escpos_raster import encode_job
    from receipt_designer.printing.worker import PrinterWorker
    received = bytearray()
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0)); server.listen(1); server.settimeout(5)
        def collect():
            conn, _ = server.accept()
            with conn:
                while chunk := conn.recv(4096): received.extend(chunk)
        thread = threading.Thread(target=collect); thread.start()
        image = Image.new('1', (576, 55), 0)
        job = PreparedPrintJob(image, [PrintPart(image, 'full')], ThermalProfile())
        worker = PrinterWorker('print', {'job': job, 'config': {'host': '127.0.0.1', 'port': server.getsockname()[1]}})
        sent = []; errors = []
        worker.signals.sent.connect(sent.append); worker.signals.error.connect(errors.append)
        worker.run(); thread.join(5)
    assert not thread.is_alive()
    assert not errors
    assert len(sent) == 1
    assert bytes(received) == encode_job(job)


def test_partial_write_is_uncertain_and_never_retried(monkeypatch, qapp):
    from receipt_designer.printing import backends
    from receipt_designer.printing.worker import PrinterWorker
    calls = []
    class BrokenSocket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, value): pass
        def sendall(self, data):
            calls.append(data[:5]); raise ConnectionResetError('after partial write')
    monkeypatch.setattr(backends.socket, 'create_connection', lambda *a, **k: BrokenSocket())
    worker = PrinterWorker('print', {'image': Image.new('1', (576, 20)), 'config': {}})
    uncertain = []; errors = []; sent = []
    worker.signals.uncertain.connect(uncertain.append); worker.signals.error.connect(errors.append); worker.signals.sent.connect(sent.append)
    worker.run()
    assert len(calls) == 1
    assert uncertain and errors and not sent
    assert 'uncertain' in errors[0].lower()


def test_no_image_fails_even_in_dry_run(qapp):
    from receipt_designer.printing.worker import PrinterWorker
    worker = PrinterWorker('print', {}, dry_run=True)
    errors = []; sent = []
    worker.signals.error.connect(errors.append); worker.signals.sent.connect(sent.append)
    worker.run()
    assert errors and not sent


def test_profile_defaults_and_explicit_threshold():
    from receipt_designer.printing.jobs import ThermalProfile, monochrome
    p = ThermalProfile.from_config({'threshold': 170, 'darkness': 250, 'host': 'printer'})
    assert (p.width_px, p.printable_width_mm, p.paper_width_mm, p.host, p.feed_lines) == (576, 72, 80, 'printer', 4)
    gray = Image.new('L', (3, 1)); gray.putdata([169, 170, 171])
    result = monochrome(gray, p)
    assert [result.getpixel((x, 0)) for x in range(3)] == [0, 0, 255]
    transparent = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    assert monochrome(transparent, p).getpixel((0, 0)) == 255


def test_render_freezes_system_time_across_elements(monkeypatch, qapp):
    from receipt_designer.ui import print_render
    from receipt_designer.printing.jobs import ThermalProfile
    calls = []
    class AdvancingClock:
        @staticmethod
        def now():
            calls.append(True)
            return datetime(2026, 11, 13, 1, 2, len(calls))
    monkeypatch.setattr(print_render, 'datetime', AdvancingClock, raising=False)
    t = models.Template(height_mm=20)
    t.elements = [models.Element('text', 40, 0, 100, 30, text='{{second}}'),
                  models.Element('text', 40, 40, 100, 30, text='{{second}}')]
    image = print_render.prepare_print_job(t, ThermalProfile()).preview
    assert len(calls) == 1
    for elem in t.elements: elem.text = '1'
    assert image.tobytes() == print_render.prepare_print_job(t, ThermalProfile()).preview.tobytes()


def test_cut_positions_colliding_at_dot_resolution_refused(qapp):
    from receipt_designer.ui.print_render import prepare_print_job
    from receipt_designer.printing.jobs import ThermalProfile
    t = models.Template(cut_markers=[models.CutMarker(10), models.CutMarker(10.01)])
    with pytest.raises(ValueError, match='collide'):
        prepare_print_job(t, ThermalProfile())


def test_legacy_qimage_pixels_are_transmitted(qapp):
    from receipt_designer.ui.print_render import pil_to_qimage, qimage_to_pil
    from receipt_designer.printing.worker import PrinterWorker
    image = Image.new('RGB', (576, 3), 'white'); image.putpixel((0, 0), (0, 0, 0))
    qimage = pil_to_qimage(image)
    assert qimage_to_pil(qimage).convert('RGB').tobytes() == image.tobytes()
    worker = PrinterWorker('print', {'image': qimage, 'config': {'cut_mode': 'none'}}, dry_run=True)
    worker.run()
    bands, events = decode_raster(b''.join(worker.dry_run_backend.sent_chunks))
    assert bands[0][2][0] == 0x80
    assert events == ['image']


def test_real_tcp_reset_is_uncertain():
    from receipt_designer.printing.backends import NetworkBackend, UncertainTransmissionError
    reset = threading.Event()
    accepted = []
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0)); server.listen(1); server.settimeout(5)
        def close_after_first_bytes():
            conn, _ = server.accept(); accepted.append(True)
            with conn:
                assert conn.recv(16)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('hh', 1, 0))
            reset.set()
        thread = threading.Thread(target=close_after_first_bytes); thread.start()
        def chunks():
            yield b'first bytes'
            assert reset.wait(5)
            for _ in range(100): yield b'x' * 4096
        try:
            with pytest.raises(UncertainTransmissionError):
                NetworkBackend('127.0.0.1', server.getsockname()[1]).send_stream(chunks())
        finally:
            thread.join(5)
    assert accepted == [True]


def test_serial_flush_failure_is_uncertain(monkeypatch):
    from receipt_designer.printing import backends
    class SerialDevice:
        def __init__(self, *a, **kw): pass
        def write(self, data): return len(data)
        def flush(self): raise OSError('device disconnected after write')
        def close(self): pass
    monkeypatch.setattr(backends.serial, 'Serial', SerialDevice)
    with pytest.raises(backends.UncertainTransmissionError):
        backends.SerialBackend('COM99').send(b'ink')


def test_usb_config_supports_legacy_hex_strings(monkeypatch):
    from receipt_designer.printing import backends
    captured = []
    monkeypatch.setattr(backends, 'USBBackend', lambda *a, **kw: captured.append((a, kw)))
    backends.make_backend({'interface': 'usb', 'usb_vid': '0x1234', 'usb_pid': '0x5678', 'usb_out': '0x01'})
    assert captured[0] == ((0x1234, 0x5678), {'out_endpoint': 1, 'interface': None})


def test_config_dry_run_reports_no_physical_printing(qapp):
    from receipt_designer.printing.worker import PrinterWorker
    worker = PrinterWorker('feed', {'config': {'interface': 'dry_run'}})
    sent = []
    worker.signals.sent.connect(sent.append)
    worker.run()
    assert 'no physical printing' in sent[0].lower()


def test_default_network_routing_and_explicit_source(monkeypatch):
    from receipt_designer.printing import backends
    called = []
    monkeypatch.setattr(backends.socket, 'create_connection', lambda *a, **kw: called.append((a, kw)))
    backends.NetworkBackend('printer')._connect()
    assert called == [((('printer', 9100),), {'timeout': 5.0})]
    backends.NetworkBackend('printer', source_ip='127.0.0.1')._connect()
    assert called[-1][1]['source_address'] == ('127.0.0.1', 0)


def test_windows_explicit_interface_affects_only_socket(monkeypatch):
    from receipt_designer.printing import backends
    calls = []
    class Socket:
        def settimeout(self, value): calls.append(('timeout', value))
        def setsockopt(self, *args): calls.append(('option', args))
        def bind(self, value): calls.append(('bind', value))
        def connect(self, value): calls.append(('connect', value))
    monkeypatch.setattr(backends.sys, 'platform', 'win32')
    monkeypatch.setattr(backends.socket, 'socket', lambda *a: Socket())
    backends.NetworkBackend('192.168.1.10', source_ip='192.168.1.20', interface_index=10)._connect()
    assert ('option', (socket.IPPROTO_IP, getattr(socket, 'IP_UNICAST_IF', 31), socket.htonl(10))) in calls
    assert calls[-2:] == [('bind', ('192.168.1.20', 0)), ('connect', ('192.168.1.10', 9100))]


def test_malformed_job_fails_before_any_transport(monkeypatch, qapp):
    from receipt_designer.printing import worker as worker_module
    from receipt_designer.printing.jobs import PreparedPrintJob, PrintPart
    image = Image.new('L', (576, 10))
    job = PreparedPrintJob(image, [PrintPart(image, 'full')])
    opened = []
    monkeypatch.setattr(worker_module, 'make_backend', lambda cfg: opened.append(cfg))
    worker = worker_module.PrinterWorker('print', {'job': job})
    errors = []; sent = []
    worker.signals.error.connect(errors.append); worker.signals.sent.connect(sent.append)
    worker.run()
    assert errors and not sent and not opened
