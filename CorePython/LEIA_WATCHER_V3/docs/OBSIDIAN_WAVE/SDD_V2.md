# SDD · L.E.I.A. Watcher Obsidian Wave 2.0

**Base arquitetural:** Watcher 1.0.0 fornecido. **Estilo:** upgrade UI + extensão de consultas IPC; core preservado. **Versão de pacote:** 2.0.0.

## 1. Contexto e fronteiras

```text
┌──────────────────────────── DESKTOP / USER SESSION ────────────────────────────┐
│  ui.py App / RuleEditor                                                        │
│      │   ui_kit Canvas, widgets nativos, WaveHero, design tokens               │
│      ├─ ui_rules: transformação pura (sem E/S)                                 │
│      ├─ ui_prefs: ui_prefs.json (somente aparência)                             │
│      └─ admin.request() ── AF_PIPE authenticated ───────────────────────┐      │
│                                                                      │      │
│  CORE subprocess (leia_watcher.main)                                 │      │
│    Admin.dispatch() ←────────────────────────────────────────────────┘      │
│       ├─ status/roots/preview/scan/update_root/undo/etc. (v1)                │
│       └─ ui_snapshot/ui_list (v2, somente leitura) ─┐                        │
│    Watcher (engine) ←────────── rule evaluation      │                        │
│    SQLite WAL ledger + journal + audit ◄────────────┘                        │
│    API HTTP/WebSocket ─── 127.0.0.1:8766 ─── Bearer de leitura para Hermes    │
└──────────────────────────────────────────────────────────────────────────────┘
```

A GUI **não** abre o SQLite, não instala hooks no motor, não faz PUT/POST HTTP, não lê bytes de documentos nem expõe segredos. O núcleo pode continuar operando com a GUI fechada. Todo IPC v1 permanece aceito, inclusive por CLI e integrações existentes.

## 2. Módulos e arquivos

- `ui.py`: shell desktop, navegação, busca, cards, modais, editor visual, animação controlada e execução assíncrona IPC.
- `ui_kit.py`: tokens, rounded pills, inputs, modal, superfície, scroll, textos e divisórias. Arredondamento sem splines que extrapolam bounds.
- `ui_rules.py`: `apply_rows`, `rule_values`, `split_csv`; não tem I/O e reusa `rules.validate_rules`.
- `ui_queries.py`: `ui_snapshot` / `ui_list` autenticados; SQL com tabelas/colunas fixas, parâmetros vinculados, filtros whitelist, paginação <=100 registros e limite explícito de página.
- `ui_prefs.py`: leitura/gravação atômica de preferência visual independente da configuração core.
- `assets/obsidian_wave.png`: raster original de fundo, junto ao wheel, sem fonte remota.
- `admin.py`: adiciona somente dois branches opcionais à API IPC existente. Nenhuma mudança no endpoint de rede.
- `scripts/install.ps1` e `upgrade_helper.py`: instalação offline, snapshot transacional e validação.
- `scripts/rollback.ps1`: restauração segura de baseline da fonte v1 incluída.

## 3. IPC e contratos V2

### `ui_snapshot` (consulta)

Payload: `{ "command": "ui_snapshot", "args": {} }`. Response: `{ "roots": [ {root_id,name,canonical_path,mode,health,enabled,last_scan_finished_at} ], "files_count": int, "pending": int, "paused": [id], "database": "ok|...", "recent": [...], "undo_eligible": int, "no_llm": true, "hermes_read_only": true, "api_host": "127.0.0.1" }`. É emitido somente via `multiprocessing.connection.Client` com autenticação derivada de `admin.secret` já existente; nunca na API Hermes.

### `ui_list` (consulta paginada)

Payload:

```json
{
  "command": "ui_list",
  "args": {
    "entity": "files",
    "filters": {"q": "contrato", "root_id": "root-downloads", "extension": ".pdf"},
    "page": 0,
    "limit": 40
  }
}
```

Entidades permitidas `files`, `audit`, `operations`. `files`: busca por `filename`/`relative_path`, filtros `root_id`, `extension`, `status`. `audit`: busca por ação/código, filtros `root_id`, `action`, `outcome`. `operations`: busca por source/destination/type, filtros `root_id`, `stage`. O servidor valida tipos, tamanho de `q` (240), limite (1..100), página inteira (0..100000), nome da entidade e whitelist de filtros. Busca `%/_/\` usa escaping de SQL LIKE, evitando wildcard involuntário. Resposta `{items,total,page,limit,has_more}` sem blob de documento e sem secrets. Nenhuma mutação SQL nos comandos `ui_*`.

### Compatibilidade

- IPC v1 (`status`,`roots`,`files`,`audit`,`operations`,`preview`,`update_root` etc.) mantido como antes.
- API Hermes só `GET`/WebSocket, loopback e Bearer no header; nenhuma nova rota.
- Config `schema_version=1`, `ruleset.version` e `schema.sql` preservados; não há migração DB.
- Pacote Python v2.0.0; `Admin.ping` informa 2.0.0; utilitários CLI continuam com mesma sintaxe.

## 4. UI lifecycle e isolamento

`App` inicia sem ações administrativas; a única operação automática é leitura (`ui_snapshot`, `roots`). Se o serviço estiver desconectado, a UI exibe diagnóstico e botão explícito de ligar core. `App._run` cria worker thread por operação; os workers NUNCA fazem chamadas Tk, apenas gravam resultados na `queue.Queue`. `App._messages` consome eventos na thread do mainloop. Intervalo de atualização ~9 segundos enquanto a janela estiver normal; consultas e ações são chamadas autenticadas, com timeout no IPC já existente.

Navegação lateral monta um único corpo de página; ao sair, widgets são destruídos e timers do hero cancelados. O widget `WaveHero` remove seus bindings de eventos da janela root no `Destroy`. Assim visitar a Visão geral repetidamente não acumula callbacks de foco nem timers ambientais.

## 5. Máquina de estados de movimento

```text
CREATED → VISIBLE_AND_FOCUSED ───→ TICK (fps limitado)
                      │                 │
                      ├─ FocusOut/Unmap └─ scheduled update
                      ▼
                    PAUSED (after_cancel)
                      │
                      ├─ Map/FocusIn → verificação focada 140ms → RESUME
                      └─ Destroy → CANCEL + UNBIND → TERMINATED
