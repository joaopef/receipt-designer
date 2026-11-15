"""Six pocket rituals; sample data is deliberately not presented as live data."""
from .design import Ticket


def build_routine():
    result = []

    t = Ticket('routine-morning', '01 · Jornal da manhã', height=160)
    t.header('UM DIA, UMA EDIÇÃO', 'HOJE.', subtitle='{{date:%d/%m/%Y}}    O essencial cabe aqui.')
    t.section('LÁ FORA / EXEMPLO', 33)
    t.text(t.var('tempo', '17° / 11°   Chuva à tarde'), 39, size=15, family='Arial', h=6)
    t.text(t.var('lembrete_tempo', 'Levar o guarda-chuva.'), 46, family='Arial', h=5)
    t.line(54, dash=True).section('AS TRÊS COISAS DE HOJE', 58)
    for i, task in enumerate(('Resolver a tarefa pendente', 'Passar na encomenda', 'Dar uma volta sem ecrãs')):
        t.check(t.var(f'prioridade_{i+1}', task), 64+i*7)
    t.line(88).section('HORA MARCADA / EXEMPLO', 92)
    for i, (time, plan) in enumerate((('09:00', 'Primeiro bloco de trabalho'), ('13:00', 'Pausa a sério'), ('18:30', 'Voltar ao que gosto'))):
        t.text(time, 99+i*6, w=14, bold=True)
        t.text(t.var(f'agenda_{i+1}', plan), 99+i*6, x=24, w=48, size=11, h=5)
    t.line(120, dash=True)
    t.text('Faz hoje uma coisa que\ndeixe amanhã mais leve.', 126, size=15, family='Arial', h=11)
    t.footer('Agenda e meteorologia de exemplo · edita as variáveis.', 145)
    result.append(t.build())

    t = Ticket('routine-three', '02 · Três coisas e chega', height=140)
    t.text('RECIBO DE ATENÇÃO', 3, size=10, bold=True)
    t.text('3', 9, w=21, h=17, size=55, family='Arial Black')
    t.text('COISAS\nE CHEGA.', 11, x=31, w=41, h=15, size=22, family='Arial Black')
    t.line(30).text('O resto pode esperar.', 34, family='Arial', size=13, h=5)
    for i, label in enumerate(('A que mais importa', 'A que desbloqueia outra', 'A pequena vitória')):
        y = 45+i*22
        t.rect(8, y, 6, 6).text(f'0{i+1}', y+.7, x=8.5, w=5, size=10, align='center', bold=True)
        t.text(label, y+.2, x=17, w=55, size=11, bold=True)
        t.text(t.var(f'tarefa_{i+1}', 'Escrever aqui a tarefa'), y+7, x=17, w=55, h=7, family='Arial', size=13)
        t.line(y+17, x=17, w=55)
    t.text('Se só fizer uma: __________________', 115, size=11)
    t.footer('O objetivo é terminar. Não é encher a lista.', 127)
    result.append(t.build())

    t = Ticket('routine-agenda', '03 · Agenda de bolso', height=150)
    t.header('LEVAR COMIGO', 'O MEU DIA', subtitle='{{date:%d/%m/%Y}}    Compromissos e espaço livre')
    plans = [('08:00', 'Preparar o dia'), ('10:00', 'Trabalho com atenção'), ('12:00', 'Almoço / pausa'),
             ('14:00', 'Compromisso a preencher'), ('16:00', 'Pendentes e recados'), ('18:00', 'Tempo fora do trabalho'), ('20:00', 'Uma coisa boa')]
    for i, (time, plan) in enumerate(plans):
        y = 35+i*10
        t.text(time, y, w=15, bold=True, size=12)
        t.text(t.var(f'bloco_{i+1}', plan), y, x=26, w=46, h=6, family='Arial', size=12)
        t.line(y+7)
    t.section('SE SOBRAR TEMPO', 110).writing(123, count=2, gap=7)
    t.footer('Horas e compromissos são exemplos editáveis.', 138)
    result.append(t.build())

    t = Ticket('routine-sprint', '04 · Sprint de 25 minutos', height=135)
    t.header('UMA COISA DE CADA VEZ', '25 MIN.', subtitle='Foco agora. Pausa depois.')
    t.section('A MISSÃO', 34)
    t.text(t.var('missao', 'Avançar uma tarefa sem interrupções'), 40, family='Arial', size=14, h=10)
    t.line(53).text('COMEÇO: ______    FIM: ______', 58, size=12)
    t.text('BLOCO', 68, w=17, size=11, bold=True)
    t.text('FOCO', 68, x=30, w=19, size=11, bold=True)
    t.text('PAUSA', 68, x=54, w=18, size=11, bold=True)
    for i in range(4):
        y = 75+i*8
        t.text(f'0{i+1}', y, w=12, bold=True)
        t.rect(30, y, 3.3, 3.3).text('25 min', y, x=35, w=15, size=11)
        t.rect(54, y, 3.3, 3.3).text('5 min', y, x=59, w=13, size=11)
    t.line(110, dash=True).text('Próximo passo: __________________', 115, size=11)
    t.footer('Usa um temporizador à parte. O papel regista o progresso.', 124)
    result.append(t.build())

    t = Ticket('routine-evening', '05 · Fecho do dia', height=155)
    t.text('{{date:%d/%m/%Y}}', 4, align='right', size=10)
    t.text('POR HOJE,', 12, align='center', family='Arial', size=22, h=8)
    t.text('FEITO.', 22, align='center', family='Arial Black', size=32, h=11)
    t.line(38)
    for y, label in [(44, 'Uma coisa que correu bem'), (72, 'Uma coisa que aprendi'), (100, 'O que deixo preparado para amanhã')]:
        t.text(label, y, family='Arial', size=12, h=6)
        t.writing(y+13, count=2, gap=7)
    t.line(133, dash=True).text('Não preciso de levar o dia todo para a cama.', 138, family='Arial', size=10, h=5, align='center')
    result.append(t.build())

    t = Ticket('routine-habits', '06 · Pequenos hábitos', height=145)
    t.header('UMA SEMANA EM PAPEL', 'PEQUENOS\nHÁBITOS')
    # Two-line title uses a larger explicit box rather than compressing its type.
    title = t.template.elements[-2]
    title.h = 15 * (203 / 25.4)
    t.template.elements.pop()  # replace header rule below the two-line title
    t.line(30).text(t.var('semana', 'Semana de ____ / ____ a ____ / ____'), 34, size=11)
    for i, day in enumerate(('S', 'T', 'Q', 'Q', 'S', 'S', 'D')):
        t.text(day, 45, x=29+i*6, w=5, size=10, align='center', bold=True)
    for i, habit in enumerate(('Ler', 'Caminhar', 'Criar', 'Arrumar')):
        y = 53+i*13
        t.text(t.var(f'habito_{i+1}', habit), y, w=20, size=11, h=7)
        for day in range(7):
            t.rect(29+day*6, y+.5, 4.4, 4.4, role='habit-cell')
        t.line(y+10)
    t.section('O QUE AJUDOU ESTA SEMANA?', 111).writing(124, count=2, gap=7)
    t.footer('Recomeçar também conta.', 138)
    result.append(t.build())
    return result
