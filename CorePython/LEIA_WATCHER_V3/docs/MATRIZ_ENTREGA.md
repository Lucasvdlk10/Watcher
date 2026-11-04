# LEIA Watcher — Matriz de implantação do PRD

## Contrato principal (P0)
| IDs | Situação em código | Observações |
|---|---|---|
| RF-001 a RF-004 | Implementado | Limite 128 raízes; `TRACK_ONLY` sem mutações; full scan, recursão e exclusão de symlink |
| RF-005 a RF-011 | Implementado | Regras determinísticas, 5 faixas, origem comprovada/UNKNOWN, prioridade e exclusões |
| RF-012 a RF-016 | Implementado com homologação pendente | Estabilização por três leituras, API Win32 handles, watchdog nativo via ReadDirectoryChangesW + reconciliação; Windows precisa de testes reais |
| RF-017 a RF-023 | Implementado com homologação pendente | Inventário SQLite, journal, rename no-replace, backup e undo; crashes de overwrite precisam de teste real |
| RF-024 | Implementado, não homologado | Tk/ttk funcional, Windows GUI ainda não testada no alvo |
| RF-025 a RF-029 | Implementado | REST/WS readonly, segredo no perfil e acesso a paths autorizados; segurança de ACE Windows não auditada |
| RF-030 a RF-034 | Implementado | Rejeição de sobreposição ativa, exclusão de output, preview, pausa, sem looping do próprio move |

## Objetivos complementares (P1)
| IDs | Estado | Pendências |
|---|---|---|
| RF-035 a RF-041 | Implementação funcional | Benchmarks com 100 mil arquivos e rollback versionado Windows pendentes |
| RF-042 a RF-043 | Parcial | Long paths Unicode não homologados no Windows; retenção dos fs_events configurável em dias |
| RF-044 | Parcial | Notificações pela interface/histórico; **tray nativo não implementado** |
| RF-045 a RF-048 | Implementado | Exclusões sensíveis, UNKNOWN, idempotência, versionamento por alteração de política |

## Critério final
**Release de engenharia instalável, não homologação integral de produção.** Os testes Linux e o teste do wheel isolado foram executados. Não declarar 100% de P0/P1 até concluir a bateria WinAPI/NTFS e os itens parciais acima. O instalador offline depende de Python x64 pré-instalado e distribui wheel, não `.exe` standalone.