```

A verificação de foco usa `state=='normal'`, `winfo_viewable()` e `focus_displayof()`; não anima quando minimizada ou sem ativação. Preferências `auto` (até ~30 fps), `reduced` (~11 fps), `off` (timer desligado), saved atomic em `ui_prefs.json`. Redução em bateria via `GetSystemPowerStatus` (~14 fps) para modo auto. Windows `SPI_GETCLIENTAREAANIMATION` orienta preferência inicial em reduced motion. Oclusão total com foco mantido não é detectada por DWM nesta versão, e a documentação registra esse desvio.

## 6. Alteração de regras em modo ORGANIZE

`RuleEditor` monta uma cópia profunda da root existente e carrega suas regras sem tocar no core. Cada regra é editável visualmente: ID fixo, tipo, alvo, opções e enable. Etapas são validadas por `rules.validate_rules`. Campos globais: nome, path saída, modo, recursão, exclusões, colisões RENAME/SKIP, fallback. `OVERWRITE` não é ativável na interface visual.

No Save: `_payload` preserva chaves desconhecidas, garante que root.id não muda, chama `config.validate`, e caso a root anterior estivesse ORGANIZE/ativa e qualquer política de risco tenha sido modificada, define `enabled=false`. Alteração para ORGANIZE também força revisão. Admin v1 gerencia backup/atomic write e incrementa `ruleset.version` após alterações. Ativar em ORGANIZE requer confirmação `ORGANIZAR` visível + token `'I_CONFIRM_FILE_MOVES'` enviado ao core.

**Observação de risco:** a edição JSON avançada admite configuração de política existente, mas mudanças em ORGANIZE ativa também exigem reativação explícita. `OVERWRITE` permanece desabilitado no fluxo visual.

## 7. Dados, recuperação e upgrades

Dados existentes: `%LOCALAPPDATA%\LEIA\Watcher` (`config.json`, SQLite `data/watcher.db`, WAL, `admin.secret`, `hermes_read.token`, backups). Binários: `%LOCALAPPDATA%\Programs\LEIAWatcher\.venv`. Upgrade por script executado como usuário:

1. localizar venv Python 3.11–3.13 existente ou criar com `py.exe` x64;
2. ping core; se conectado solicitar `stop`; aguardar sumir IPC, abortar caso permaneça;
3. criar `<data>\upgrade-backups\timestamp\`; snapshot de config, SQLite através de `sqlite3.Connection.backup()` (inclui páginas WAL), `manifest.json`, wheel 1.0.0;
4. `pip install --no-index --no-deps --force-reinstall` do novo wheel, verificar health DB, assets embarcados e segredos existentes;
5. criar atalho GUI no menu Iniciar, sem alterar o shortcut do core já existente;
6. se core estava ativo, tentar reiniciá-lo; deixar aviso de falha sem apagar backup;
7. gravar `latest.txt` para rollback.

Rollback: confirmado pelo usuário, parar core, instalar wheel v1 baseline do snapshot, restaurar SQLite verificado e config, sem sobrescrever tokens, e religar core se antes ativo. O script Python suporta testes em Linux, mas o fluxo Windows completo não foi executado nesta máquina de desenvolvimento.

## 8. Segurança e modelo de ameaças

A superfície de rede permanece inalterada: somente API loopback autenticada readonly. O UI expõe textos de caminhos somente a usuário local, conforme permissões existentes, jamais conteúdo de documento. Não há scripts no browser, bibliotecas externas de rede, downloads automáticos, analytics, recursão sobre diretórios proibidos ou segredos no log de UI. A exportação exige consentimento específico e oferece CSV/JSON para operação local.

### Respostas a falhas

- IPC off: UI informa falta de conexão e ação explícita.
- CLI/IPC comando falhou: rodapé persistente e não declara sucesso.
- Regra inválida: validação mostra detalhe e impede envio.
- SQLite inválido no upgrade: fail-stop sem instalar wheel; rollback preservado.
- Animação inativa/minimizada: timers cancelados e gráficos não concorrem com scan do core.
- Regra altera enabled sem confirmação: `RuleEditor` força desativar ORGANIZE e UI exige ativação textual.

## 9. Estratégia de testes

`pytest`: testes originais + unit tests `ui_queries`, `ui_rules`, `ui_prefs`, backup/restore, proteção de root/config. Smoke Linux: core isolado + UI `Tk()` sob Xvfb + navegação por seis telas + abertura de editor sem alterações + encerramento core. Teste de wheel isolado: pip install do wheel offline, `importlib.resources`, CLI `ping`, `status`. Testes nativos ainda requeridos: upgrade em instalação real Windows, ACLs, DPI 100–200%, 50 minimizações, 100 alternâncias de foco, Windows reduced motion, bateria e suspensão, repositório de ícones e uso de Narrator.

## 10. Limitações e débito técnico

É uma implementação Canvas customizada, não PySide6/QML; sem blur/gpu compositor real, sem ícone de bandeja, sem binário .exe autônomo, sem testes Windows executados aqui. Não confundir sucesso de testes Linux com certificação Windows. Migração futura para QML deve reusar IPC, models puros e suite de regressão, nunca reescrever core em conjunto.
