# Mapa de telas e jornadas

## Tela 1 · Visão geral

Estado conectado/desconectado, hero original com animação controlada, 4 indicadores: pastas, arquivos, operações pendentes, integridade SQLite. Feed de seis eventos, ações rápidas (abrir Pastas, simular, backup, Hermes, undo quando elegível), seletor ambiental Suave/Reduzido/Desligado. Atualiza via `ui_snapshot` somente leitura.

## Tela 2 · Pastas

Cada pasta: nome, localização, modo, saúde, última varredura, enabled e ações Editar/Simular/Varrer/Pausar/Retomar/Ativar/Remover. Adicionar mostra modal de nome, path escolhido localmente, mode TRACK_ONLY default. ORGANIZE cadastra desativada no core. Ativar organização exige digitar `ORGANIZAR`.

## Tela 3 · Regras

Cards por root mostram ordem de etapas, contagem de regras e exclusões, link para editor visual. Editor: nome da pasta, output path, modo, colisão, recursão, enabled; seleção de etapas, fallback, conjunto de regras por tipo, campos-alvo e valores vírgula-separados, reordenar/remover/adicionar, exclusões por linha, editor JSON avançado secundário. Validação por motor determinístico antes de enviar IPC.

## Tela 4 · Arquivos

Busca por nome/caminho, paginação (40 por página), filtros de pasta, extensão e status. Linha contém nome, raiz, extensão, tamanho e estado. Clique em linha abre metadados textuais copiáveis; não abre o documento. Exportação CSV confirmada.

## Tela 5 · Histórico / Movimentações

Alternância auditoria/operações, busca, root, resultado/etapa, páginas, dados completos sob clique. Exportação explícita. Undo aparece quando há operação potencialmente elegível e ainda exige confirmação textual `DESFAZER` e validação de integridade no core.

## Tela 6 · Integração Hermes

Vínculo 127.0.0.1:8766, permissão GET/WS somente leitura, garantia de ausência de chamadas de IA, exemplo curl copiado com marcador `<TOKEN_LOCAL>`; não renderiza conteúdo de token. Caminho do segredo só exibido após confirmação.

## Fluxos transversais

- **Core ausente:** a UI abre passiva; CTA iniciar serviço informa que monitoramentos já habilitados poderão operar.
- **Erro IPC:** mostra falha persistente sem repetir mutações automaticamente.
- **Alterar pasta ORGANIZE em funcionamento:** mudanças de risco desativam automaticamente a root no payload antes da gravação; simular e reativar manualmente.
- **Fechar GUI:** não encerra o core nem altera estado de pastas.
- **Preferências ambientais:** persistem fora de config.json principal; desligar movimento não interfere com o worker.

## Caminhos de teclado

Botões Canvas permitem foco e Enter/Espaço; navegação de sidebar pode ser acionada por teclado; campos aceitam seleção nativa e Ctrl+C; Escape fecha modais. Compatibilidade Narrator detalhada precisa de auditoria Windows real. Acessibilidade de menus nativos e escalas DPI é testável sem mudar os contratos de core.
