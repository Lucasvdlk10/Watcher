# PRD · LEIA Watcher Obsidian Wave 2.0

**Tipo:** atualização visual de produto existente. **Escopo:** shell visual, operações de UX, extensão IPC read-only e upgrade local. **Baseline:** Watcher 1.0.0 fornecido. **Idioma:** pt-BR. **Plataforma-alvo:** Windows 10/11 x64.

## 1. Problema e oportunidade

O monitoramento local, organização determinística e integração read-only do Watcher estão operacionais, porém a antiga interface com Notebook e Treeview no tema `clam` comunica uma experiência de software legado. Usuários têm dificuldade em ler estado geral, entender risco de operações, fazer buscas, criar regras sem editar JSON e distinguir atividade normal de falha.

**Hipótese de produto:** uma interface de alta legibilidade, informação hierarquizada e confirmação progressiva melhora o controle sem sacrificar desempenho, privacidade ou segurança. Não se pretende criar um novo motor ou passar o trabalho a modelos de IA.

## 2. Visão e objetivos

- O estado das pastas, banco, indexação e pendências deve ser compreendido na primeira tela.
- O painel deve transmitir sofisticação e leveza, preservando identidade LEIA própria.
- A operação comum deve ser guiada: cadastrar, simular, revisar, ativar; erros traduzidos.
- As rotinas mais delicadas nunca devem ser disparadas ao abrir UI ou navegar.
- Core continua autônomo, mesmo se o usuário fechar toda a interface.
- O usuário pode reverter a atualização visual com cópia consistente do banco e configuração.

## 3. Escopo funcional

| ID | Requisito | Prioridade | Entrega |
|---|---|---|---|
| OUI-01 | Dashboard com saúde geral, inventário, pastas e pendências | P0 | Implementado |
| OUI-02 | Navegação lateral e componentes originais modernos | P0 | Implementado |
| OUI-03 | Fundo procedural azul/violeta/ciano sem rede | P0 | Implementado |
| OUI-04 | Pausar movimento quando UI perde foco ou minimiza | P0 | Implementado; oclusão exata não verificada |
| OUI-05 | Preferência de movimento normal/reduzido/off e política de bateria | P0 | Implementado |
| OUI-06 | Pastas com nome humano, modo, estado, data e comandos | P0 | Implementado |
| OUI-07 | Simular antes de ativar ORGANIZE e exigir confirmação textual | P0 | Implementado |
| OUI-08 | Editor de regras visual por tipo, palavra, data, tamanho e origem | P0 | Implementado |
| OUI-09 | Manter editor JSON secundário com validação de domínio | P1 | Implementado |
| OUI-10 | Busca paginada de inventário e auditoria por IPC | P0 | Implementado |
| OUI-11 | Mostrar integração Hermes sem jamais renderizar segredo | P0 | Implementado |
| OUI-12 | Ações perigosas separadas com confirmação forte | P0 | Implementado |
| OUI-13 | Atualização offline com backup e rollback de baseline | P0 | Implementado; Windows real pendente |
| OUI-14 | Responsividade Windows HiDPI, Narrator e multimonitor | P1 | Parcial; requer homologação nativa |
| OUI-15 | Occlusion detection exata, 50 ciclos e GPU/RAM benchmark | P1 | Não homologado |
| OUI-16 | Ícone de bandeja nativo e `.exe` standalone | P2 | Não incluído |

## 4. Critérios de não regressão (mandatórios)

1. `TRACK_ONLY` jamais move arquivos; ações de movimentação continuam no engine original.
2. Organização só é ativada por IPC local com confirmação `I_CONFIRM_FILE_MOVES` e verificação explícita na GUI.
3. SQLite WAL, migrações v1, journal, políticas RENAME/SKIP, OVERWRITE opt-in, `undo` e backups preservados.
4. Arquivos instáveis, temporários, symlinks, junctions, paths fora do diretório, output e raízes sobrepostas continuam impedidos pelo engine.
5. REST/WS Hermes apenas loopback, Bearer; nenhum POST, PATCH, PUT, DELETE; UI nunca recebe o segredo.
6. Nenhum arquivo do Hermes é modificado e nenhuma chamada a modelos ocorre.
7. A GUI consulta IPC autenticado; não usa acesso direto ao SQLite e não cria/ativa jobs no boot.
8. Banco, tokens, roots, histórico e backups persistentes continuam sob `%LOCALAPPDATA%\LEIA\Watcher`.
9. Upgrade/rollback não requerem permissão de administrador nem conexão à internet.

