# HANDOFF — LEIA Watcher V4 (para executor Windows)

## Portão de segurança

NÃO substituir V3 até o EXE WinUI e o instalador terem sido compilados, instalados e testados em Windows 11. A base `CorePython/LEIA_WATCHER_V3` é cópia da versão 3.0.0 do usuário, NÃO instalar novamente seu wheel.

## Pipeline de validação

1. Restaurar NuGet e compilar `LEIAWatcher.sln` em Windows x64 com .NET 10 e Windows App SDK 1.8.12; corrigir falhas efetivas de XAML antes de distribuir.
2. Executar 129 testes baseline + 10 testes Bridge; adicionar testes de ViewModel em .NET e UI automatizada.
3. Compilar Release x64 e executar com Python V3 real instalado.
4. Conferir dashboard com 9 atuais + 425 legados = 434 em perfil oficial **sem alterar banco**.
5. Testar `TRACK_ONLY`, organização tipo/data com confirmação e undo numa pasta descartável isolada (nunca usar Downloads real nos testes).
6. Testar 1280x720, 1366x768, 1440x900, 1920x1080, 2560x1440 e DPIs 100,125,150,175,200.
7. Medir tempo de inicialização, flicker, uso idle CPU, acessibilidade Narrator, focus, alto contraste e transições.
8. Gerar instalador x64 offline com `Installer/BUILD_WINDOWS_RELEASE.ps1`, conferir dependências e assinatura.
9. Antes de atualizar produção, guardar backup consistente SQLite e atalho V3. Instalar como usuário comum, conferir `no_llm=true`, port local, operations_pending=0.
10. Executar rollback em Windows, verificar restauração do atalho V3 **sem reverter dados**, restaurar V4 e testar novamente.
11. Assinar MSIX com certificado confiável, caso o canal MSIX seja necessário.

## Contratos IPC usados

`ensure_core`, `ping`, `ui_snapshot`, `ui_list`, `ui_files_origin`, `roots`, `add_root`, `pause`, `resume`, `preview`, `rules_validate`, `rules_apply`, `update_root`, `backup`, `export`.

Toda movimentação real é delegada ao motor Python por socket/pipe autenticado, nunca pelo WinUI.

## Gaps conhecidos

- Não há screenshots reais (nenhum executável Windows rodou aqui).
- Não há MSIX assinado ou instalador EXE pronto neste ZIP.
- Refinamentos de motion e alta acessibilidade ainda precisam de validação no Windows.
- Controle de alto contraste depende das preferências do sistema operacional; preferências de notificação/densidade e startup precisam do comportamento nativo correspondente.
- Sem compilação Windows não é possível afirmar que XAML e C# estejam livres de erros do toolchain Microsoft.

Leia `Reports/TEST_REPORT.md` e `Reports/WINDOWS_QA.md` antes de instalar.
