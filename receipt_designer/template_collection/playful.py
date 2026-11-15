"""Six original, editable pocket games and keepsakes for the local collection."""
from __future__ import annotations

from ..core.models import Element, Template
from .design import PPM, Ticket


_SUDOKU_PUZZLE = (
    '530070000',
    '600195000',
    '098000060',
    '800060003',
    '400803001',
    '700020006',
    '060000280',
    '000419005',
    '000080079',
)
_SUDOKU_SOLUTION = (
    '534678912',
    '672195348',
    '198342567',
    '859761423',
    '426853791',
    '713924856',
    '961537284',
    '287419635',
    '345286179',
)
_CHESS_FEN = '7k/8/5KQ1/8/8/8/8/8 w - - 0 1'


def _segment(ticket, x1, y1, x2, y2, *, role, stroke=2):
    ticket.template.elements.append(Element(
        'line', x1 * PPM, y1 * PPM,
        (x2 - x1) * PPM, (y2 - y1) * PPM,
        stroke_px=stroke, z=2,
        data={'collection': 'thermal-ideas-v1', 'slug': ticket.slug, 'role': role}))


def _sudoku_grid(ticket, rows, top, *, solution=False):
    x0, cell = 13, 6
    role = 'sudoku-solution' if solution else 'sudoku-given'
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            if value == '0':
                continue
            ticket.text(value, top + row * cell + .55,
                        x=x0 + column * cell, w=cell, h=4.9,
                        size=14, bold=True, align='center', role=role)
            ticket.template.elements[-1].data.update(row=row, column=column, digit=int(value))
    for index in range(10):
        stroke = 3 if index % 3 == 0 else 2
        _segment(ticket, x0, top + index * cell, x0 + 54,
                 top + index * cell, role='sudoku-grid', stroke=stroke)
        _segment(ticket, x0 + index * cell, top, x0 + index * cell,
                 top + 54, role='sudoku-grid', stroke=stroke)


def _sudoku():
    ticket = Ticket('playful-sudoku', '13 · Sudoku de bolso', height=210)
    ticket.header('JOGOS DE BOLSO / 01', 'Sudoku de bolso',
                  subtitle='Um número por casa. Sem pressa.')
    ticket.template.elements[0].data.update(
        puzzle=list(_SUDOKU_PUZZLE), solution=list(_SUDOKU_SOLUTION),
        puzzle_digits=''.join(_SUDOKU_PUZZLE),
        solution_digits=''.join(_SUDOKU_SOLUTION),
        game='sudoku', difficulty='clássico')
    ticket.section('UM MOMENTO DE FOCO', 33)
    _sudoku_grid(ticket, _SUDOKU_PUZZLE, 41)
    ticket.text('Completa cada fila, coluna e bloco\ncom os números de 1 a 9.',
                101, family='Arial', size=11, h=10)
    ticket.text('A solução fica no canhoto. Guarda-a à parte.',
                114, family='Arial', size=9, h=5)
    ticket.cut(123)
    ticket.section('CANHOTO / SOLUÇÃO', 129)
    _sudoku_grid(ticket, _SUDOKU_SOLUTION, 139, solution=True)
    ticket.footer('Um quadrado de cada vez.', 199)
    return ticket.build()


