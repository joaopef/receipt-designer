"""Background transmission of prepared pixels, without implicit retries."""
from PySide6 import QtCore, QtGui
from PIL import Image
from .backends import make_backend, DryRunBackend, UncertainTransmissionError
from .exceptions import friendly_message
from .jobs import ThermalProfile, PreparedPrintJob, PrintPart, monochrome
from .escpos_raster import iter_job_bytes, cut_command


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()  # lifecycle only; emitted after success and error
    error = QtCore.Signal(str)
    progress = QtCore.Signal(int)
    sent = QtCore.Signal(str)  # transport accepted bytes; physical output unverified
    uncertain = QtCore.Signal(str)


class PrinterWorker(QtCore.QThread):
    """Accept payload['job'] or legacy payload['image'] plus config.

    Prepared jobs are transmitted unchanged. Legacy QImage/PIL payloads are
    resized and converted once here, preserving the existing public entrypoint.
    """
    def __init__(self, action: str, payload=None, parent=None, *, dry_run=False):
        super().__init__(parent)
        self.action = (action or '').lower()
        self.payload = payload or {}
        self.signals = WorkerSignals()
        self.dry_run = dry_run
        self.dry_run_backend = None

    @staticmethod
    def _qimage_to_pil(image):
        if image.isNull():
            raise ValueError('Cannot print a null image.')
        rgba = image.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        return Image.frombytes('RGBA', (rgba.width(), rgba.height()), bytes(rgba.constBits()),
                               'raw', 'RGBA', rgba.bytesPerLine()).copy()

    def _legacy_job(self, cfg):
        image = self.payload.get('image')
        if isinstance(image, QtGui.QImage):
            image = self._qimage_to_pil(image)
        if not isinstance(image, Image.Image):
            raise ValueError('No image supplied for printing.')
        profile = ThermalProfile.from_config(cfg)
        width = profile.width_px
        if cfg.get('width_px') == 0:
            width = image.width
        if image.width != width:
            image = image.resize((width, max(1, round(image.height * width / image.width))), Image.Resampling.LANCZOS)
        image = monochrome(image, profile)
        return PreparedPrintJob(image, [PrintPart(image, profile.cut_mode)], profile)

    def run(self):
        try:
            cfg = dict(self.payload.get('config') or {})
            profile = ThermalProfile.from_config(cfg)
            if self.action == 'print':
                job = self.payload.get('job')
                if job is None:
                    job = self._legacy_job(cfg)
                if not isinstance(job, PreparedPrintJob):
                    raise ValueError('Invalid prepared print job.')
                # Validate all raster bands before opening any connection.
                chunks = list(iter_job_bytes(job))
            elif self.action == 'feed':
                chunks = [b'\x1b@', bytes((0x1b, 0x64, profile.feed_lines))]
            elif self.action == 'cut':
                chunks = [b'\x1b@', cut_command(profile.cut_mode, profile.feed_lines)]
            else:
                raise ValueError(f'Unknown print action: {self.action}')
            self.signals.progress.emit(0)
            backend = DryRunBackend() if self.dry_run else make_backend(cfg)
            if isinstance(backend, DryRunBackend):
                self.dry_run_backend = backend
            backend.send_stream(chunks)
            self.signals.progress.emit(100)
            self.signals.sent.emit('Data sent to printer. Physical output has not been verified.'
                                   if not isinstance(backend, DryRunBackend) else 'Dry run captured printer data; no physical printing occurred.')
        except UncertainTransmissionError as exc:
            message = friendly_message(exc)
            self.signals.uncertain.emit(message)
            self.signals.error.emit(message)
        except Exception as exc:
            self.signals.error.emit(friendly_message(exc))
        finally:
            self.signals.finished.emit()
