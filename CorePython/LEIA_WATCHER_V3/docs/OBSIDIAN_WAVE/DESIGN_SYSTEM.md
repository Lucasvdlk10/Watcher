# Design System — Obsidian Wave

## Linguagem visual

Marca L.E.I.A. como infraestrutura tranquila, soberana e local: superfícies escuras, elementos compactos, pontilhados leves e gradientes originais azul/ciano/violeta. Inspiração tipológica do design contemporâneo; sem transferência de marcas ou assets proprietários. Canvas procedural desenha a onda, com PNG local como apoio.

| Token | Hex | Uso |
|---|---|---|
| background | `#080B12` | shell e área principal |
| sidebar | `#0E111C` | navegação fixa |
| surface | `#151B29` | cards e modais |
| elevated | `#1D2637` | campos e ações discretas |
| stroke | `#293449` | limites e separadores |
| text-primary | `#F3F6FD` | cabeçalhos e valores |
| text-secondary | `#A6B4CC` | explicações e caminhos |
| text-subtle | `#71839E` | metadados menos relevantes |
| accent-blue | `#6B93FF` | ações principais e foco |
| accent-cyan | `#4DE1D6` | sistema local e marca |
| violet | `#9A83FF` | ornamentação de onda |
| success | `#63E6AD` | serviço pronto e OK |
| warning | `#F4C978` | atenção e confirmação |
| danger | `#FF8597` | erro/remover/undo |

## Tipografia e dimensões

Segoe UI local (sem download). Display 23 px, título de página 20 px, título de seção 14–15 px, corpo 10–11 px, label de suporte 9–10 px. Grid de 8 px; cards padding 14–24 px; botões height 32/38 px; raio 12–14 px; largura mínima de janela 960 px; atalho de teclado Enter/Espaço em botões Canvas, Esc nos modais.

## Componentes reais

- **`pill`:** Canvas arredondado, papéis subtle/primary/danger/quiet/success, estado hover/focus; nenhuma dependência CSS/WebView.
- **`surface`:** card com borda discreta, padding estável, aparência material.
- **`field`:** entrada nativa, sem borda clássica; seleção/cópia padrão do sistema.
- **`scroll`:** viewport adaptativo com região rolável.
- **`WaveHero`:** imagem procedural de fundo + até quatro linhas móveis sutis, sem clique capturado no background.
- **`modal` e `confirm`:** textos humanos, cancelamento e palavra crítica; apenas ações administrativas disparam o IPC.
- **`RuleEditor`:** form visual não destrutivo, valida regras determinísticas antes de salvar; editor JSON avançado alternativo.
- **`ui_list`:** busca por argumentos vinculados, limite máximo de 100 registros/página, dados apenas do índice.

## Estados

`CONECTADO`: verde + texto. `DESCONECTADO`: vermelho + explicação e ação explícita de iniciar core. `PAUSED`: mostrado textualmente. `TRACK_ONLY`: ciano. `ORGANIZE`: azul, com confirmações. Erros críticos em rodapé persistente e diálogo de detalhes quando explicitado; dados nunca são transmitidos remotamente. Páginas vazias mostram orientação e próximo passo.

## Movimento

Suave até 30 FPS; reduzido ~11 FPS; em bateria até ~14 FPS. Ao minimizar/perder foco, o timer é cancelado; ao restaurar, volta a rodar. Os bindings de eventos do root são removidos quando o hero é destruído. Sistema operacional Reduced Motion inicializa no modo reduzido caso configurado; override manual é salvo no perfil. Detecção DWM de oclusão não implementada.
