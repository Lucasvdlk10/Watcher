# Estado de engenharia e homologação

## Funcionalidades implementadas
- Banco SQLite WAL, integridade, backup Online Backup API, versões de regras, inventário e operações journaled.
- Rastreamento somente leitura, organização ativa com confirmação, pausa, full scan, snapshots e reconciliação.
- Motor determinístico de regras, exclusões, origem não inventada, faixas de tamanho e simulação sem escrita em arquivos.
- Deduplicação por id do arquivo e path; Windows usa `ReadDirectoryChangesW` e fila bounded de eventos; resto usa polling.
- Mover no mesmo dispositivo, rename no-replace, colisão RENAME/SKIP ou OVERWRITE opt-in com backup.
- Reverter o último movimento seguro; bloquear retorno se destino editado/colidido.
- API REST + WS no loopback readonly; token hash SHA256 armazenado na base e segredo no perfil do usuário; canal admin AF_PIPE/AF_UNIX com authkey.
- GUI padrão Tk/ttk, CLI, instalador offline, scripts de logon opcionais e desinstalador sem remoção de dados.

## Itens não homologados / lacunas da release
- Não foi possível produzir executável Windows nativo, assinado, sem Python instalado. Distribuição atual é wheel e instalador offline usando Python pré-existente.
- O WinAPI ReadDirectoryChangesW, locks reais NTFS, symlinks/junctions, placeholders OneDrive, DPI/tray e startup automático não puderam ser testados no Windows neste ambiente. O tray nativo ainda não está implementado (a GUI funciona em janela). Não afirmar conformidade total dos P0/P1 antes da homologação.
- O indicador de fila da GUI lista operações pendentes; o histórico de jobs mostra scan por IPC. Não existe barra de progresso granular de 100 mil arquivos.
- A estabilidade usa 3 observações de stat e tentativa de handle exclusivo; trata-se de heurística, não prova absoluta de fim de escrita. Rotinas de alto volume podem ser lentas; não houve medição de p95 / RSS alvo.
- Rótulo `UNKNOWN` para origem sem evidência é esperado; não existe classificador semântico nem integração externa de origem. Zone.Identifier indica zona Internet, não o aplicativo originador.
- `OVERWRITE` tem risco residual de crash/junction races e é intencionalmente **desativado** em qualquer nova raiz. Faça cópia externa antes de habilitar.
- Não há filtragem formal de cada ACE Windows para as bases/backups; diretórios LocalAppData herdam ACLs do perfil, secrets tentam restringir icacls. Auditoria ACL deve ser feita no alvo.
- O observer Windows sinaliza eventos e rescan; interrupções podem perder a ordem exata de eventos externos, mas reconciliam estado final. `fs_events` é best effort.

## Homologação exigida no Windows (não executada aqui)
1. Instalar por usuário em Windows 10/11 64-bit com Python 3.12, sem admin e sem alterar Hermes.
2. Verificar somente bind 127.0.0.1 e token inválido em REST/WS.
3. Rastrear projeto real (TRACK_ONLY) e conferir ausência de alterações, renomes, exclusões e reconciliação.
4. Criar arquivos `.crdownload`, arquivos abertos no Word, arquivos grandes, NTFS junctions, OneDrive placeholders.
5. Simular regras, validar resultado; ativar ORGANIZE somente em pasta de teste com backup externo.
6. Forçar colisões RENAME/SKIP/OVERWRITE com backup e desfazer, inclusive após edição de destino.
7. Interromper processo após PREPARED e após rename; verificar recuperação `MOVED` ou `NEEDS_ATTENTION` e bytes intactos.
8. Repetir testes com 100k arquivos e medir p95 da API e RAM do processo; simular overflow e revogação do token.
9. Validar autostart opt-in, encerramento seguro, backup/restauração de SQLite e desinstalação sem perda de dados.

## Resultado de testes reproduzível
Veja `TEST_RESULTS.json` no topo do pacote. A suíte é incluída em `tests/`, e roda localmente via `pytest`. Esse resultado **não** certifica o funcionamento em instalações Windows específicas.
