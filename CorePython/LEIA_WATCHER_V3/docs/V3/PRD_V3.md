# PRD · LEIA Watcher V3 Dark Program

**Baseline:** Watcher Obsidian Wave 2.0.0 entregue e usado no Windows. **Release alvo:** 3.0.0 por usuário, atualização in-place. **Escopo:** evolução visual e entrega instalável real, sem substituir motor/arquitetura.

## Objetivo de produto

A pessoa deve abrir o programa instalado, encontrar seis módulos operacionais na UI escura oficial LEIA, identificar o estado do core sem precisar inspecionar JSON e realizar as mesmas operações auditáveis da V2. Controles rotineiros usam tons neutros e ações de risco mantêm confirmação explícita.

## Requisitos de aceitação

| ID | Requisito | Como validar |
|---|---|---|
| V3-RF01 | Atualizar Watcher 2.0.0 instalado, sem demo paralela | wheel V3 no mesmo `.venv`, CLI `ping` versão 3.0.0 |
| V3-RF02 | Preservar 100% de regras, raízes, banco, histórico e secrets | comparativo config/backup, integrity check e smoke Windows |
| V3-RF03 | Downloads permanece ORGANIZE e não recursivo conforme configuração atual | leitura `roots` após upgrade e amostra sem movimento inesperado |
| V3-RF04 | Sidebar oficial LEIA com ícones locais e layout mono escuro | abrir GUI V3, referência visual Linux, high DPI Windows pendente |
| V3-RF05 | Dashboard com dados verdadeiros e sem chamada web | `ui_snapshot` autenticado; sem fixtures artificiais |
| V3-RF06 | Navegação acessível `Ctrl+K`, `Ctrl+1..6`, `F5` | smoke GUI e validação humana Windows |
| V3-RF07 | Pastas, regras, inventário, histórico e Hermes funcionais | seis telas e core real IPC |
| V3-RF08 | TRACK_ONLY jamais move arquivos | regressão do engine + smoke |
| V3-RF09 | ORGANIZE exige simulação/confirmação, OVERWRITE não muda | core sem mudanças + testes existentes |
| V3-RF10 | API Hermes permanece GET/WS read-only em 127.0.0.1 | inspecionar api.py/contrato e regressão |
| V3-RF11 | Instalação offline sem elevação | wheel puro, pip --no-index --no-deps; scripts usuário |
| V3-RF12 | Rollback V3→V2 com preservação de dados por padrão | script rollback + validação Windows pendente |
| V3-RF13 | Ausência de modelos, nuvem, analytics e telemetry | dependencies=[], core igual V2 |
| V3-RF14 | Zero migração de SQLite/config, apenas verificação | migration NOOP só de leitura |
| V3-RF15 | UI minimizada ou inativa não mantém animação | WaveHero foco, Map/Unmap, reduced/off; Windows pendente |

## Não escopo

Nenhum redesenho de motor de regras, recomposição de dados, mudança na localização de saída, modificação Hermes, migração Qt Quick (requer wheels Windows e homologação não disponíveis), blur compositor real ou empacotamento `.exe` do Python.

## Requisitos não funcionais

Compatibilidade Python 3.11–3.13 x64 dentro do venv preexistente, operação offline, tempo/consumo próximos ao V2, sem alterar fluxo de tratamento de arquivos, layout desktop mínimo 960x650 e strings pt-BR. Testes integrais Python + smoke real com IPC e revisão de instalação/rollback pelo operador Windows antes de promover release.
