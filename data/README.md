# Dados históricos da dívida pública

## Produto Interno Bruto — Contas Nacionais Trimestrais

`raw/ibge/contas_nacionais_trimestrais_sidra.json` aponta para a coleta mais recente; arquivos `contas_nacionais_trimestrais_sidra_YYYYMMDDTHHMMSSZ.json` preservam cada snapshot e as respostas da API oficial do [IBGE/SIDRA](https://sidra.ibge.gov.br/pesquisa/cnt/tabelas), com horário de coleta em UTC. A coleta usa a tabela 1846 (valores correntes, milhões de reais), 1620 (índice encadeado de volume, base média 1995=100) e 5932 (taxas de variação do volume). `processed/pib_trimestral.csv` consolida PIB a preços de mercado, os três grandes setores e componentes de despesa desde 1996-T1 até o último trimestre divulgado (2026-T2 na coleta atual).

As taxas de crescimento trimestre contra trimestre com ajuste sazonal, contra o mesmo trimestre do ano anterior, acumulada no ano e acumulada em quatro trimestres são séries publicadas pelo IBGE. Os valores correntes de semestres e anos são somas trimestrais; a taxa nominal compara com o mesmo período do ano anterior. A comparação real semestral usa a razão entre as somas (equivalente à média, com igual número de trimestres) dos índices trimestrais de volume não ajustados e é derivada pelo projeto, não publicada como taxa semestral pelo IBGE. Períodos sem cobertura comparável ficam sem taxa. O IBGE pode revisar períodos históricos; o arquivo bruto registra a versão consultada e sua data.

Atualize e gere o bundle local do site com:

```sh
uv run python scripts/baixar_pib.py
uv run python web/scripts/build_data.py
```

Os arquivos em `raw/` são cópias dos dados publicados pelos órgãos responsáveis, baixadas em 6 de outubro de 2026. As planilhas do Tesouro contêm observações até agosto de 2026; o CSV detalhado por título chega a julho de 2026. Os arquivos em `processed/` são tabelas normalizadas pelo script `scripts/processar_divida.py`.

O arquivo processado `dpf_posicoes_por_titulo.csv.gz` preserva as posições individuais e os vencimentos interpretados do CSV detalhado, mantendo a cobertura de setembro de 2017 a julho de 2026.

URLs de origem, tamanho dos arquivos e hashes SHA-256 estão registrados em [source_manifest.json](source_manifest.json).

## Orçamento federal em saúde, segurança pública e educação

O arquivo `raw/siop/execucao_por_funcao_2001_2025.json` preserva as respostas anuais agregadas e as consultas SPARQL ao [endpoint aberto do SIOP](https://www1.siop.planejamento.gov.br/sparql/), conforme a [documentação oficial do orçamento aberto](https://orcamento.dados.gov.br/siopdoc/doku.php/acesso_publico:dados_abertos/) e os [exemplos de consultas SPARQL](https://orcamento.dados.gov.br/siopdoc/doku.php/acesso_publico:scripts_sparql). A tabela tratada está em `processed/orcamento_saude_seguranca_educacao.csv`.

A série cobre 2001–2025 e contém valores pagos e liquidados para as funções orçamentárias 06 (Segurança Pública), 10 (Saúde) e 12 (Educação), mais os totais do GND 4 (Investimentos) dentro de cada função. Valores originais estão em reais correntes. O notebook apresenta os totais pagos em R$ correntes e também corrigidos pelo IPCA para preços médios de 2025. O ano de 2026 não foi incluído porque estava incompleto na data da coleta.

Esta base representa a execução do orçamento federal no SIOP; não inclui as despesas próprias de estados e municípios. “Total pago por função” inclui despesas correntes e de capital. GND 4 é apenas a classificação orçamentária de investimentos e não equivale ao gasto total da função. O SIOP é uma base dinâmica; as respostas e consultas usadas estão preservadas no arquivo bruto.

## Programas sociais

`processed/bpc_historico_anual.csv` registra a tabela agregada anual do [VIS DATA 3/SAGICAD-MDS](https://aplicacoes.cidadania.gov.br/vis/data3/v.php?ma=ano&q%5B%5D=r6C5ZNnryaG4emVqrWZ9f2RdiJxlmm9niquBYWx5sZzpnKy%2Bp5G2w5jYeJm%2B58CZd7ynr950iMKporycbt2yoIDdvZebsZmp7KissJybkseU1rCYmO%2B%2FqaGDcK7rrrKJcqDMzlbMrZa8672Ym76hde2rwrNyocnWmKV4p8%2Fwsm93u6qnnJu9sZaWu9Cm2ZypybbBprGtcK7rrrKJcqHJ1pileKbS6HCvXauWrd5ZxLacm3fEosupmNDeslx8qqWd2Km9spaPvM9fmmZTiJuwo520mq3cnnWOmZ26wJzOrKbM2q%2BZqnRlY5l3bX5Xob%2FGoYqgor7nsqefrV1626mwraedu8CVz6tfjaRtX1yrpJvlnsCxnFWXw6PNnJzB6sCjm6qaqKVpdm6cmcrGU9iyn8mbsqKgabJ135q5wZxoy9Ooz3huw9y5p6GDcK3upnDJWJC41JiKtJvC6W2Xq6mhn%2BycsnZ3j8fEktqtl7zxuWBscVVlmZy8r6OSysSYkn2Vzd6snaC3qKnYr7l6Z1Z3n1OaXafF4LtUn7eWpt6ssLNfbbnRlsmto8Haw6BoeF5apFmwvZiZvNSWz2Vzv%2Buwk6WspK3omMO6Y12AgZjWsJh96cKgqGiaqN1ayomrn8zGbt6vqMK2iJqdtKiftHTAw6Spp8am3ayU0Juwo6loeZ%2FforC3%2BtfFxJzLXVutvpFdXKqaqN6ftrGg8PjTnMuwU8HqbXaMi1iD3ajAvapNucahz6OcwOQQ1a6xpK2ZnbxueX2ahInLqaLPm5%2BZrKmordqdvG6YTaekd91do8LnvFR%2BmHhdz5q5valNqcajy7Cmvt%2B8VJ1ofp7orLzBV528zaKKf4OgnqGjsKmhWt2ebZCcm7zHnM2m9v7ttqOvaJmpmXudkVqDuM2i3F2HzO%2BuoFy6mqrarMCvm5x3wqKKf4Og971vuMSxbKlpgXtnXoSRZL5tY5erfW5seI91), com contagens de pessoas com deficiência e idosas beneficiárias e valores anuais repassados, de 2004 a 2024. A série é agregada; nenhum identificador pessoal foi coletado. O estudo também usa o total de R$ 168,3 bilhões e mais de 20,86 milhões de famílias alcançadas pelo Bolsa Família em 2024, conforme o [balanço do MDS](https://www.gov.br/mds/pt-br/noticias-e-conteudos/desenvolvimento-social/noticias-desenvolvimento-social/governo-federal-repassa-r-168-3-bilhoes-pelo-bolsa-familia-em-2024), e a cobertura média do Auxílio Gás por ciclo bimestral informada no Relatório de Gestão 2024. Beneficiários individuais e famílias não são unidades comparáveis; tampouco se somam os públicos dos programas.

O notebook [programas_sociais_brasil.ipynb](../notebooks/programas_sociais_brasil.ipynb) explica a metodologia, as fontes e as limitações da comparação. Os valores estão em reais correntes, sem ajuste inflacionário.

## Arrecadação federal e carga tributária

`raw/tributos/arrecadacao_receitas_federais_1994_2025.xlsx` contém a série histórica mensal oficial da Receita Federal, em R$ milhões correntes. O total geral é a soma das receitas administradas pela RFB e das administradas por outros órgãos. O anexo mensal mais recente (`raw/tributos/arrecadacao_federal_2026_ate_agosto.xlsx`, Tabela III) revisa e detalha essa mesma cobertura de janeiro de 2021 a agosto de 2026. `processed/arrecadacao_federal_mensal.csv` mantém o histórico até 2020 e substitui os meses a partir de 2021 pelos dados revisados do anexo.

`raw/tributos/carga_tributaria_governo_geral_2025.xlsx` e `processed/carga_tributaria_governo_geral_anual.csv` registram a carga tributária bruta anual de 2010 a 2025, por esfera de governo e como percentual do PIB, conforme o Tesouro Nacional. Essa série inclui Governo Central, estados e municípios; é um contexto anual distinto da arrecadação federal mensal.

O contador da página “Impostômetro” mostra a soma nominal acumulada dos meses efetivamente publicados no ano. Não interpola valores diários nem projeta meses futuros. A variação nominal em 12 meses mistura preços, atividade, alterações legais e composição da arrecadação; não deve ser lida como crescimento real. As fontes podem revisar os dados.

Para refazer os arquivos processados e atualizar o bundle local do site após substituir os arquivos brutos pelas publicações oficiais mais recentes:

```sh
uv run python scripts/processar_impostos.py
uv run python web/scripts/build_data.py
```

## Poder de compra do real e IPCA

A série mensal IPCA (SGS 433), obtida do [Banco Central do Brasil](https://dadosabertos.bcb.gov.br/dataset/433-indice-nacional-de-precos-ao-consumidor-amplo-ipca) e calculada pelo IBGE, está preservada em `raw/bcb/ipca_mensal.json`. Para medir a evolução dos preços desde o real, julho de 1994 é a referência igual a 100 e as variações são compostas a partir de agosto de 1994. O índice de preços é o produto dos fatores mensais; inflação acumulada é o índice dividido pela base menos 1. A perda do poder de compra é calculada separadamente como `1 - (índice-base / índice atual)`. Assim, inflação acumulada e perda de poder de compra não são percentuais iguais.

Essa conversão é uma aproximação para o nível médio de preços medido pelo IPCA e não representa a inflação pessoal de cada família nem a variação cambial do real. A resposta exibida no painel usa o último mês presente no arquivo bruto; a coleta atual termina em agosto de 2026.

## Inflação e preços dos alimentos

`scripts/baixar_inflacao_alimentos.py` consulta fontes oficiais do IBGE/SIDRA e do Banco Central. O SIDRA usa as tabelas 655 (1999–2006), 2938 (2006–2011), 1419 (2012–2019) e 7060 (2020 em diante), que preservam a classificação do IPCA de cada período. O SGS 1635 fornece a série longa do grupo Alimentação e bebidas desde 1991; o SGS 433 fornece o índice geral. A tabela tratada nacional fica em `processed/ipca_alimentos_nacional.csv`; `processed/ipca_alimentos_regional.csv` contém agregados por áreas pesquisadas e subitens regionais publicados pela tabela 7060 (desde 2020).

Cada coleta guarda as respostas compactadas em `raw/ibge/ipca_alimentos_sidra_YYYYMMDDTHHMMSSZ.json.gz` e atualiza `raw/ibge/ipca_alimentos_sidra.json.gz`. A taxa em 12 meses e o acumulado no ano são compostos a partir das taxas mensais, com períodos ausentes preservados como nulos. Índices rebaseados e distribuição dos subitens são métricas analíticas derivadas. Pesos publicados são preservados quando disponíveis; impactos aproximados não substituem contribuições oficiais. O IPCA mede variação e índice de preços ao consumidor, não preço de varejo unitário em reais. Tabelas e ponderações podem ser revistas e mudam ao longo do histórico.

Para atualizar e gerar o pacote independente do site:

```sh
uv run python scripts/baixar_inflacao_alimentos.py
uv run python web/scripts/build_data.py
```

Os bundles `web/src/assets/data/ipca_alimentos_nacional.json.gz` e `web/src/assets/data/ipca_alimentos_regional.json.gz` são carregados sob demanda pela página e pelo explorador; os dados regionais só são lidos quando a comparação por área se aproxima da tela ou quando essa base é escolhida no explorador. A navegação não consulta APIs externas. O DIEESE e a Conab não foram automatizados: não foi identificada uma série pública estruturada de preços por produto sem assinatura ou CAPTCHA, nem API oficial pública documentada adequada para coleta.

## Fontes

| Arquivo bruto | Fonte e conteúdo | Histórico disponível | Licença |
| --- | --- | --- | --- |
| `raw/tesouro/estoque-dpf-resumo.xlsx` | [Tesouro Transparente — Estoque da Dívida Pública Federal](https://www.tesourotransparente.gov.br/ckan/dataset/0998f610-bc25-4ce3-b32c-a873447500c2) | Dez/2000–Ago/2026, mensal; valores em R$ bilhões | ODbL |
| `raw/tesouro/estoquedpf.csv` | Mesmo conjunto; detalhe por título/contrato, classe de carteira, tipo de dívida e vencimento | Set/2017–Jul/2026, mensal; valores em R$ | ODbL |
| `raw/tesouro/fatores-variacao-dpf.xlsx` | [Tesouro Transparente — Fatores de variação da DPF](https://www.tesourotransparente.gov.br/ckan/dataset/fatores-de-variacao-da-divida-publica-federal) | Jan/2007–Ago/2026; valores em R$ milhões | ODbL |
| `raw/tesouro/emissoes-resgates-dpf.xlsx` | [Tesouro Transparente — Emissões e resgates da DPF](https://www.tesourotransparente.gov.br/ckan/dataset/emissoes-e-resgates-divida-publica-federal) | Nov/2006–Ago/2026; valores em R$ milhões | ODbL |
| `raw/bcb/dbgg_pib.json` | [Banco Central — DBGG/PIB (SGS 13762)](https://dadosabertos.bcb.gov.br/dataset/13762-divida-bruta-do-governo-geral--pib---metodologia-utilizada-a-partir-de-2008) | Dez/2006–Ago/2026, mensal; percentual do PIB | ODbL |
| `raw/bcb/divida_liquida_gg_pib.json` | [Banco Central — DLGG/PIB (SGS 4536)](https://dadosabertos.bcb.gov.br/dataset/4536-divida-liquida-do-governo-geral--pib) | Jan/2002–Ago/2026, mensal; percentual do PIB | ODbL |
| `raw/bcb/ipca_mensal.json` | [Banco Central — IPCA mensal (SGS 433)](https://dadosabertos.bcb.gov.br/dataset/433-indice-nacional-de-precos-ao-consumidor-amplo-ipca) | Jan/1980–Ago/2026, mensal; variação percentual | ODbL |

## Escopo e interpretação

DPF é a dívida sob responsabilidade do Tesouro Nacional. DBGG é uma medida do Banco Central que abrange débitos do Governo Federal, estados e municípios; portanto, a série DBGG/PIB é indicador macroeconômico de contexto, não uma razão calculada diretamente sobre o estoque da DPF. A DPF inclui dívida mobiliária interna e externa, apurada segundo a metodologia documentada pelo Tesouro.

Os dados podem ser revisados pelo órgão de origem. A planilha de estoque agrega mensalmente o histórico longo; o arquivo CSV detalhado por título tem janela temporal menor. Os gráficos respeitam essa cobertura. Nenhum dado individual de cidadãos foi coletado.

## Juros da DPF

A planilha de fatores registra mensalmente desde janeiro de 2007 os “Juros Apropriados” da DPMFi e da DPFe, além do total da DPF. Trata-se de apropriação por competência de juros e encargos sobre títulos e contratos, conforme os metadados do Tesouro; não é sinônimo de pagamento em caixa no mesmo período. A análise anual soma esses valores nominais e também mostra uma taxa implícita aproximada, calculada dividindo os juros do ano pelo estoque médio mensal da DPF. Essa razão analítica não substitui o indicador oficial de custo médio da dívida, publicado pelo Tesouro nos [Relatórios Mensais da Dívida](https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd) e calculado conforme a [metodologia oficial dos indicadores da DPF](https://www.tesourotransparente.gov.br/publicacoes/metodologia-de-calculo-dos-indicadores-da-divida-publica/2021/30).

Para reconstruir as tabelas processadas:

```sh
uv run python scripts/processar_divida.py
uv run python scripts/baixar_investimentos_areas.py
```
