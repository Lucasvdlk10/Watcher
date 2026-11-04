# Validação executada / pendências (21-10-2026)

## O que foi efetivamente executado

- Regressão da baseline: 63 testes Python originais, sem alterações no motor.
- Testes adicionados para filtros paginados, consultas read-only, escaping de SQL LIKE, limites e validação whitelist de entidades e filtros.
- Testes do editor visual de regras (incluindo IDs legados, campos extras, categorias, sizes, datas, duplicidade e rejeição de nomes inseguros).
- Testes de preferências de movimento separadas de `config.json`, sem instalação de modelos.
- Testes de snapshot/rollback do SQLite WAL em arquivo temporário, JSON de configuração e manutenção de `admin.secret` no lugar.
- Integração gráfica sob **Linux + Python 3.13 + Xvfb + Tk 8.6**: core real em pasta temporária, raiz TRACK_ONLY, GUI aberta, seis telas navegadas, editor aberto, payload validado, fechamento da UI e core sem mover o arquivo monitorado.
- Correções induzidas por testes gráficos: pílulas Canvas sem extrapolação de spline e assinatura do handler de eventos de foco.

## Verificações pendentes

- Upgrade PowerShell e rollback com uma instalação real Windows 10/11: escritos, porém **não executados neste ambiente Linux**.
- Homologação de DPI 100/125/150/200%, comportamento do Windows Narrator, permissões ACL e UI em múltiplos monitores.
- Stress test de 50 minimizações, 100 alternâncias de foco e medição de RAM/CPU/GPU em condições reais.
- Políticas de bateria/suspensão, oclusão completa com foco mantido, driver de composição DWM.
- Tests Windows de NTFS, handles e watchdog WinAPI, além de rollout com banco de produção do usuário.
- O visual usa superfícies sólidas e não implementa composição alpha-blur real nem PySide6/QML.
- Ainda depende de Python x64 já instalado; não distribui `.exe` standalone.

## Interpretação

Uma suíte Python verde e uma janela que abre sob Xvfb **não são homologação de produção Windows**. Não foram utilizados documentos privados ou banco real do usuário. Compatibilidade com a configuração de Downloads foi avaliada estruturalmente, sem tentar resolver o caminho Windows em Linux (isso seria enganoso). Antes de migrar arquivos importantes, execute o guia Windows e faça backup independente.
