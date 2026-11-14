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
