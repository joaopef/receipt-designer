from __future__ import annotations

import socket
import sys
from typing import Optional

from .exceptions import PrinterConnectionError, PrinterConfigError, PrintJobError, map_exception


class UncertainTransmissionError(PrintJobError):
    """Some bytes may have reached the printer; an automatic retry is unsafe."""

try:
    import serial  # pyserial
except Exception:
    serial = None

try:
    import usb.core  # pyusb
    import usb.util
except Exception:
    usb = None  # type: ignore


class BaseBackend:
    def send(self, data: bytes) -> None:
        raise NotImplementedError

    def send_stream(self, chunks) -> None:
        self.send(b''.join(chunks))


class NetworkBackend(BaseBackend):
    def __init__(self, host: str, port: int = 9100, timeout: float = 5.0,
                 source_ip: Optional[str] = None, interface_index: Optional[int] = None):
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        self.source_ip = source_ip or None
        self.interface_index = int(interface_index) if interface_index is not None else None
        if self.interface_index is not None and (sys.platform != 'win32' or self.interface_index <= 0):
            raise PrinterConfigError('An explicit interface index requires Windows and a positive index.')

    def _connect(self):
        if self.interface_index is None:
            kwargs = {'timeout': self.timeout}
            if self.source_ip:
                kwargs['source_address'] = (self.source_ip, 0)
            return socket.create_connection((self.host, self.port), **kwargs)
        # This changes this socket, never OS routes.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.setsockopt(socket.IPPROTO_IP, getattr(socket, 'IP_UNICAST_IF', 31), socket.htonl(self.interface_index))
            if self.source_ip:
                sock.bind((self.source_ip, 0))
            sock.connect((self.host, self.port))
            return sock
        except Exception:
            sock.close()
            raise

    def send(self, data: bytes) -> None:
        self.send_stream([data])

    def send_stream(self, chunks) -> None:
        attempted = False
        try:
            with self._connect() as s:
                s.settimeout(self.timeout)
                for chunk in chunks:
                    if chunk:
                        attempted = True
                        s.sendall(chunk)
        except Exception as exc:
            if attempted:
                raise UncertainTransmissionError(
                    'Transmission uncertain: some data may have reached the printer. '
                    'Check the paper before sending again; no automatic retry was made.'
                ) from exc
            raise map_exception(exc) from exc


class SerialBackend(BaseBackend):
    def __init__(self, port: str, baudrate: int = 19200, timeout: float = 2.0):
        if serial is None:
            raise PrinterConfigError(
                "pyserial not installed. `pip install pyserial` to use Serial backend."
            )
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)

    def send(self, data: bytes) -> None:
        attempted = False
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout, write_timeout=self.timeout)
            try:
                attempted = True
                written = ser.write(data)
                if written != len(data):
                    raise OSError('Incomplete serial write.')
                ser.flush()
            finally:
                ser.close()
        except Exception as exc:
            if attempted:
                raise UncertainTransmissionError('Transmission uncertain after serial write; check the paper before sending again.') from exc
            raise map_exception(exc) from exc


class USBBackend(BaseBackend):
    # Generic ESC/POS USB backend via PyUSB. Provide VID/PID and an OUT endpoint.
    def __init__(
        self,
        vendor_id: int,
        product_id: int,
        out_endpoint: Optional[int] = None,
        interface: Optional[int] = None,
    ):
        if usb is None:
            raise PrinterConfigError(
                "pyusb not installed. `pip install pyusb` and install a USB backend (libusb) to use USB."
            )
        self.vendor_id = int(vendor_id)
        self.product_id = int(product_id)
        self.out_ep = out_endpoint
        self.interface = interface
        self._dev = None
        self._cfg = None
        self._ep_out = None
        self._open()

    def _open(self):
        self._dev = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
        if self._dev is None:
            raise RuntimeError(f"USB device {hex(self.vendor_id)}:{hex(self.product_id)} not found.")

        self._dev.set_configuration()
        self._cfg = self._dev.get_active_configuration()
        if self.interface is not None:
            intf = self._cfg[(self.interface, 0)]
        else:
            intf = self._cfg[(0, 0)]  # default to first interface

        # Detach kernel driver if needed (Linux)
        try:
            if self._dev.is_kernel_driver_active(intf.bInterfaceNumber):  # type: ignore[attr-defined]
                self._dev.detach_kernel_driver(intf.bInterfaceNumber)     # type: ignore[attr-defined]
        except Exception:
            pass

        # Locate OUT endpoint
        if self.out_ep is not None:
            self._ep_out = usb.util.find_descriptor(intf, bEndpointAddress=self.out_ep)
        else:
            self._ep_out = next(
                (ep for ep in intf if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT),
                None
            )

        if self._ep_out is None:
            raise RuntimeError("Could not locate a USB OUT endpoint for printer.")

    def send(self, data: bytes) -> None:
        assert self._ep_out is not None
        CHUNK = 16384
        for i in range(0, len(data), CHUNK):
            chunk = data[i:i + CHUNK]
            try:
                if self._ep_out.write(chunk) != len(chunk):
                    raise OSError('Incomplete USB write.')
            except Exception as exc:
                raise UncertainTransmissionError('Transmission uncertain after USB write; check the paper before sending again.') from exc


class DryRunBackend(BaseBackend):
    """Backend that captures bytes without touching any hardware.

    Useful for testing the print pipeline end-to-end in CI.
    """

    def __init__(self) -> None:
        self.sent_chunks: list[bytes] = []

    def send(self, data: bytes) -> None:
        self.sent_chunks.append(data)

    @property
    def total_bytes(self) -> int:
        return sum(len(c) for c in self.sent_chunks)


def make_backend(cfg: dict) -> BaseBackend:
    """Factory to build a backend from your printer config dict."""
    iface = (cfg.get("interface") or "network").lower()
    if iface == "dry_run":
        return DryRunBackend()
    if iface == "network":
        return NetworkBackend(cfg.get("host", "192.168.1.10"), int(cfg.get("port", 9100)),
                              float(cfg.get('timeout', 5)), cfg.get('source_ip'), cfg.get('interface_index'))
    if iface == "serial":
        return SerialBackend(cfg.get("serial_port", "COM1"), int(cfg.get("baudrate", 19200)), float(cfg.get('timeout', 2)))
    if iface == "usb":
        def number(value):
            return int(value, 0) if isinstance(value, str) else int(value)
        vid = number(cfg.get("usb_vid", 0))
        pid = number(cfg.get("usb_pid", 0))
        ep = cfg.get("usb_endpoint", cfg.get('usb_out'))
        ep = number(ep) if ep is not None else None
        iface_no = cfg.get("usb_interface")
        iface_no = int(iface_no) if iface_no is not None else None
        if not (vid and pid):
            raise PrinterConfigError("USB backend requires usb_vid and usb_pid in config.")
        return USBBackend(vid, pid, out_endpoint=ep, interface=iface_no)
    raise PrinterConfigError(f"Unknown interface: {iface}")
