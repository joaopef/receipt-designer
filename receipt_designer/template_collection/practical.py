"""Six original native utility layouts; example data, never live telemetry.

Use-case inspiration (no artwork/code copied):
https://github.com/HostisHumani/ReceiptPi — lists and system/status slips.
https://github.com/cognitivegears/ha-escpos-thermal-printer — shopping/recipe slips.
"""
from __future__ import annotations

from ..core.models import Element, Template
from .design import PPM, Ticket


def _shopping() -> Template:
    t = Ticket('practical-shopping', '07 · Compras sem voltas', height=160)
    t.header('MERCADO / LISTA POR CORREDOR', 'COMPRAS', subtitle='Uma volta. Tudo o que faz falta.')
    t.text(t.var('lista_data', 'SÁBADO · 21 NOV'), 32, size=11, bold=True)
    t.text('QTD.', 32, x=59, w=13, size=10, align='right')
    categories = [
        ('FRESCOS', 41, [('tomate', 'Tomate', '6 un.'), ('fruta', 'Maçãs', '4 un.'), ('folhas', 'Espinafres', '1 saco')]),
        ('DESPENSA', 74, [('massa', 'Massa', '1 emb.'), ('aveia', 'Aveia', '500 g'), ('azeite', 'Azeite', '1 fr.')]),
        ('CASA', 107, [('sabao', 'Sabão', '1 un.'), ('papel', 'Papel cozinha', '1 emb.')]),
    ]
    for label, y, entries in categories:
        t.section(label, y).line(y+5)
        for index, (key, item, quantity) in enumerate(entries):
            row = y+8+index*7
            t.check(t.var('compra_'+key, item), row, w=49)
            t.text(t.var('quant_'+key, quantity), row, x=59, w=13, size=10, h=4.7, align='right')
    t.text('FALTA MAIS ALGUMA COISA?', 137, size=9, family='Arial', bold=True)
    t.writing(147, count=1)
    t.footer('EXEMPLO · riscar ao colocar no cesto', 151)
    return t.build()


def _recipe() -> Template:
    t = Ticket('practical-pocket-recipe', '08 · Receita de bolso', height=177)
    t.text('COZINHA / RECEITA DE BOLSO', 3, size=10, bold=True, spacing=.5)
    t.line(8)
    t.text(t.var('prato', 'TOSTA DE TOMATE'), 12, size=21, family='Arial Black', h=9)
    t.text(t.var('porcoes', '2 porções'), 24, w=31, size=12, bold=True)
    t.text(t.var('tempo', '10 minutos'), 24, x=42, w=30, size=12, align='right')
    t.line(31)
    t.section('NA BANCADA', 35)
    ingredients = [('pao', '2 fatias', 'Pão'), ('tomate', '1 un.', 'Tomate maduro'),
                   ('azeite', '1 c. sopa', 'Azeite'), ('ervas', 'A gosto', 'Orégãos e sal')]
    for index, (key, amount, ingredient) in enumerate(ingredients):
        row = 44+index*7
        t.text(t.var('dose_'+key, amount), row, w=23, size=11, bold=True)
        t.text(t.var('ingrediente_'+key, ingredient), row, x=33, w=39, size=11)
    t.line(75, dash=True)
    t.section('TRÊS GESTOS', 80)
    steps = [('1', 'Lava o tomate e corta-o em fatias finas.'),
             ('2', 'Torra o pão e distribui o tomate por cima.'),
             ('3', 'Rega com azeite; termina com sal e orégãos.')]
    for index, (number, sentence) in enumerate(steps):
        row = 90+index*18
        t.rect(8, row, 7, 7)
        t.text(number, row+.5, x=8, w=7, h=6, size=17, bold=True, align='center')
        t.text(t.var('passo_'+number, sentence), row, x=18, w=54, size=12, h=14)
    t.text('A MINHA VARIAÇÃO', 147, size=9, family='Arial', bold=True)
    t.writing(157, count=1)
    t.footer('EXEMPLO CULINÁRIO · adaptar os campos ao teu gosto', 165)
    return t.build()


def _packing() -> Template:
    t = Ticket('practical-packing', '09 · Mala pronta', height=164)
    t.header('PARTIDA / CONFERIR ANTES DE SAIR', 'MALA PRONTA')
    t.rect(8, 28, 64, 16)
    t.text(t.var('destino', 'DESTINO: SERRA'), 30, x=10, w=60, size=12, bold=True)
    t.text(t.var('duracao', '3 dias · mochila leve'), 36, x=10, w=60, size=11)
    groups = [
        (8, 50, 'ESSENCIAIS', [('documentos', 'Documentos'), ('bilhetes', 'Bilhetes'), ('carteira', 'Carteira')]),
        (42, 50, 'TECNOLOGIA', [('telemovel', 'Telemóvel'), ('cabo', 'Cabo USB'), ('carregador', 'Carregador')]),
        (8, 86, 'ROUPA', [('camisolas', '3 camisolas'), ('meias', '3 pares meias'), ('casaco', 'Casaco leve')]),
        (42, 86, 'NECESSAIRE', [('escova', 'Escova'), ('pasta', 'Pasta dentes'), ('protecao', 'Protetor solar')]),
    ]
    for x, y, label, entries in groups:
        t.text(label, y, x=x, w=30, size=10, bold=True)
        t.line(y+5, x=x, w=30)
        for index, (key, sample) in enumerate(entries):
            t.check(t.var('mala_'+key, sample), y+8+index*7, x=x, w=30)
    t.line(122, dash=True)
    t.section('ÚLTIMA VOLTA À CASA', 127)
    t.check('Janelas fechadas / luzes desligadas', 135)
    t.check('Chaves na mão', 143)
    t.footer('EXEMPLO · preparar, conferir, partir', 153)
    return t.build()


