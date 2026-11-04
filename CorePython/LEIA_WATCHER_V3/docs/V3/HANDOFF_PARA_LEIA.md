# Handoff de implantação · LEIA Watcher V3

**Objeto:** upgrade in-place da versão 2.0.0 para 3.0.0 na máquina Windows, preservando Downloads ORGANIZE **direto na raiz**, não recursivo, conflitos `RENAME`, sem overwrite, `no_llm=true`, SQLite intacto, operações pendentes 0 no momento de referência.

## Comandos e gates para a LEIA

1. Extraia pacote **fora de Downloads**, confira `SHA256_MANIFEST.txt` via `scripts/CHECAR_INTEGRIDADE.cmd`. Se hash falhar: `BLOCKED` sem tentar aplicar.
2. Consulte status atual usando o Python do venv `%LOCALAPPDATA%\Programs\LEIAWatcher\.venv\Scripts\python.exe -m leia_watcher.cli ping` e confirme **versão 2.0.0**, db `ok`, `no_llm=true`.
3. Consulte raízes e pendências via IPC/CLI real; verifique Downloads `mode=ORGANIZE`, `recursive=false`, `conflict_policy=RENAME`, `allow_overwrite=false`, sem raiz/saída extra; registre snapshot do estado sem expor tokens.
4. Feche a GUI (não exclua arquivos). **Somente se configuração estiver íntegra**, execute `scripts/INSTALAR_UPDATE_VISUAL.cmd` como usuário normal. Instalação interrompe core com IPC autenticado e reinicia conforme estado anterior.
5. Execute `scripts/INICIAR_GUI.cmd`; inspecione Visão geral, Pastas, Regras, Arquivos, Histórico, Hermes. Compare banco/config e `no_llm=true` antes/depois.
6. Valide UI com o core efetivamente executando, sem dados fictícios: Ctrl+K, Ctrl+1..6, F5, modo reduzido/off, perdas de foco/minimização, DPI e navegação de teclado. Teste simulação dry-run, sem ativação/movimentação desnecessária.
7. Se qualquer gate operacional falhar, execute `scripts/ROLLBACK_UPDATE_VISUAL.cmd` para **voltar ao código 2.0.0 sem reverter DB/config**. Não usar `-RestoreSnapshot` sem necessidade e autorização explícita, pois descartaria eventos posteriores ao upgrade.
8. Registre versão, hashes, status core, db, contagem raízes, pendências, saúde Hermes e screenshot sem informações privadas em `VALIDACAO_WINDOWS_LOCAL.md`. Atualize para `DONE` apenas se todos os gates passarem.

## Estados

- `DONE`: V3 atualizado e health/UI/caminhos verificados na máquina.
- `BLOCKED`: config ou versão diferente, UI ativa, impossibilidade de parar core, dependência Python ausente, hashes divergentes ou problema de integridade.
- `FAILED`: instalação/health interrompidos; rollback automático ou manual executado e V2 retestada.

## Pontos que não devem ser alterados

Nenhum novo projeto Supabase, token, server, Hermes write API, app HTML substituto, serviço extra, diretório de saída em Downloads, pasta obrigatória `_LEIA_Organizado` quando não consta da config atual, regra recursiva modificada ou modelo de IA.

## Resultado de testes conhecido deste ZIP

117 testes Python passaram em Linux e GUI abriu com core V3 real por IPC em sandbox. Wheel V3 foi construído e seus assets inspecionados. **Instalação PowerShell, DPI/NTFS e rollback efetivo no Windows ainda não foram executados aqui.**
