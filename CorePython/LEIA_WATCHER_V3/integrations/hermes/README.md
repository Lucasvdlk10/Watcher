# Integração opcional Hermes (somente leitura)

O Watcher não mexe na configuração já existente do Hermes. Para disponibilizar a busca de arquivos ao seu agente, use o código `leia_watcher_reader.py` como uma ferramenta local dentro do runtime Hermes, de acordo com seu carregador de ferramentas existente. **Não há chamada LLM neste módulo; o Hermes decide quando chamar a ferramenta.**

```python
from leia_watcher_reader import LEIAWatcherReader
api = LEIAWatcherReader(port=8766)
print(api.find(query='proposta',extension='.pdf',limit=25))
```

Leia o token protegido do perfil do usuário (`%LOCALAPPDATA%\LEIA\Watcher\data\hermes_read.token`). Não envie esse segredo ao contexto da IA, a mensagens, URLs, analytics ou logs. O endpoint aceita apenas `Authorization: Bearer`. A integração não organiza arquivos, não altera o inventário e não exporta bytes de documentos. Verificar que o Hermes esteja executando sob o mesmo usuário Windows com permissão para ler o token.
