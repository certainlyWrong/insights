# Insights Brasil

Projeto local para coletar, organizar e explorar dados públicos brasileiros de fontes oficiais. Reúne um painel web, estudos em notebooks e uma ferramenta de linha de comando; o foco analítico atual é a dívida pública, junto de orçamento, PIB, tributos e políticas sociais.

## Começar

Requisitos: [uv](https://docs.astral.sh/uv/) e Node.js com npm.

```sh
./start.sh
```

O script prepara o ambiente, instala as dependências web quando necessário, atualiza o bundle local e inicia o site em <http://127.0.0.1:5173>. Encerre com `Ctrl+C`.

Atalhos para compilar e distribuir o projeto (opcional: `make`):

```sh
make build    # bundle de dados + build de produção do site
make pdf      # atualiza o bundle e gera a apresentação
make package  # gera o PDF e o ZIP do projeto
```

Os arquivos resultantes ficam em `artifacts/`.

## Organização do projeto

```text
.
├── src/insights/      # CLI, catálogo de fontes, coleta e armazenamento DuckDB
├── data/
│   ├── raw/           # respostas e arquivos preservados das fontes oficiais
│   ├── processed/     # tabelas normalizadas usadas nos estudos e no site
│   └── README.md      # cobertura, método, limitações e fontes por conjunto
├── notebooks/         # análises reproduzíveis em Jupyter
├── scripts/           # atualização de dados, geração de PDF e empacotamento
├── web/               # painel em Vue 3 + Vite e gerador do bundle local
├── artifacts/         # PDF de apresentação e ZIP distribuível
├── .insights/         # banco DuckDB e coletas da CLI (criado em tempo de uso)
├── pyproject.toml     # dependências e configuração Python/uv
├── uv.lock            # versões travadas das dependências Python
├── Makefile           # atalhos de build, PDF e pacote
└── start.sh           # inicialização rápida do painel
```

### Estudos disponíveis

- **Dívida pública:** estoque da DPF, juros apropriados, fatores de variação, emissões e resgates, composição e comparação contextual com DBGG/PIB.
- **Orçamento:** execução federal paga em saúde, segurança pública e educação, além do grupo de investimentos GND 4.
- **Programas sociais:** histórico agregado do BPC e contexto de Bolsa Família e Auxílio Gás.
- **PIB:** Contas Nacionais Trimestrais do IBGE, com valores nominais e taxas reais.
- **Tributos:** arrecadação federal mensal e carga tributária anual do Governo Geral.
- **Poder de compra:** evolução dos preços pelo IPCA desde julho de 1994.
- **Estudo visual completo:** [notebooks/estudo_graficos_politicas_publicas.ipynb](notebooks/estudo_graficos_politicas_publicas.ipynb) reúne os gráficos do painel e as explicações de leitura.

Os notebooks estão em `notebooks/`. O painel apresenta gráficos, indicadores, explicações de métricas e fontes. O site usa dados locais já empacotados e não consulta APIs enquanto está aberto.

## Atualizar e analisar dados

O fluxo das séries históricas é: obter ou substituir arquivos em `data/raw/`, executar os scripts de processamento e, por fim, reconstruir o bundle do painel.

```sh
# Dívida e séries de orçamento
uv run python scripts/processar_divida.py
uv run python scripts/baixar_investimentos_areas.py

# PIB: baixa a publicação mais recente e atualiza a tabela processada
uv run python scripts/baixar_pib.py

# Tributos: após atualizar os arquivos brutos oficiais
uv run python scripts/processar_impostos.py

# Reunir tabelas processadas para o site
uv run python web/scripts/build_data.py
```

Abra os estudos com:

```sh
uv run jupyter lab
```

Detalhes de cobertura, fontes, fórmulas e limitações ficam em [data/README.md](data/README.md). A coleta não é agendada: atualizações são iniciadas manualmente.

## CLI e armazenamento local

Instale as dependências Python com `uv sync`. A CLI oferece catálogo de conjuntos, coleta e estado local:

```sh
uv run insights catalog
uv run insights catalog --json
uv run insights fetch pncp_contratacoes --max-pages 2
uv run insights update pncp_contratacoes --max-pages 5
uv run insights status
```

O banco fica em `.insights/insights.duckdb`; respostas brutas da CLI ficam em `.insights/raw/`. Defina `INSIGHTS_HOME` para usar outro diretório. Alguns conjuntos da CGU exigem token: configure `PORTAL_TRANSPARENCIA_TOKEN` no ambiente, sem gravá-lo no projeto. Os limites e filtros dos conectores estão documentados em [web/README.md](web/README.md) e na documentação oficial de cada fonte.

## Apresentação e ZIP

```sh
make pdf      # artifacts/apresentacao_insights_brasil.pdf
make package  # artifacts/insights-brasil-projeto.zip
```

O PDF é compilado pela execução do notebook de estudo: traz os gráficos e suas explicações, sem exibir código. O notebook também guarda as figuras como saídas para consulta no Jupyter. O ZIP reúne código, notebooks, dados, banco local e PDF. Não inclui `.venv`, `.git`, `node_modules`, `web/dist` nem caches; as dependências são recriadas com `uv sync` e `npm ci --prefix web`.