def _chess():
    ticket = Ticket('playful-chess-mate', '14 · Um lance de xadrez', height=190)
    ticket.header('TABULEIRO DE BOLSO / 02', 'Um lance de xadrez',
                  subtitle='Brancas jogam. Mate em um lance.')
    ticket.template.elements[0].data.update(
        game='chess', fen=_CHESS_FEN, solution_uci='g6g7', solution_san='Qg7#',
        pieces={'f6': 'K', 'g6': 'Q', 'h8': 'k'})
    x0, top, cell = 16, 40, 6
    for row in range(8):
        rank = 8 - row
        ticket.text(str(rank), top + row * cell + 1.25,
                    x=10, w=4, h=3.8, size=9, align='center', role='chess-rank')
        for column in range(8):
            x, y = x0 + column * cell, top + row * cell
            dark = (column + rank) % 2 == 1
            square = f'{chr(97 + column)}{rank}'
            ticket.rect(x, y, cell, cell, fill='#ffffff', role='chess-square')
            ticket.template.elements[-1].data.update(square=square, dark=dark)
            if dark:
                # Editable diagonal hatching survives monochrome thresholding.
                for offset in (1.5, 3, 4.5, 6, 7.5, 9, 10.5):
                    _segment(ticket,
                             x + max(0, offset - cell), y + min(cell, offset),
                             x + min(cell, offset), y + max(0, offset - cell),
                             role='chess-hatch')
    for column in range(8):
        ticket.text(chr(97 + column), 91, x=x0 + column * cell,
                    w=cell, h=3.8, size=9, align='center', role='chess-file')
    for square, label in [('f6', 'WK'), ('g6', 'WQ'), ('h8', 'BK')]:
        column, row = ord(square[0]) - ord('a'), 8 - int(square[1])
        x, y = x0 + column * cell, top + row * cell
        ticket.rect(x + .45, y + .45, 5.1, 5.1, fill='#ffffff', role='chess-piece-backplate')
        ticket.template.elements[-1].z = 3
        ticket.text(label, y + 1.15, x=x + .45, w=5.1, h=4.1,
                    size=10, bold=True, align='center', role='chess-piece')
        ticket.template.elements[-1].data.update(square=square, piece={'WK': 'K', 'WQ': 'Q', 'BK': 'k'}[label])
    ticket.text('WK = rei branco  |  WQ = dama branca\nBK = rei preto',
                99, size=9, family='Arial', h=9)
    ticket.section('O TEU LANCE', 113)
    ticket.writing(122, count=1)
    ticket.cut(132)
    ticket.section('CANHOTO / SOLUÇÃO', 139)
    ticket.text('Qg7#', 148, size=30, family='Arial Black', h=12, role='chess-solution')
    ticket.text('A dama chega a g7. O rei branco\nprotege-a. Não há casa de fuga.',
                164, size=11, family='Arial', h=11)
    ticket.footer('Dama em g7: xeque-mate.', 181)
    return ticket.build()


def _poem():
    ticket = Ticket('playful-poem', '15 · Poema para guardar', height=169)
    ticket.text('UM ORIGINAL EM PAPEL', 4, size=10, bold=True, spacing=.7)
    ticket.text('O que fica', 14, size=29, family='Arial Black', h=12)
    ticket.line(30)
    ticket.rect(8, 36, 3, 3, fill='#000000', role='poem-ornament')
    poem = [
        'Cabe um dia neste papel:',
        'a chávena ainda morna,',
        'o nome dito à porta,',
        'um sol pousado no chão.',
        'O resto passa depressa.',
        'Eu dobro esta pequena luz',
        'e levo no bolso',
        'o que não pesa na mão.',
    ]
    for index, verse in enumerate(poem):
        ticket.text(verse, 44 + index * 8, size=14, family='Arial', h=6, role='poem-verse')
    signature = ticket.var('assinatura', 'Quem guardou este instante')
    ticket.text(signature, 119, size=11, h=9, family='Courier New', role='poem-signature')
    ticket.writing(135, count=1, w=38)
    ticket.text('Texto original desta coleção.\nAcrescenta o teu nome ou oferece-o sem assinatura.',
                142, size=9, family='Arial', h=10)
    ticket.footer('Guarda. Dobra. Oferece.', 159)
    return ticket.build()


