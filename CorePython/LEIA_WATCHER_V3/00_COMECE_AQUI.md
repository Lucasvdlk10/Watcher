# L.E.I.A. Watcher · V3 Dark Program

## UPDATE REAL, não demonstração

Este pacote contém **o código-fonte funcional do LEIA Watcher V2 modificado**, wheel instalado sobre a versão 2.0.0, identidade oficial LEIA incorporada à GUI nativa, script de atualização por usuário, backup transacional, rollback para **2.0.0**, testes reais e documentos de handoff.

### Como aplicar no Windows 11

1. **Deixe o LEIA Watcher V2 funcionando normalmente antes do upgrade** e encerre apenas a janela da interface. Não remova o programa atual.
2. Extraia o ZIP em uma pasta estável, **fora de Downloads** (pois Downloads está em modo de organização).
3. Execute `LEIA_WATCHER_V3_UPDATE\scripts\INSTALAR_UPDATE_VISUAL.cmd` por duplo clique. Não requer permissões de administrador.
4. O instalador detectará V2, verificará o pacote, verificará compatibilidade, parará o core via IPC (se ativo), criará backup consistente, instalará wheel V3 offline, fará health check, recriará atalho da GUI e reiniciará o core se antes estava ativo.
5. Execute `scripts\INICIAR_GUI.cmd` para abrir a interface. `Ctrl+K` abre navegação rápida; `Ctrl+1` a `Ctrl+6` abre módulos; `F5` atualiza dados.
6. Confirme banco `OK`, modo `WATCHING`, `no_llm=true` via `leia-watcher ping`, operações pendentes `0`, e Downloads ainda ORGANIZE não recursivo. Não é preciso reinserir pastas nem regras.

**Rollback:** `scripts\ROLLBACK_UPDATE_VISUAL.cmd` restaura o **código V2.0.0** mantendo estado atual do SQLite, configuração, histórico, Downloads e secrets por padrão. Há opção técnica `rollback.ps1 -RestoreSnapshot`, com confirmação distinta, somente quando se desejar reverter os dados ao instante anterior ao update (pode descartar eventos posteriores).

### O que NÃO fazemos

Não há nova instância genérica HTML, dados fictícios, servidor web da GUI, banco novo, download em instalação, agente LLM, edição de Hermes, reorganização da árvore de Downloads ou reescrita de regras. A UI consulta o **core real** pelo IPC autenticado.

### Limitações verificáveis

- Wheel V3 e scripts Windows inclusos. Não há executável `.exe` independente; a instalação V2 já existente fornece Python x64 e `.venv`.
- Os 117 testes Python e o smoke com **core real** / GUI Linux Xvfb passaram. O instalador PowerShell, NTFS, alta DPI, foco/oclusão Windows e hotkeys Windows **ainda exigem homologação nesta máquina**.
- O shell visual permanece em Tk Canvas customizado, não PySide6/QML; blur translucente do compositor Windows não está presente. Esta é uma evolução integrada de baixo risco sobre o V2, não implementação literal de Qt Quick.

Leia `docs/V3/HANDOFF_PARA_LEIA.md` e `docs/V3/QA_E_LIMITACOES.md` antes de promover a produção.
