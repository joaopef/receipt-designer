# Verificação da biblioteca pessoal

## Base e implementação

- Base upstream: `bd671b0ed0c663f485d2c16876d9ab7e14dc6c84`.
- Fork: `joaopef/receipt-designer`, branch `feat/personal-layout-library`.
- Baseline: 107 testes passaram com Qt ativado.
- Após integração: 194 testes passaram.
- Revisão independente: cinco falhas funcionais importantes reproduzidas; uma segunda revisão encontrou também a perda do estado pendente após recuperação.
- Após correções da revisão: **209 testes passaram**, sem avisos, incluindo
  transmissão TCP real num servidor local e testes da interface Qt.

Comando usado em Windows:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:RUN_QT_TESTS='1'
.venv/Scripts/python.exe -m pytest -v
```

Os testes headless registam fontes Windows explicitamente: o plugin offscreen
do Qt não carregava a base de fontes do sistema. A aplicação interativa usa o
motor Windows normal. Os testes TCP exigiram acesso a sockets fora da sandbox.

## Correções verificadas

1. Recursos de imagem conservados entre gravações, incluindo os necessários
   para desfazer uma eliminação ou substituição de imagem.
2. Alterações apenas nas variáveis tornam o documento pendente e entram na
   recuperação automática, mesmo com um indicador de alterações desatualizado.
3. Ordem de sobreposição preservada entre editor, preparação e reabertura,
   incluindo objetos com o mesmo valor de z.
4. Inspeção de alterações sem terminar a edição de texto em linha.
5. Objetos carregados recuperam visibilidade, rotação e camada; o texto resolve
   as variáveis do documento correto.

Também foram verificados espaçamento positivo/negativo entre letras, cache
após editar variáveis, rotação de texto a 180° sem espelhamento, recursos
portáveis e instalação inicial dos exemplos sem substituir alterações.

A recuperação foi validada também através de dois arranques consecutivos: as
alterações mantêm-se pendentes até guardar, no mesmo ID da biblioteca.

## Teste físico confirmado pelo utilizador

O novo motor preparou um talão de 50 mm, com texto, uma linha de 2 píxeis,
corte completo a 25 mm e corte no fim. O utilizador autorizou o envio e
confirmou que o texto e a linha saíram nítidos e os dois cortes corretos.

O ensaio usou a Ethernet direta já existente, com origem `192.168.1.20` e
índice de interface Windows 10. São dados dessa instalação, não valores fixos
do produto. O modo normal da aplicação usa o encaminhamento do sistema.

Os modelos completos nativos Diário/Cinema foram comparados visualmente em
PNG. O ensaio físico desta implementação foi o talão curto, não uma nova
tiragem dos dois modelos completos.

## Decisões de execução

- Cópia dedicada numa branch de funcionalidade em vez de outro worktree ligado:
  isola o trabalho sem tocar em repositórios existentes; custo de reversão é
  apenas mudar a localização de trabalho.
- Registo de progresso nativo Windows em vez dos helpers bash: conserva as
  decisões e evidência; só muda o mecanismo de registo.
- Trabalho dividido por três subagentes a pedido do utilizador, seguido de
  revisão independente; exige coordenação das interfaces partilhadas.
- V1 reduzida: sem CI novo, histórico de revisões, quotas arbitrárias ou QA
  formal a 150%; essas conveniências ficam para evolução posterior.
- Biblioteca inicial em Documentos, visível e selecionável, em vez de AppData:
  facilita cópia e consulta; o caminho pode ser alterado pela interface.
- Conservado o autosave ao fechar do upstream; a deteção de alterações foi
  corrigida, incluindo variáveis e edição em linha.

## Empacotamento

O primeiro build encontrou uma DLL ICU incompatível de uma instalação Poppler
no PATH do ambiente. O ficheiro `.spec` exclui essa DLL estrangeira, permitindo
ao Qt usar a API ICU do Windows. Não são redistribuídos binários do sistema.
O executável foi aberto fora da árvore de código e apresentou a biblioteca e os modelos nativos. A validação interativa final está registada abaixo.

O estilo Fusion e a paleta explícita do tema claro evitam
texto branco sobre botões claros herdado do tema escuro do Windows.
A regressão foi reproduzida antes da correção e incluída na suite final.

## Validação do executável entregue

Build PyInstaller terminou com código 0. O ficheiro entregue em outputs foi
aberto fora da árvore de código, com uma biblioteca de teste isolada. A interface
apresentou botões legíveis com Fusion; o modelo criado e guardado anteriormente
reapareceu após relançar e abriu com os seus elementos. Uma nova edição foi
guardada também na versão final. Não foi usado Python para arrancar o .exe.

Não foi feito um ensaio numa instalação limpa de Windows nem uma nova tiragem
física dos dois modelos completos. A ligação física validada foi o teste curto
já confirmado pelo utilizador.

## Correção da altura das propriedades

O painel devolvia altura mínima zero. No estilo Fusion, a área com scroll
comprimiu linhas de formulários abaixo da altura mínima dos controlos (até
1 px numa janela curta), cortando o texto. Passou a conservar a altura mínima
do layout, mantendo a largura reduzida e usando deslocamento vertical.

Dois testes reproduziram a falha antes da correção, com alturas de 480 e 900.
Ambos passaram depois; verificam a altura de todos os campos visíveis e o
acesso aos últimos campos através do scroll. Suite completa: 211 passaram.

## FIT ao conteúdo

Opção por documento (schema 2 aditivo), com guardar/reabrir e Desfazer/Refazer.
Recorta apenas linhas brancas exteriores do raster final, mantém largura/escala,
respeita margens verticais e conserva todos os cortes. Um rascunho vazio pode
ser guardado; o envio FIT sem tinta é recusado.

239 testes passaram na árvore final. A revisão independente comparou o stream
FIXED com d45718a em 32 cenários e no Cinema: bytes idênticos. No rascunho RAM,
renderizado com as fontes Windows nativas, a imagem passou de 576x600 para
576x175 pontos (75 para 21,875 mm), sem mudar as letras.

O .exe v3 arrancou fora da árvore de código, numa biblioteca de teste isolada,
com o botão FIT visível e o layout de teste carregado. O guia distingue a página
de trabalho da saída recortada e da margem física do cortador.

A referência ESC/POS Epson GS V documenta a separação entre cabeça e cortador
e que a margem inicial depende do modelo. Isso explica o tipo de espaço visto
na fotografia, mas não é uma medição nem um manual da AB-88H:
https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_cv.html
Não foram alterados avanço de corte, backfeed nem firmware da impressora.

## Isolamento dos testes

A análise revelou que testes antigos podiam eliminar o autosave do utilizador:
usavam TempLocation real. A fixture de sessão passou a isolar temporários,
biblioteca e preferências QSettings, mesmo sem RUN_QT_TESTS. A suite completa
foi repetida com esse isolamento: 239 passaram em 14,73 s. Foi conservada
uma cópia local do rascunho existente, sem alterar o documento aberto.

## Versão conjunta v5 — 15 de novembro de 2026

Integrado por fast-forward o commit 57302a9 do Opus, conservando o autor e o
histórico. A cópia work/receipt-designer-estilos ficou intacta e o executável
v4 mantém SHA256 73AD156A01848B88620222130B3273A8971BCB77B0BB2D37CA6C3713A43A21A2.
A v5 mantém linhas tracejadas e texto branco, FIT e os 18 modelos da coleção.

A renomeação podia publicar corretamente o novo documento e falhar apenas na
limpeza de assets ReadOnly da cópia antiga. A limpeza agora trata ReadOnly
Windows somente dentro das transações da biblioteca, sem mudar ACLs, seguir
links ou alterar atributos de ficheiros com ligações físicas fora da transação.
Outras falhas de limpeza depois da publicação conservam a cópia para nova
tentativa, sem reportar que a gravação já concluída falhou. A recuperação não
apaga a cópia antiga se o documento publicado estiver inválido.

Regressões novas reproduzidas antes de corrigir: atributos ReadOnly, limpeza
parcial, JSON estruturalmente inválido e proteção de ligações físicas. Suporte
ao callback de Python 3.10/3.11 mantido. Suite conjunta: 290 testes passaram
em 96,05 s, incluindo os 30 testes de estilos/cor do Opus e os 18 modelos.

Após criar uma cópia local da biblioteca, a gravação foi validada nos dois
modelos originais usando o próprio nome atual: 001Diário de bordo e Cinema
no sofá. Todos os campos e recursos foram comparados antes/depois; intactos.
Restaram zero cópias temporárias de substituição. Nenhuma impressão física.

## Limpeza da extração onefile — v6

O aviso ao fechar a v5 referia a pasta de QA v5-qa-temp/_MEI00006a882.
Restavam 26 diretórios, todos só de leitura, e zero ficheiros. A tentativa
de remover um diretório vazio reproduziu WinError5; remover o atributo
permitiu limpar a árvore. A biblioteca não pertencia a essa extração.

A v6 regista um callback de saída só em Windows/frozen/onefile. Limpa apenas
o atributo ReadOnly de diretórios dentro do próprio sys._MEIPASS, sem
apagar ficheiros, alterar ACLs ou percorrer ligações. O bootloader conserva
a responsabilidade de remover a extração quando o processo Python termina.

Testes unitários: 3 passaram, 1 ignorado porque esta sessão Windows não
permite criar symlinks. Suite completa: 293 passaram, 1 ignorado em 36,17 s.
Um probe onefile separado criou 3 diretórios ReadOnly, fechou com código 0 e
o bootloader removeu toda a extração, sem aviso nem restos. Este é um ensaio
real do fecho empacotado; não é uma nova verificação visual da interface.

Referência do comportamento de limpeza no bootloader 6.22.3:
https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/bootloader/src/pyi_utils_win32.c
A extração vazia da v5 indicada no aviso foi removida após verificar caminho,
ausência de ficheiros e ausência de ligações. Nenhuma impressão física.
