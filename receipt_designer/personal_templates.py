"""Editable personal tickets rebuilt from the approved 576-dot references."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

from .core.models import CutMarker, Element, Template
from .library import LibraryRepository


# The reference artwork uses 8 dots/mm. The model uses nominal 203 DPI.
_SCALE = 203 / 203.2
_INSET = 4 * 203 / 25.4
_MARKER = ".personal-layouts-v1.json"


def _pattern_path() -> str:
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent
    return str(base / "assets" / "Templates" / "personal" / "chess-dots.png")


def _text(template, text, x, top, width, size=20, *, align="left",
          family="Courier New", spacing=0, bold=True, height=None, data=None,
          rotation=0, z=5):
    height = height or size * 1.55
    y = top - size * .22
    if rotation == 180:
        x += width
        y += height
    template.elements.append(Element(
        kind="text", x=_INSET + x * _SCALE, y=y * _SCALE,
        w=width * _SCALE, h=height * _SCALE, text=text,
        font_family=family, font_size=round(size * .75), bold=bold,
        halign=align, valign="top", wrap=False, shrink_to_fit=True,
        letter_spacing_px=spacing * _SCALE, data=data or {}, rotation=rotation, z=z))


def _rect(template, x, y, width, height, *, fill="", stroke="#000000", data=None, z=0):
    template.elements.append(Element(
        kind="rect", x=_INSET + x * _SCALE, y=y * _SCALE,
        w=width * _SCALE, h=height * _SCALE,
        fill_color=fill, stroke_color=stroke, stroke_px=2 * _SCALE,
        data=data or {}, z=z))


def _line(template, y, *, x=42, width=492, dash=0, gap=4, stroke=2):
    segments = range(0, int(width), dash + gap) if dash else [0]
    for start in segments:
        length = min(dash, width - start) if dash else width
        template.elements.append(Element(
            kind="line", x=_INSET + (x + start) * _SCALE, y=y * _SCALE,
            w=length * _SCALE, h=0, stroke_px=stroke * _SCALE,
            stroke_color="#000000", fill_color="", z=4))


def make_daily_template() -> Template:
    template = Template(name="Diário de bordo", width_mm=80, height_mm=1835 / 8)
    for name, value in {"task_1": "Enviar aquele email", "task_2": "Levantar a encomenda",
                        "task_3": "Dar uma volta a pé", "date": "SEXTA-FEIRA · 13 NOV 2026",
                        "temperature": "16° / 11°", "weather": "Chuva à tarde",
                        "rain": "Prob. chuva: 70% · Leva o guarda-chuva."}.items():
        template.variable_manager.set_variable(name, value)
    _text(template, "EDIÇÃO DE BOLSO", 42, 52, 350, 18, spacing=1.8,
          data={"personal_template": "daily-v1"})
    _text(template, "N.º 001", 400, 52, 134, 18, spacing=1.8, align="right")
    _text(template, "DIÁRIO DE BORDO", 42, 110, 492, 20, spacing=5.2, align="center")
    _text(template, "BOM DIA,", 42, 150, 492, 55, family="Arial Black", spacing=-2.5, align="center")
    _text(template, "MUNDO.", 42, 203, 492, 55, family="Arial Black", spacing=-2.5, align="center")
    _text(template, "{{var:date}}", 42, 267, 492, 20, align="center")
    _line(template, 336, dash=5, gap=4)
    _text(template, "LÁ FORA · EXEMPLO", 42, 367, 492, 20, spacing=2.3)
    _text(template, "{{var:temperature}}", 42, 407, 270, 43, family="Arial", spacing=-1)
    _text(template, "{{var:weather}}", 300, 424, 234, 22, align="right")
    _text(template, "{{var:rain}}", 42, 466, 492, 20)
    _line(template, 514, dash=5, gap=4)
    _text(template, "HOJE, SE DER", 42, 545, 492, 20, spacing=2.3)
    for index, y in enumerate((590, 638, 686), 1):
        _rect(template, 43, y - 7, 18, 18)
        _text(template, "{{var:task_" + str(index) + "}}", 77, y, 457, 24)
    _line(template, 767, dash=5, gap=4)
    _line(template, 793, dash=5, gap=4)
    _text(template, "UM MINUTO DE XADREZ", 42, 824, 492, 20, spacing=2.3)
    _text(template, "Brancas jogam", 42, 866, 300, 20)
    _text(template, "Mate em 1", 350, 866, 184, 20, align="right")
    board_x, board_y, cell = 106, 905, 48.6
    pieces = {"h8": "♚", "f6": "♔", "g6": "♕"}
    for row, rank in enumerate(range(8, 0, -1)):
        _text(template, str(rank), 80, board_y + row * cell + 14, 19, 20, align="center", bold=False)
        for file in range(8):
            square = chr(97 + file) + str(rank)
            x, y = board_x + file * cell, board_y + row * cell
            _rect(template, x, y, cell, cell, data={"role": "chess-square", "square": square})
            if (file + rank) % 2 == 1:
                template.elements.append(Element(
                    kind="image", x=_INSET + (x + 2) * _SCALE, y=(y + 2) * _SCALE,
                    w=(cell - 4) * _SCALE, h=(cell - 4) * _SCALE,
                    image_path=_pattern_path(), keep_aspect=False, z=-1,
                    data={"role": "chess-square-pattern", "square": square}))
            if square in pieces:
                _rect(template, x + 7, y + 6, cell - 14, cell - 11,
                      fill="#ffffff", stroke="#ffffff", z=2)
                _text(template, pieces[square], x, y + 6, cell, 43,
                      family="Segoe UI Symbol", bold=False, align="center", height=cell,
                      data={"role": "chess-piece", "square": square}, z=5)
    for file, label in enumerate("abcdefgh"):
        _text(template, label, board_x + file * cell, 1304, cell, 20, align="center", bold=False)
    _text(template, "O teu lance: ______________", 42, 1339, 492, 21, align="center")
    _line(template, 1387, dash=5, gap=4)
    _text(template, "“Faz uma coisa pequena", 42, 1420, 492, 24, align="center")
    _text(template, "que deixe amanhã mais fácil.”", 42, 1454, 492, 24, align="center")
    _line(template, 1503, dash=5, gap=4)
    _text(template, "TOTAL A APROVEITAR", 42, 1537, 380, 23)
    _text(template, "1 DIA", 425, 1537, 109, 23, align="right")
    _text(template, "OBRIGADO PELA VISITA AO PLANETA TERRA.", 42, 1589, 492, 18, align="center")
    _line(template, 1635, dash=5, gap=4)
    _text(template, "DOBRA AQUI ANTES DE ESPIAR", 42, 1667, 492, 18, spacing=1.8, align="center")
    _text(template, "Solução: Dg7# · dama de g6 para g7.", 42, 1700, 492, 18,
          align="center", rotation=180)
    _text(template, "ESBOÇO · DADOS FICTÍCIOS", 42, 1761, 492, 18,
          align="center", bold=False, spacing=.9)
    return template


def make_cinema_template() -> Template:
    template = Template(name="Cinema no sofá", width_mm=80, height_mm=1545 / 8,
                        cut_markers=[CutMarker(129.375, "full")])
    for name, value in {"film": "INTERSTELLAR", "film_meta": "2014 · 169 MIN · FICÇÃO CIENTÍFICA",
                        "date": "14 NOV 2026", "date_short": "14.11.2026", "time": "21:30",
                        "room": "LÁ DE CASA", "seat": "O DO COSTUME", "number": "0001"}.items():
        template.variable_manager.set_variable(name, value)
    _rect(template, 0, 0, 576, 29, fill="#000000", data={"personal_template": "cinema-v1"})
    for x in range(15, 576, 44):
        _rect(template, x, 8, 13, 14, fill="#ffffff", stroke="#ffffff", z=1)
    _text(template, "BILHETE INDIVIDUAL", 44, 78, 350, 18, spacing=1.8)
    _text(template, "N.º {{var:number}}", 395, 78, 137, 18, spacing=1.8, align="right")
    _text(template, "UMA PRODUÇÃO CÁ DE CASA", 44, 145, 488, 19, spacing=4.5, align="center")
    _text(template, "CINEMA", 44, 187, 488, 75, family="Arial Black", spacing=-3.7, align="center")
    _text(template, "NO SOFÁ.", 44, 254, 488, 75, family="Arial Black", spacing=-3.7, align="center")
    _text(template, "A MELHOR SALA É A NOSSA.", 44, 340, 488, 20, spacing=1.2, align="center")
    _line(template, 396, x=44, width=488)
    _line(template, 402, x=44, width=488)
    _text(template, "EM EXIBIÇÃO", 44, 442, 488, 19, spacing=3)
    _text(template, "{{var:film}}", 44, 484, 488, 51, family="Arial Black", spacing=-1.8)
    _text(template, "{{var:film_meta}}", 44, 544, 488, 18)
    _text(template, "SÁBADO", 44, 631, 300, 19, spacing=3)
    _text(template, "{{var:date}}", 44, 668, 300, 28)
    _text(template, "SESSÃO", 390, 610, 142, 19, spacing=3)
    _text(template, "{{var:time}}", 390, 648, 142, 58, family="Arial", spacing=-1.8)
    _line(template, 728, x=44, width=488, dash=5, gap=4)
    _text(template, "SALA", 44, 758, 244, 19, spacing=3)
    _text(template, "LUGAR", 300, 758, 232, 19, spacing=3)
    _text(template, "{{var:room}}", 44, 796, 244, 28)
    _text(template, "{{var:seat}}", 300, 796, 232, 28)
    _line(template, 846, x=44, width=488, dash=5, gap=4)
    _text(template, "ENTRADA", 44, 893, 155, 22)
    _text(template, "1 TAÇA DE PIPOCAS", 208, 888, 324, 31, align="right")
    _text(template, "LUZES APAGADAS. MANTA PREPARADA.", 44, 953, 488, 18, align="center")
    _text(template, "INTERVALO QUANDO NOS APETECER.", 44, 979, 488, 18, align="center")
    # The original decorative perforation is replaced by physical cut metadata.
    _text(template, "DESTACAR · PREENCHER · GUARDAR", 44, 1077, 488, 18,
          spacing=2.2, align="center")
    _text(template, "{{var:date_short}}", 44, 1128, 320, 18, spacing=1.8)
    _text(template, "N.º {{var:number}}", 395, 1128, 137, 18, spacing=1.8, align="right")
    _text(template, "{{var:film}}", 44, 1171, 488, 26)
    _text(template, "A MINHA NOTA", 44, 1238, 250, 22)
    _text(template, "☆☆☆☆☆", 310, 1229, 222, 41, family="Segoe UI Symbol", bold=False,
          spacing=3, align="right")
    _text(template, "Vi com:", 44, 1303, 488, 21)
    _line(template, 1359, x=44, width=488, dash=5, gap=4)
    _text(template, "Fica para a memória:", 44, 1394, 488, 21)
    _line(template, 1451, x=44, width=488, dash=5, gap=4)
    _text(template, "ARQUIVO DE NOITES BEM PASSADAS.", 44, 1488, 488, 17,
          spacing=1.1, align="center")
    return template


def _preview(template):
    from PySide6.QtWidgets import QApplication
    if QApplication.instance() is None:
        return None
    from .printing.jobs import ThermalProfile
    from .ui.print_render import prepare_print_job
    return prepare_print_job(template, ThermalProfile()).preview


def ensure_personal_templates(repository: LibraryRepository) -> None:
    """Seed once, recording IDs independently of later edits, renames or trash.

    Failed initialisation moves newly created entries to recoverable trash and
    leaves existing user layouts untouched. A retry starts a fresh pair.
    """
    marker = repository.root / _MARKER
    if marker.exists():
        with marker.open(encoding="utf-8") as stream:
            state = json.load(stream)
        if (not isinstance(state, dict) or state.get("schema_version") != 1
                or set(state.get("layouts", {})) != {"daily", "cinema"}):
            raise ValueError("Invalid personal layout seed marker; existing layouts were preserved")
        return
    # If the process stopped before publishing the marker, adopt already
    # created native tickets by their persistent tag rather than their name.
    # Entries rolled back into trash are deliberately excluded from this scan.
    seeded = {}
    tags = {"daily-v1": "daily", "cinema-v1": "cinema"}
    for entry in repository.list_layouts():
        try:
            template = repository.load(entry.id)
        except (ValueError, OSError, TypeError):
            continue
        for element in template.elements:
            data = element.data if isinstance(element.data, dict) else {}
            tag = data.get("personal_template")
            key = tags.get(tag) if isinstance(tag, str) else None
            if key:
                seeded.setdefault(key, entry.id)
                break
    created = {}
    pending = None
    try:
        for key, factory in (("daily", make_daily_template), ("cinema", make_cinema_template)):
            if key in seeded:
                continue
            template = factory()
            created[key] = repository.save(template, preview=_preview(template)).id
            seeded[key] = created[key]
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=repository.root,
                                         prefix=".personal-layouts-", suffix=".tmp", delete=False) as stream:
            pending = Path(stream.name)
            json.dump({"schema_version": 1, "layouts": seeded}, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, marker)
    except Exception as error:
        for layout_id in created.values():
            try:
                repository.trash(layout_id)
            except OSError as rollback_error:
                error.add_note(f"Could not move incomplete seed {layout_id} to trash: {rollback_error}")
        raise
    finally:
        if pending is not None and pending.exists():
            pending.unlink()
