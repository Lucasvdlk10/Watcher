# Qualidade e limitações verificadas — V3

| Gate | Resultado | Observações |
|---|---|---|
| Testes originais V2 107 | PASSOU | suíte mantida, sem alterações nas regras/motor |
| Testes extras V3 10 | PASSOU | assets, IPC real, migration NOOP, installer/rollback verificados estaticamente |
| Total Python | 117 PASSARAM | Linux + Python disponível no ambiente, `pytest -q` |
| GUI Tk e core real | PASSOU | sandbox `LEIA_WATCHER_HOME`, conexão autenticada, 6 telas, banco `ok`, `no_llm=true` |
| Downloads não recursivo TRACK_ONLY | PASSOU | teste isolado, sem mover/modificar arquivo de teste |
| Wheel V3 offline | PASSOU | gerado com `pip wheel --no-index --no-build-isolation --no-deps`; assets dentro do wheel |
| Rollback wheel V2 no pacote | PRESENTE | mesmo arquivo de release V2 |
| Script de upgrade/rollback Windows | IMPLEMENTADO, NÃO EXECUTADO | precisa homologação na máquina Windows |
| UI Windows DPI 100/125/150/200 | PENDENTE | ambiente é Linux Xvfb |
| PowerShell parser/execution Windows | PENDENTE | PowerShell ausente no ambiente |
| NTFS/WAL com dados reais e snapshot de upgrade | PENDENTE | em Linux testes SQLite/WAL em temp passaram |
| 50 minimizar/restaurar, 100 focos e bateria Windows | PENDENTE | código oferece foco/Unmap/reduced/off |

**Regra de honestidade:** wheel integrado e scripts entregues não significam homologação operacional no Windows. A LEIA deve validar antes de promover a atualização.

**Estratégia de segurança:** janela GUI precisa ser fechada antes da troca de wheel; o core é parado via IPC. Backup transacional SQLite/config é feito antes do `pip install`. Código anterior é reinstalado em erro posterior. Não há SQL de migração V3; configuração e dados continuam compatíveis com versão 2.0.0.
