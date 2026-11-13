# Desenvolvimento da biblioteca pessoal

Base upstream: `bd671b0ed0c663f485d2c16876d9ab7e14dc6c84`.
Fork: https://github.com/joaopef/receipt-designer
Branch: `feat/personal-layout-library`.

Python 3.13, ambiente virtual local `.venv`. Dependências validadas em
`requirements-lock.txt`. Em PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
$env:RUN_QT_TESTS='1'
$env:QT_QPA_PLATFORM='offscreen'
.venv/Scripts/python.exe -m pytest -v
```

Baseline real antes das alterações funcionais: **107 testes passaram**,
com Qt ativado, em 2026-11-13. Os novos testes são escritos antes da
implementação. O plano revisto está em `docs/superpowers/plans/`.

Para executar a interface interativamente, retirar `QT_QPA_PLATFORM` do ambiente.
Para isolar biblioteca/testes, definir `RECEIPT_DESIGNER_LIBRARY` para uma pasta
dedicada. O programa não altera interfaces nem rotas Windows. A configuração
preferida é impressora e PC na mesma LAN do router; origem/interface explícitas
são opções avançadas para instalações específicas.

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m receipt_designer
.venv/Scripts/pyinstaller.exe ReceiptDesigner.spec
```

Um envio TCP bem-sucedido confirma transmissão; a saída em papel necessita de
verificação física. Não repetir automaticamente trabalhos de estado incerto.
