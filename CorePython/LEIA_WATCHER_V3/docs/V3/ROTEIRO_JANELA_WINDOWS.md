# Aceitação no Windows 10/11 x64

1. Abrir `INICIAR_GUI.cmd` e comparar logo, sidebar, cards e estados com a captura de Linux. Confirmar visual em 1366x768 e 1920x1080, DPI 100/125/150/200%.
2. Percorrer navegação por teclado com Tab/Shift+Tab, Ctrl+K, Ctrl+1..6, F5 e Enter. Checar foco visível nos controles.
3. Minimizar/restaurar 50x, alternar foco 100x, suspender/retomar notebook e medir CPU/GPU. Confirmar `WaveHero.job=None` inativo e ausência de crescimento constante de memória.
4. Revisar `ui_snapshot` no core real: banco `ok`, pendências esperadas, modo Downloads não recursivo, regras inalteradas.
5. Selecionar uma pasta de TESTE em TRACK_ONLY e checar que não move arquivos; simular ORGANIZE em pasta TESTE sem ativar raiz de Downloads como efeito colateral.
6. Validar Hermes GET/WS readonly apenas 127.0.0.1 com token do próprio ambiente, negar escrita via HTTP e verificar logs sem token.
7. Fazer atualização com versão V2 instalada e snapshot conhecido; testar rollback V3→V2 sem restore de dados. Só depois considerar uso prolongado.
8. Registrar `DONE` ou `BLOCKED` com evidências e rollback em caso de falha.
