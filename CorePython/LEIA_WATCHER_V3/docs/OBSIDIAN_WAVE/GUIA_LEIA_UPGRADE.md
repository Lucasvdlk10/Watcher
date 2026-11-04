# Guia operacional para L.E.I.A. instalar/testar — Windows 10/11

## 1. Pré-voo

- Descompacte o ZIP inteiro; execute `scripts\CHECAR_INTEGRIDADE.cmd` para validar SHA256.
- Confirme que o usuário logado possui permissão nos diretórios `%LOCALAPPDATA%\Programs\LEIAWatcher\.venv` e `%LOCALAPPDATA%\LEIA\Watcher`.
- Confirme Python x64 3.11–3.13; se v1 existente, reusa venv da v1; **não requer Qt/PySide6**.
- Realize uma cópia independente do diretório de dados antes de validar a versão sobre dados críticos.
- Verifique se há movimentações em andamento. O instalador pedirá encerramento gracioso do core, não kill forçado.

## 2. Instalar

Dê duplo clique em `scripts\INSTALAR_UPDATE_VISUAL.cmd`. O PowerShell detecta o core, pede parada por IPC existente, realiza snapshot consistente e instala wheel offline, checa integridade e religa core se necessário. A mudança visual **não** altera a configuração de roots nem as tabelas SQLite. Se não for possível parar o core, a instalação aborta e deixa a versão anterior intacta.

## 3. Conferir

- `scripts\INICIAR_GUI.cmd` abre a interface; `scripts\INICIAR_CORE.cmd` pode iniciar core em console para diagnóstico.
- Verificar nomes, roots, ruleset original e ID exatamente iguais aos da baseline.
- Verificar que o modo TRACK_ONLY não movimenta nenhum arquivo; simular organização sem mover.
- Em ORGANIZE ativa, editar uma regra e salvar: raiz deve ficar desativada antes da próxima movimentação. Confirmar ativação apenas depois da simulação.
- Confirmar `ui_snapshot` e `ui_list` através da GUI, incluindo filtros, paginação e atualização do histórico.
- Conferir Hermes `GET /v1/health`, read-only, Bearer, sem tokens mostrados na interface.
- Comparar `PRAGMA integrity_check`, totais e IDs do SQLite pré/pós-instalação.
- Testar backup explícito e undo apenas com amostra controlada e backup independente.

## 4. Matriz de homologação em Windows real — obrigatória antes de promover

| Cenário | Passos | Passa quando |
|---|---|---|
| DPI | 100/125/150/200% | texto legível, sem clipping, focus ring visível |
| Resolução | 1366x768 e 1920x1080 | primeira tela compreensível, botões alcançáveis |
| Multi-monitor | mover entre dois monitores | foco, menus e escala consistentes |
| Minimização | 50 ciclos | timers param, sem aumento contínuo de RAM |
| Foco | 100 alternâncias | onda pausa e retoma, sem callbacks acumulados |
| Oclusão | sobrepor outras janelas | fora de foco sem animação; oclusão DWM exata **pendente** |
| Bateria | notebook ligado/desligado da tomada | menor FPS em bateria |
| Reduced motion | opção Windows e interna | animações reduzidas ou canceladas |
| Core + GUI | fechar GUI no meio da varredura | core segue operando, sem duplicação |
| ORGANIZE | mudança de regras ativa | root desativada e exige confirmação antes de reativar |
| Rollback | `ROLLBACK_UPDATE_VISUAL.cmd` | volta ao v1 com config e DB do snapshot, tokens preservados |
| Suspensão | suspender/retomar Windows | reconciliação e IPC retornam sem corrupção |
| Segurança | token errado, métodos HTTP de escrita | retornos bloqueados; nenhum log de segredo |
| Localidade | paths com acentos e >240 caracteres | comportamento seguro e explícito, sem exceções silenciosas |

## 5. Rollback

Execute `scripts\ROLLBACK_UPDATE_VISUAL.cmd` e digite `RESTAURAR`. O script para core antes da restauração, reinstala wheel 1.0.0 fornecido no ZIP e volta config/SQLite ao snapshot. Não copia nem revela segredos. Atenção: alterações feitas entre instalação 2.0 e rollback não estarão no snapshot original — faça uma cópia atualizada dos dados antes de reverter se precisar preservá-las.

## 6. Critérios de bloqueio

NÃO promover se core não consegue parar, sqlite.integrity_check falha, alguma configuração/raiz sumiu, tokens foram alterados sem autorização, TRACK_ONLY moveu, modo ORGANIZE foi ativado silenciosamente, HTTP permitiu escrita ou não for possível restaurar o snapshot.
