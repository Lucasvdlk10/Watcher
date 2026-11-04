# SDD · LEIA Watcher V3 Dark Program

## Arquitetura real

```text
Startup do usuário → pythonw -m leia_watcher.main [core V3]
                          │
                          ├─ Watcher engine / rules (imutados da V2)
                          ├─ SQLite WAL + journal / undo / backups (imutados)
                          ├─ Hermes REST/WebSocket Bearer + loopback / readonly (imutados)
                          └─ Admin.Listener AF_PIPE [Windows], auth admin.secret
                                     ↑  request('ui_snapshot'/'roots'/'ui_list'/admin actions)
Menu Start → pythonw -m leia_watcher.ui ──┘
             Tk shell, icons PNG oficiais, WaveHero, ui_kit, ui_prefs
```

**Pontos de alteração:** `ui.py`, `ui_kit.py`, `assets/*`, `__init__.py`, `admin.py` (string `ping.version`), `pyproject.toml`. Demais módulos do core V2 são preservados integralmente. A GUI segue cliente do IPC, não acessa SQLite diretamente e não substitui o core por dados de demonstração.

## Estado e comandos

`GET/WS` Hermes não foram alterados. Comandos V2 via IPC incluem `ping`, `status`, `ui_snapshot`, `ui_list`, `roots`, `preview`, `activate`, `scan`, `pause`, `resume`, `backup`, `export`, `undo` e CRUD administrativo protegido. `ui_snapshot` mantém `no_llm=true`, `hermes_read_only=true`, `api_host=127.0.0.1`. `ui_list` mantém consultas parametrizadas, filtros whitelist e paginação limitada.

## Fluxo instalador

1. Verifica wheel original 2.0.0, wheel V3, SHA256, paths `.venv`, schema config/SQLite, versão instalada.
2. Exige que a GUI esteja fechada (falha em segurança caso não detecte processos).
3. Para core via IPC se ativo; recusa troca caso parada não confirmada.
4. Executa SQLite online backup sob motor parado, lê WAL, preserva config e não copia secrets para snapshot.
5. Reinstala wheel V3 via pip offline sem dependências e verifica versão/recursos/config/SQLite.
6. Reinicia core se antes estava ativo e valida resposta de IPC; atualiza atalho GUI do Menu Iniciar.
7. Se falha após pip, tenta reinstalar wheel V2 automaticamente e reinicia core original.

`migrations/v2_to_v3.py` **somente inspeciona** `config.schema_version==1`, tabelas essenciais e `PRAGMA integrity_check`; nenhuma DDL/DML ou migração de caminhos.

## Reversão

`rollback.ps1` fornece rollback de código V3→V2 com confirmação `RESTAURAR`. Banco/config atuais preservados; `-RestoreSnapshot` requer `RESTAURAR-DADOS` e só deve ser usado quando é intencional regressar ao snapshot do upgrade. Tokens nunca entram no ZIP nem no backup. Arquivos organizados continuam onde estão (o rollback de software não reverte movimentações), e o undo V2 permanece funcional quando elegível.

## UI e render

Tk 8.6 `Frame/Canvas` (stdlib Python já presente no V2), ícones oficiais PNG locais, superfícies grafite e ações majoritariamente neutras, estado textual e cores semânticas discretas; Ctrl+K abre `Toplevel` sem enviar mutações; atalhos Ctrl+1..6/F5; `WaveHero` faz ticks apenas sob foco/mapeamento, com modos auto/reduzido/off e detecção de bateria. PNG hero e paleta são locais no wheel, sem download.

## Segurança e compatibilidade

Nenhuma nova dependência; nenhum socket HTTP de escrita; nenhuma mudança na tabela SQLite e no contrato `config.json`; nenhum token no wheel. `ACTIVATE` e `OVERWRITE` mantêm gates originais. Processo GUI e processo core continuam separados. A homologação final Windows é requisito externo, não substituída pelos testes Linux.
