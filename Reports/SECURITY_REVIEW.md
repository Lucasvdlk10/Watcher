# Revisão de segurança

- Bridge JSON/stdio somente no computador, sem endpoint HTTP de escrita.
- IPC `multiprocessing.connection` autenticado: o Python obtém admin.secret localmente; o C# não o lê nem o apresenta.
- Comandos da ponte em allowlist. `stop`, comandos de shell arbitrários e acesso a segredos proibidos.
- Ativação de organização exige `I_CONFIRM_FILE_MOVES`; regras validadas pelo core.
- Executa `undo`, `update_root` e operações administrativas apenas pelo core.
- `SingleInstance` já existe no motor e não foi alterado.
- Nenhuma telemetria externa. Não existe uso de LLM no frontend.
- Instalador faz hash de binário, backup consistente SQLite e rollback de interface.

**Não verificado:** assinaturas Authenticode, WinUI compiled binary, ACL Windows, code signing do instalador, resistência a DLL hijack, sandboxing e scan antivírus.
