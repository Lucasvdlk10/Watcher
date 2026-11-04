# LEIA Watcher 4.0.0 — WinUI migration source

- Adicionada nova solução C#/XAML WinUI 3 com sete páginas e MVVM.
- Introduzido canal JSON/stdio para o IPC administrativo Python autenticado já existente.
- Mantido integralmente core Python 3.0.0; sem alteração do schema SQLite, regras ou serviço Hermes.
- Adicionado catálogo unificado com filtro de origem, busca e paginação real.
- Editor de regras transacional, layout de pastas e confirmação de ativação.
- Adicionados scripts de build, instalador Windows condicionado ao Release e rollback da interface.
- Atualização visual dark com recursos semânticos e identidade Watcher específica.

**Status:** fonte implementada; build Windows e QA nativo pendentes.