def _voucher():
    ticket = Ticket('playful-good-idea', '16 · Vale uma boa ideia', height=231)
    ticket.text('NÃO TEM CÓDIGO. TEM INTENÇÃO.', 4, size=10, bold=True)
    ticket.line(10)
    ticket.text('VALE UMA\nBOA IDEIA', 15, size=26, family='Arial Black', h=20)
    experience = ticket.var('experiencia', 'Um café e uma boa conversa')
    recipient = ticket.var('para', 'Alguém especial')
    sender = ticket.var('de', 'Quem te faz este convite')
    when = ticket.var('quando', 'Quando nos der jeito')
    ticket.rect(8, 42, 64, 43, role='voucher-frame')
    ticket.text('DESTA VEZ VALE', 47, x=11, w=58, size=11, bold=True, spacing=.5)
    ticket.text(experience, 56, x=11, w=58, size=16,
                bold=True, family='Arial', h=15, role='voucher-offer')
    ticket.text('café / jantar / escolher o filme', 76,
                x=11, w=58, size=9, family='Arial', h=5)
    ticket.section('PARA', 93)
    ticket.text(recipient, 99, size=12, h=8)
    ticket.section('DE', 111)
    ticket.text(sender, 117, size=12, h=8)
    ticket.text('Sem prazo para a boa companhia.', 133, size=10, family='Arial', h=6)
    ticket.cut(147)
    ticket.section('CANHOTO / O COMBINADO', 154)
    ticket.text(experience, 165, size=14, bold=True, family='Arial', h=15)
    ticket.section('QUANDO', 184)
    ticket.text(when, 191, size=12, h=8)
    ticket.section('UMA NOTA PARA NÓS', 205)
    ticket.writing(215, count=1)
    ticket.footer('Uma ideia boa merece acontecer.', 222)
    return ticket.build()


def _memory():
    ticket = Ticket('playful-day-memory', '17 · Memória do dia', height=201)
    ticket.header('ARQUIVO DE PEQUENAS COISAS', 'Memória do dia',
                  subtitle='Um espaço para o que queres lembrar.')
    date = ticket.var('data', 'DD / MM / AAAA')
    caption = ticket.var('legenda', 'Uma pequena coisa que ficou.')
    ticket.text(date, 32, size=11, align='right', h=5)
    ticket.rect(12, 42, 56, 42, role='photo-placeholder')
    ticket.text('INSERIR FOTO', 57, x=14, w=52, size=12,
                bold=True, align='center', h=6, role='photo-placeholder-label')
    ticket.text('moldura editável / sem imagem', 65, x=14, w=52,
                size=9, family='Arial', align='center', h=5)
    ticket.text(caption, 90, size=12, family='Arial', h=10, role='photo-caption')
    for prompt, top in [('UM DETALHE QUE VI', 107),
                        ('UM SOM OU UMA FRASE', 134),
                        ('COM QUEM ESTIVE', 161)]:
        ticket.section(prompt, top)
        ticket.writing(top + 11, count=2, gap=6)
    ticket.footer('O dia passa. Este detalhe fica.', 190)
    return ticket.build()


def _adventure():
    ticket = Ticket('playful-pocket-adventure', '18 · Bilhete de aventura', height=226)
    ticket.header('UMA MISSÃO PEQUENA / 03', 'Bilhete de aventura',
                  subtitle='Uma caça ao detalhe, onde já estás.')
    mission = ticket.var('missao', 'Descobrir três coisas que costumas não ver.')
    when = ticket.var('quando', 'Hoje, ao meu ritmo')
    ticket.text(mission, 35, size=13, bold=True, family='Arial', h=13, role='adventure-mission')
    steps = [
        ('01 / OLHAR DEVAGAR', 'Encontra uma forma redonda num\nobjeto do teu quotidiano.', 55),
        ('02 / OUVIR O LUGAR', 'Pára um minuto e guarda um som\nque quase passava despercebido.', 89),
        ('03 / DEIXAR UM SINAL', 'Desenha um detalhe do que viste.\nGuarda-o neste bilhete.', 123),
    ]
    for label, instructions, top in steps:
        ticket.section(label, top)
        ticket.text(instructions, top + 7, size=11, family='Arial', h=11)
        ticket.check('Missão cumprida.', top + 22)
    ticket.section('REGISTO DE CHEGADA', 159)
    ticket.text(when, 166, size=11, h=7)
    ticket.text('O meu detalhe:', 178, size=10, h=5)
    ticket.rect(8, 186, 64, 23, role='adventure-record')
    ticket.footer('A aventura cabe numa pausa.', 216)
    return ticket.build()


def build_playful() -> list[Template]:
    """Return six independent native layouts, without I/O or library writes."""
    return [_sudoku(), _chess(), _poem(), _voucher(), _memory(), _adventure()]
