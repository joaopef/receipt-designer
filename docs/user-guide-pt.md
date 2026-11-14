# Biblioteca pessoal de talões

Abra `ReceiptDesigner-Pessoal.exe`. Não é necessário instalar Python.
A aplicação começa na biblioteca com os modelos **Diário de bordo** e
**Cinema no sofá**. Os conteúdos desses exemplos são fictícios.

## Criar e editar

- Selecione um cartão e carregue em **Abrir**, ou faça duplo clique.
- Use **Novo modelo** para começar outro desenho.
- Use o editor, os painéis de propriedades e as variáveis para alterar os
  elementos. O espaçamento entre letras aceita valores positivos e negativos.
- **Ctrl+S** guarda na biblioteca. **Biblioteca** regressa à coleção.
- Ative **FIT ao conteúdo**, junto de Preview, para retirar o branco no topo
  e no fundo da impressão. O tamanho das letras e a largura não mudam.
  A opção fica guardada nesse modelo e pode ser desfeita com Ctrl+Z.
- **Duplicar** cria um modelo independente. Pode mudar o nome e pesquisar.
- Os modelos movidos para o lixo podem ser recuperados na vista do lixo.

Ao mudar de documento com alterações pendentes, escolha guardar, descartar ou
cancelar. O mecanismo de recuperação do editor também conserva alterações
pendentes ao fechar; isso não substitui guardar a versão definitiva com Ctrl+S.

## Onde ficam os desenhos

A pasta inicial é `Documentos/Receipt Designer/Biblioteca`. O caminho aparece
na janela. **Pasta da biblioteca…** permite escolher outra pasta.

Os documentos, miniaturas e recursos são ficheiros persistentes fora do `.exe`.
Para fazer uma cópia de segurança ou mudar de computador, copie a **pasta da
biblioteca completa**, incluindo os recursos e o lixo que queira conservar.
As imagens usadas por um layout são copiadas para a biblioteca ao guardar.

Os modelos de exemplo são instalados uma vez. Editá-los, mudar-lhes o nome
ou eliminá-los não faz com que sejam substituídos no arranque seguinte.

## Impressão na AB-88H

Com **FIT ao conteúdo** ativo, a pré-visualização de impressão mostra o
comprimento ajustado. A página do editor conserva a altura de trabalho, para
continuar a desenhar; o FIT atua na saída. Respeita as margens superior e
inferior do modelo e conserva os cortes intermédios, incluindo os que estão
depois do último texto. Sem tinta visível, pode guardar o rascunho, mas a
aplicação recusa imprimir uma página vazia em FIT.

O recorte retira branco da imagem. O avanço antes do corte configurado em
**Config** continua a ser aplicado, e pode existir espaço físico entre a
cabeça de impressão e a lâmina. O FIT não promete uma borda física de zero
milímetros. Não reduzir automaticamente esse avanço evita cortar texto.

O perfil de referência usa papel de 80 mm, área imprimível de 72 mm,
imagem de 576 píxeis e TCP `192.168.1.10:9100`. O endereço é configurável.
Use a pré-visualização para verificar os mesmos píxeis que serão enviados.

A configuração preferida liga impressora e PC à mesma rede LAN do router.
As opções avançadas de IP de origem e índice de interface destinam-se a
ligações diretas específicas. Um IP temporário pode desaparecer ao reiniciar;
o programa não altera endereços nem rotas do Windows.

Nesta impressora, **Dark** e **Slow** foram ativados fisicamente por
**DIP 6=ON** e **DIP 7=ON**, com a impressora desligada. O **Limiar preto/branco**
do editor apenas converte a imagem e não muda esses interruptores.

**Cortes intermédios…** permite definir posições em milímetros e corte completo
ou parcial. As guias dos cortes não são impressas. O modelo do cinema separa
o bilhete e o canhoto. A margem entre cabeça e lâmina pode precisar de ajuste
para outras impressoras.

“Dados enviados” confirma a transmissão, não o resultado físico. Se o envio
ficar incerto, verifique primeiro o papel: o programa não repete o trabalho
automaticamente.

## Formatos e limites desta versão

Os modelos são JSON nativo do Receipt Designer. Importar um PNG cria um objeto
de imagem; não transforma automaticamente as suas letras em texto editável.
Os dois modelos fornecidos foram reconstruídos como elementos editáveis.

Esta versão conserva o editor original e acrescenta a biblioteca e os cortes.
A tradução dos novos ecrãs está em PT-PT; partes do editor original continuam
em inglês. Meteorologia online, calendários e impressão diária agendada são
possíveis desenvolvimentos posteriores.
