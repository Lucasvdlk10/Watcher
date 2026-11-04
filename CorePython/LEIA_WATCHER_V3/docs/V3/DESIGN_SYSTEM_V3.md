# Design system LEIA V3 · Dark Program

Tonalidade dominante **grafite quase preto + branco + cinzas**. Cores de identidade somente para informação e estados, evitando glow exagerado. Tokens runtime em `ui_kit.py` e assets oficiais originais em `assets_original/`.

- Fundo `#090A0C`, sidebar `#101115`, superfície `#17191D`, elevada `#22252B`, borda `#30333B`.
- Primário `#F4F5F6`; secundário `#B0B5BF`; muted `#8D929D`.
- Ação primária: branco suave com texto carvão, raio ~15 px; ações secundárias cinza escuro; críticas em vermelho dessaturado.
- Azul `#8AABEA`, violeta `#B3A7D9`, ciano `#6ED3C5`: reservados aos dados e à marca; verde `#78C8A7` para OK, âmbar `#E6BD75` para atenção.
- Tipografia: Segoe UI local, sem webfonts; labels técnicas e contagens claras; foco no teclado evidenciado no desenho Canvas.
- Marca: `leia_watcher_48.png` (navegação), `leia_watcher_256.png` (ícone de janela), 12 PNGs de ícones de navegação produzidos a partir dos SVGs oficiais.
- Hero: background procedural local, com linhas finas, malha discreta e gradiente cinza original, mantendo animação suspensa fora do foco da janela.
- Layout: sidebar 216px, dashboard responsivo a largura mínima 960px; superfície visual sobre conteúdo real do IPC; modal para confirmação destrutiva; buscador Ctrl+K não executa comandos perigosos.

A leitura de estado nunca depende exclusivamente da cor: `OK`, `ATIVO / LOCAL`, `DESCONECTADO`, etapas e resultados aparecem textualmente.
