"""Printer settings, with optional source binding and normal routing by default."""
from __future__ import annotations
import ipaddress
from PySide6 import QtWidgets


def show_printer_config_dialog(printer_cfg: dict, parent=None) -> dict | None:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle('Configurar impressora')
    form = QtWidgets.QFormLayout(dialog)
    iface = QtWidgets.QComboBox()
    for name, value in [('Rede (TCP)', 'network'), ('USB direto', 'usb'), ('Série (RS-232)', 'serial')]:
        iface.addItem(name, value)
    iface.setCurrentIndex(max(0, iface.findData(printer_cfg.get('interface', 'network'))))
    host = QtWidgets.QLineEdit(printer_cfg.get('host', '192.168.1.10'))
    port = QtWidgets.QSpinBox()
    port.setRange(1, 65535)
    port.setValue(int(printer_cfg.get('port', 9100)))
    threshold = QtWidgets.QSpinBox()
    threshold.setRange(0, 255)
    threshold.setValue(int(printer_cfg.get('threshold', 170)))
    threshold.setToolTip('Conversão de imagem para preto e branco. Valores maiores escurecem a imagem; não altera os DIP físicos Dark/Slow.')
    width = QtWidgets.QSpinBox()
    width.setRange(8, 2048)
    width.setSingleStep(8)
    width.setValue(int(printer_cfg.get('width_px', 576)) or 576)
    printable = QtWidgets.QDoubleSpinBox()
    printable.setRange(1, 200)
    printable.setValue(float(printer_cfg.get('printable_width_mm', 72)))
    dpi = QtWidgets.QSpinBox()
    dpi.setRange(100, 600)
    dpi.setValue(int(printer_cfg.get('dpi', 203)))
    conversion = QtWidgets.QComboBox()
    conversion.addItem('Limiar preto/branco', 'threshold')
    conversion.addItem('Pontilhado (dither)', 'dither')
    conversion.setCurrentIndex(max(0, conversion.findData(printer_cfg.get('conversion', 'threshold'))))
    cut = QtWidgets.QComboBox()
    for name, value in [('Total', 'full'), ('Parcial', 'partial'), ('Sem corte', 'none')]:
        cut.addItem(name, value)
    cut.setCurrentIndex(max(0, cut.findData(printer_cfg.get('cut_mode', 'full'))))
    feed = QtWidgets.QSpinBox()
    feed.setRange(0, 255)
    feed.setValue(int(printer_cfg.get('feed_lines', 4)))
    timeout = QtWidgets.QDoubleSpinBox()
    timeout.setRange(1, 120)
    timeout.setValue(float(printer_cfg.get('timeout', 30)))
    profile = QtWidgets.QLineEdit(printer_cfg.get('profile', 'AB-88H'))
    for label, widget in [('Ligação:', iface), ('Endereço da impressora:', host), ('Porta TCP:', port), ('Perfil:', profile), ('Largura em píxeis:', width), ('Área imprimível (mm):', printable), ('DPI nominal:', dpi), ('Conversão:', conversion), ('Limiar P/B (0–255):', threshold), ('Corte final:', cut), ('Avanço antes do corte (linhas):', feed), ('Tempo limite (s):', timeout)]:
        form.addRow(label, widget)
    note = QtWidgets.QLabel('AB-88H: papel de 80 mm, área central de 72 mm / 576 píxeis.\nDark/Slow são definições físicas dos DIP da impressora.')
    note.setWordWrap(True)
    form.addRow(note)
    advanced = QtWidgets.QGroupBox('Rede avançada — opcional')
    adv = QtWidgets.QFormLayout(advanced)
    source = QtWidgets.QLineEdit(printer_cfg.get('source_ip') or '')
    source.setObjectName('source_ip')
    source.setPlaceholderText('Vazio: encaminhamento normal do Windows')
    interface_index = QtWidgets.QSpinBox()
    interface_index.setRange(0, 2147483647)
    interface_index.setSpecialValueText('Automática')
    interface_index.setValue(int(printer_cfg.get('interface_index') or 0))
    adv.addRow('IP local de origem:', source)
    adv.addRow('Índice da interface Windows:', interface_index)
    explanation = QtWidgets.QLabel('Use de preferência a LAN do router. Estas opções aplicam-se apenas à ligação TCP; não alteram IPs ou rotas do Windows.')
    explanation.setWordWrap(True)
    adv.addRow(explanation)
    form.addRow(advanced)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    form.addRow(buttons)
    result = None

    def accept():
        nonlocal result
        local_ip = source.text().strip()
        try:
            if local_ip:
                ipaddress.IPv4Address(local_ip)
            if not host.text().strip():
                raise ValueError('Indique o endereço da impressora.')
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(dialog, 'Endereço inválido', str(exc))
            return
        result = dict(printer_cfg)
        result.update(interface=iface.currentData(), host=host.text().strip(), port=port.value(), profile=profile.text().strip() or 'AB-88H', width_px=width.value(), printable_width_mm=printable.value(), paper_width_mm=80.0, dpi=dpi.value(), conversion=conversion.currentData(), threshold=threshold.value(), cut_mode=cut.currentData(), feed_lines=feed.value(), timeout=timeout.value(), source_ip=local_ip, interface_index=interface_index.value() or None)
        dialog.accept()

    buttons.accepted.connect(accept)
    buttons.rejected.connect(dialog.reject)
    dialog.exec()
    return result
