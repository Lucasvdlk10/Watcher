# LEIA Watcher 3.0 — Dark Program · atualização do programa funcional

**Produto instalável sobre LEIA Watcher 2.0.0**, sem demo independente e sem dados fictícios.

Instruções rápidas: [00_COMECE_AQUI.md](00_COMECE_AQUI.md).

### Estrutura

- `src/leia_watcher/`: core local, SQLite, API Hermes readonly, GUI nativa conectada ao IPC, editor de regras e assets oficiais.
- `dist/leia_watcher-3.0.0-py3-none-any.whl`: wheel offline **V3** gerado com o fonte acima.
- `rollback-bundle/leia_watcher-2.0.0-py3-none-any.whl`: wheel exato da baseline V2 fornecida.
- `scripts/install.ps1`, `scripts/rollback.ps1`: atualização por usuário, snapshot, health, fail-closed e rollback.
- `migrations/v2_to_v3.py`: migração intencionalmente sem alterações; detecta incompatibilidades V2 e aborta.
- `tests/`: suíte V2 preservada + testes específicos V3.
- `docs/V3/`: PRD, SDD, ADR, design system, instalação, handoff, relatório QA e matriz de alterações.
- `assets_original/`: documentação e ícones vetoriais fornecidos com a identidade LEIA.
- `spec/`: contrato completo PRD/SDD original, preservado.

### Contratos preservados

100% local, `no_llm=true`, SQLite WAL, movimentos determinísticos e auditáveis, TRACK_ONLY, organização direta nas pastas configuradas, undo, confirmação de ORGANIZE, IPC local autenticado, Hermes REST/WS somente leitura em loopback e dados persistentes do usuário no mesmo `%LOCALAPPDATA%\LEIA\Watcher`.

### Qualidade

- `python -m pytest -q` — 117 testes (Linux).
- `xvfb-run -a python scripts/smoke_v3_linux.py` — GUI nativa + core real isolado, seis telas, nenhum move.
- `scripts/CHECAR_INTEGRIDADE.cmd` — valida SHA-256 dos arquivos de entrega (Windows).
- Windows V2→V3 real e rollback não foram executados neste ambiente Linux, exigem etapa final de homologação.