def _homelab() -> Template:
    t = Ticket('practical-homelab', '10 · Radar do homelab', height=178)
    t.header('EXEMPLO / REGISTO MANUAL', 'RADAR DO LAB', subtitle='Valores fictícios. Sem ligação a equipamentos.')
    t.text(t.var('registo', 'REGISTO: 21 NOV · 09:00'), 32, size=10)
    cards = [
        (42, 'RPI', 'rpi', 'OK', 'Serviço: notas locais', 'Carga: 12% · CPU: 42 °C'),
        (77, 'TOSHIBA', 'toshiba', 'REVER', 'Portátil de bancada', 'Disco: 61% · verificar cópia'),
        (112, 'NAS', 'nas', 'OK', 'Arquivo de laboratório', 'Cópia: concluída · espaço: 38%'),
    ]
    for y, name, key, state, purpose, detail in cards:
        t.rect(8, y, 64, 29)
        t.text(name, y+2, x=11, w=32, h=7, family='Arial Black', size=18)
        t.text(t.var(key+'_estado', state), y+2, x=46, w=23, h=7, size=17, bold=True, align='right')
        t.line(y+11, x=11, w=58)
        t.text(t.var(key+'_servico', purpose), y+14, x=11, w=58, h=5, size=10)
        t.text(t.var(key+'_nota', detail), y+21, x=11, w=58, h=5, size=10)
    t.section('PRÓXIMA AÇÃO', 148)
    t.text(t.var('acao_lab', 'Rever a cópia do portátil.'), 155, size=11, h=6)
    t.footer('EXEMPLO FICTÍCIO · não representa estado em tempo real', 167)
    return t.build()


def _bookmark() -> Template:
    t = Ticket('practical-bookmark', '11 · Marca-páginas', height=120)
    t.text('LEITURA / PARA CONTINUAR', 3, size=9, bold=True, spacing=.6)
    t.line(8)
    t.text('ENTRE\nPÁGINAS', 11, size=23, family='Arial Black', h=18)
    t.line(33, dash=True)
    t.text('LIVRO', 37, size=9, family='Arial', bold=True)
    t.text(t.var('livro', 'O atlas das pequenas coisas'), 42, size=12, h=10)
    t.text(t.var('autor', 'Autor de exemplo'), 54, size=10, family='Arial')
    t.rect(8, 65, 64, 16)
    t.text('PAREI NA PÁGINA', 68, x=11, w=39, size=10, bold=True)
    t.text(t.var('pagina', '042'), 66, x=52, w=17, h=12, size=26, bold=True, align='right')
    t.text('A MINHA NOTA', 86, size=9, family='Arial', bold=True)
    for index in range(5):
        t.template.elements.append(Element(
            'star', (8+index*7)*PPM, 92*PPM, 5*PPM, 5*PPM,
            stroke_px=2, fill_color='', stroke_color='#000000',
            data={'collection': 'thermal-ideas-v1', 'slug': t.slug, 'role': 'rating-star', 'star_points': 5}))
    t.text('UMA IDEIA PARA GUARDAR', 101, size=9, family='Arial', bold=True)
    t.writing(111, count=1)
    t.text('EXEMPLO · dobrar aqui a pausa', 114, size=9, h=4, family='Arial', align='center')
    return t.build()


def _equipment() -> Template:
    t = Ticket('practical-equipment', '12 · Ficha de equipamento', height=170)
    t.text('OFICINA / INVENTÁRIO + RMA', 3, size=10, bold=True, spacing=.5)
    t.line(8)
    t.text('FICHA TÉCNICA', 12, family='Arial Black', size=23, h=9)
    t.text(t.var('inventario', 'EQ-EXEMPLO-01'), 25, size=19, bold=True, h=8)
    t.line(36)
    fields = [('EQUIPAMENTO', 'equipamento', 'Router de bancada'),
              ('MODELO', 'modelo', 'Modelo de demonstração'),
              ('N.º SÉRIE / ETIQUETA', 'serie', 'PREENCHER'),
              ('LOCALIZAÇÃO', 'localizacao', 'Prateleira da oficina')]
    for index, (label, key, sample) in enumerate(fields):
        y = 41+index*13
        t.text(label, y, size=9, family='Arial', bold=True)
        t.text(t.var(key, sample), y+4.5, size=12, h=6)
    t.line(94, dash=True)
    t.text('PEDIDO RMA', 99, w=31, size=9, family='Arial', bold=True)
    t.text('GARANTIA', 99, x=42, w=30, size=9, family='Arial', bold=True)
    t.text(t.var('rma', 'Por atribuir'), 104, w=31, size=11)
    t.text(t.var('garantia', 'A confirmar'), 104, x=42, w=30, size=11)
    t.section('SINTOMA / PRÓXIMO PASSO', 115)
    t.text(t.var('sintoma', 'Reinicia ao ligar.\nRegistar teste de alimentação.'), 123, h=15, size=12)
    t.text('ACESSÓRIOS ACOMPANHANTES', 142, size=9, family='Arial', bold=True)
    t.check('Fonte', 149, w=28)
    t.check('Cabo', 149, x=42, w=30)
    t.footer('EXEMPLO · substituir pelos dados do equipamento', 160)
    return t.build()


def build_practical() -> list[Template]:
    """Return six independent, editable 80 mm utility documents."""
    return [_shopping(), _recipe(), _packing(), _homelab(), _bookmark(), _equipment()]
