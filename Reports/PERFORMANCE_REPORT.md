# Performance

Não medida em Windows. A ponte é um processo Python persistente, comunica por stdio e serializa chamadas IPC, evitando spawn a cada interação. O core preserva SingleInstance; o catálogo usa `ui_list` paginado no core. Filtro de origem é implementado com travessia de páginas e pode ser custoso em catálogos muito grandes; otimizar no core num release futuro mantendo contrato autenticado.

Metas de 2,5 s startup, navegação 100 ms e 60fps exigem medição com executável compilado. **Sem números simulados.**