## 5. Personas e histórias de usuário

**Operador:** quer compreender o estado de monitoramento sem ver termos de SQLite; ao cadastrar Downloads deve começar em rastreio e ver uma explicação de que organização move arquivos. **Administrador técnico:** precisa inspecionar eventos de erro, exportar CSV com ciência de caminhos privados, fazer backup e desfazer alterações protegidas. **Integração Hermes:** consulta índice e histórico, jamais organiza via HTTP.

- Como operador, vejo a saúde em segundos e sei se há algo que exige atenção.
- Como operador, filtro arquivos pelo nome/raiz/estado e copio metadados sem abrir o conteúdo.
- Como operador, edito uma categoria do classificador sem tocar em JSON; o motor valida tudo antes de salvar.
- Como operador, uma alteração de regras em pasta ORGANIZE ativa não dispara novos movimentos sem nova confirmação.
- Como técnico, encontro ações, resultados e códigos em um histórico; exporto apenas com confirmação.
- Como usuário, posso desligar a animação para reduzir distração e consumo.

## 6. Diretrizes de UX

Estilo **Obsidian Wave**: fundo grafite, sobreposição de cards noturnos, tipografia Segoe UI, pontos e linhas luminosas originais, sem copiar a identidade Stitch. Área principal com largura útil a partir de 960 px, cartões flexíveis, tabela paginada, contraste por texto e por ícones. Botões rotineiros distintos de ações críticas; cores são apoio e não o único meio de comunicar estado. Modais críticos exibem consequência, ação de cancelamento e, quando necessário, palavra confirmatória.

### Fluxos que devem manter invariantes

Cadastro de raiz: `TRACK_ONLY` padrão → seleção pasta → validação no core → inventário seguro. Para ORGANIZE: cadastro desativado → edição/simulação → confirmação de texto → ativação e varredura. Mudança de política em raiz ativa: salvar (desativa) → simular → ativar com confirmação.

## 7. Requisitos não funcionais

- Rede: zero dependências remotas; nenhuma telemetria.
- Privacidade: não exibir token, não abrir conteúdo de documentos, exports por consentimento.
- Performance: consultas IPC executadas em threads worker; mainloop Tk não deve bloquear durante chamadas longas. A onda usa até 30 FPS e pausa timers fora de foco. Modo reduzido ~11 FPS; em bateria ~14 FPS.
- Manutenibilidade: `ui_kit` componentes, `ui_rules` transformações puras, `ui_queries` IPC read-only, `ui_prefs` configurações de movimento.
- Acessibilidade: foco de teclado nos botões principais; texto nativo selecionável em entradas; contraste claro. Testes completos com Narrator seguem pendentes.
- Segurança: sem privilégios elevados e sem elevação de superfície HTTP de escrita.

## 8. Métricas e aceite

Aceitar tecnicamente depois de: testes de regressão existentes + novos testes passarem; instalação do wheel isolado; UI conectar com core sem disparar ações no boot; comando `ui_list` retornar apenas metadados e respeitar limites. Aceitar em produção **somente** depois da validação Windows real (Windows 10 e 11, escalas de 100–200%, múltiplos monitores, perda de foco, 50 minimizar/restaurar, 100 focos alternados, suspensão, backup, rollback, WinAPI e NTFS).

## 9. Fora do escopo

Reescrever engine, mudar algoritmos de classificação, adicionar OCR/LLM, alterar Hermes, transmitir eventos para nuvem, usar WebEngine, modificar dados reais enviados pelo operador, instalar drivers, adicionar atualizador com download remoto ou prometer `.exe` sem compilá-lo.

## 10. Riscos e mitigação

- Tk Canvas não fornece blur/composição real como Qt Quick: surfaces sólidas permitem contraste e runtime leve; documentar limite.
- Windows-specific widgets/DPI não testados no host: manutenção de compatibilidade com Tk/Python 3.11–3.13 e homologação obrigatória.
- Motorização da onda com foco incorreto: cancelar timers ao perder foco e remover bindings no destroy; script de smoke para ciclos.
- Erro no update: parar core, backup consistente via `sqlite3.backup`, instalação offline, verificar integridade e fornecer rollback.
- Alteração inesperada de regras ativas: forçar `enabled=false` antes de aplicar mudança de ORGANIZE.
