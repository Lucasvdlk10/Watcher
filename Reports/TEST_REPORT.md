# RELATÓRIO DE TESTES — 2026-10-21

| Suite | Resultado | Ambiente |
|---|---|---|
| Core Python V3 fornecido | **129/129 PASS** | Python 3.13, Linux (cópia intacta) |
| Bridge V4 | **10/10 PASS** | Python 3.13, Linux |
| IPC autenticado contra core real | **PASS** | Perfil isolado, socket Unix no Linux |
| XAML — boa formação XML | **17/17 PASS** | Parser XML; não é validação XAML Microsoft |
| Wheel core V3 | preservado | Não foi instalado no Windows |
| .NET WinUI 3 build x64 | **NÃO EXECUTADO** | SDK/Windows indisponível |
| Windows installer e rollback | **NÃO EXECUTADOS** | Windows indisponível |
| UI Automation, Narrator, DPI e screenshots | **NÃO EXECUTADOS** | Windows indisponível |

### Smoke com motor real

`tests/BridgeTests/test_real_core_bridge.py` inicia o Watcher V3 em perfil **temporário**, chama a ponte via stdin/stdout, valida `ping` com `no_llm=true`, `db=ok`, cria uma raiz TRACK_ONLY, consulta `ui_snapshot` e `ui_files_origin`, cria backup, verifica que o arquivo original não é movido e que `_LEIA_Organizado` não foi criado.

### Limitação crítica

Os gates do PRD que exigem **binário WinUI, instalação Windows real, testes UI e screenshots reais** não foram satisfeitos; não há declaração de aceite final.
