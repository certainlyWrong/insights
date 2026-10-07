# Insights

Catálogo e ferramentas locais para descobrir, baixar e analisar dados públicos brasileiros. O projeto começa com fontes oficiais federais e guarda os arquivos de origem e os registros coletados localmente.

## Instalação

```sh
uv sync
```

## Comandos

```sh
uv run insights catalog
uv run insights catalog --json
uv run insights fetch pncp_contratacoes --max-pages 2
uv run insights update pncp_contratacoes --max-pages 5
uv run insights status
```

## Análise da dívida pública

O foco de análise atual é a dívida pública brasileira. O repositório inclui os arquivos históricos oficiais do Tesouro e do Banco Central, as tabelas mensais normalizadas em `data/processed/` e o notebook [notebooks/analise_divida_publica_brasil.ipynb](notebooks/analise_divida_publica_brasil.ipynb). A série agregada da DPF vai de dezembro de 2000 a agosto de 2026; fatores e juros apropriados cobrem janeiro de 2007 a agosto de 2026; fluxos, detalhe por título e séries macroeconômicas têm suas próprias coberturas documentadas em [data/README.md](data/README.md).

Para o estudo do orçamento federal em saúde, segurança pública e educação, veja o notebook [notebooks/investimentos_saude_seguranca_educacao.ipynb](notebooks/investimentos_saude_seguranca_educacao.ipynb). Ele compara execução paga e o grupo contábil GND 4 entre 2001 e 2025. A série SIOP pode ser atualizada com `uv run python scripts/baixar_investimentos_areas.py`.

O notebook [notebooks/programas_sociais_brasil.ipynb](notebooks/programas_sociais_brasil.ipynb) analisa a evolução do BPC (2004–2024) e compara sua escala de repasses com Bolsa Família e Auxílio Gás em 2024. Os indicadores são agregados, de fontes do MDS, e as unidades de cobertura distintas são explicitadas.

O painel também inclui uma página de estudo do PIB com a série trimestral do IBGE desde 1996, valores correntes, taxas reais oficiais, comparações por semestre e ano, setores produtivos e componentes da despesa. Atualize a coleta e recompile o bundle com `uv run python scripts/baixar_pib.py` e `uv run python web/scripts/build_data.py`; a origem e o método estão detalhados em [data/README.md](data/README.md).

Uma home page interativa em Vue reúne os indicadores, gráficos e tabelas do projeto. Gere os dados web e inicie a aplicação com:

```sh
uv run python web/scripts/build_data.py
cd web
npm install
npm run dev
```

O guia da interface está em [web/README.md](web/README.md).

Para abrir o notebook:

```sh
uv run jupyter lab
```

Para reconstruir as tabelas tratadas a partir dos arquivos brutos:

```sh
uv run python scripts/processar_divida.py
```

O notebook separa a Dívida Pública Federal (DPF), do Tesouro, da Dívida Bruta do Governo Geral (DBGG), do Banco Central, que inclui também estados e municípios. A comparação com DBGG/PIB é contextual e não trata os dois conceitos como equivalentes. Os arquivos brutos foram baixados de fontes oficiais em 6 de outubro de 2026 e podem ser atualizados pela fonte original; as datas de cobertura e limitações estão registradas em `data/README.md`.

O PNCP consulta contratações publicadas no período de ontem e hoje, para a modalidade 6 (pregão eletrônico), por padrão. Informe filtros próprios com `--param nome=valor`; datas usam `AAAAMMDD`.

Compras.gov.br consulta por padrão as contratações publicadas ontem e hoje, modalidade 5, com até 10 registros por página. As datas usam os parâmetros `dataPublicacaoPncpInicial` e `dataPublicacaoPncpFinal` no formato `AAAA-MM-DD`; outros filtros, como `codigoOrgao`, podem ser passados por `--param`.

```sh
uv run insights fetch compras_contratacoes --max-pages 2
```

A API de despesas da CGU exige um token obtido pelo cadastro de e-mail no [Portal da Transparência](https://portaldatransparencia.gov.br/api-de-dados). Defina-o como variável de ambiente e informe o código SIAFI do órgão superior:

```sh
export PORTAL_TRANSPARENCIA_TOKEN="seu-token"
uv run insights fetch cgu_despesas_orgao --param orgaoSuperior=26000 --param ano=2025
```

O exemplo usa o Ministério da Educação (código 26000); não representa todos os órgãos federais. A API de Compras.gov.br também aceita filtros `--param` de acordo com sua [documentação atual](https://www.gov.br/compras/pt-br/cidadao/portal-de-dados-abertos/documentacao-interativa-da-api-de-dados-abertos).

## Arquivos locais

Por padrão, o banco DuckDB fica em `.insights/insights.duckdb`, e respostas brutas versionadas por horário ficam em `.insights/raw/`. Defina `INSIGHTS_HOME` para mudar esse diretório. O banco contém registros JSON consultáveis, hash para deduplicação e histórico de coletas em `records` e `fetch_runs`. O histórico guarda o período e filtros não sensíveis; filtros com possíveis identificadores pessoais e credenciais são omitidos.

Por exemplo, em Python:

```python
import duckdb

db = duckdb.connect(".insights/insights.duckdb", read_only=True)
print(db.sql("SELECT dataset_id, count(*) FROM records GROUP BY 1"))
print(db.sql("SELECT json_extract_string(payload, '$.orgao') FROM records LIMIT 5"))
```

`catalog` inclui também famílias de dados planejadas. Um conjunto marcado como planejado ainda não tem conector de download.

## Fontes iniciais

- [Portal da Transparência / CGU](https://portaldatransparencia.gov.br/api-de-dados)
- [Dados abertos do Compras.gov.br](https://www.gov.br/compras/pt-br/cidadao/portal-de-dados-abertos/portal-de-dados-abertos)
- [API de consulta do PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html)

O coletor limita cada execução a duas páginas por padrão, aplica uma pausa entre páginas, repete tentativas em falhas transitórias e registra os erros. A CGU impõe limite de requisições; consulte os termos e limites vigentes das fontes antes de aumentar o volume.
