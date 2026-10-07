# Insights Brasil — interface Vue

Aplicação Vue 3 + Vite para explorar séries locais de dívida pública, orçamento, PIB, programas sociais e arrecadação tributária.

## Rodar localmente

Na raiz do repositório, gere o pacote estático para o navegador:

```sh
uv run python web/scripts/build_data.py
```

Depois:

```sh
cd web
npm install
npm run dev
```

Abra exatamente o endereço `Local` mostrado por esse comando. Se já havia outro Vite em execução, encerre-o com `Ctrl+C` antes de iniciar este; quando a porta padrão está ocupada, o Vite escolhe outra porta. Depois de atualizar o código, faça uma recarga forçada no navegador (`Cmd+Shift+R` no macOS / `Ctrl+Shift+R` no Windows e Linux).

Para compilar a versão estática:

```sh
npm run build
npm run preview
```

## Dados no painel

O pacote em `src/assets/data/dashboard.json.gz` é gerado das tabelas de `../data/processed/`. O Vite incorpora o caminho correto dos arquivos no desenvolvimento e no build, inclusive quando o site é hospedado em um subcaminho. Inclui estoque mensal da DPF, juros apropriados mensais e anuais desde 2007, componentes históricos, séries do BCB, fatores, emissões/resgates, composição por carteira e tipo, e execução orçamentária por função.

As posições individuais por título e vencimento são carregadas sob demanda de `src/assets/data/posicoes_por_titulo.csv.gz`; podem ser pesquisadas na página “Explorar dados” ou baixadas no formato original comprimido. A página **PIB** cobre as Contas Nacionais Trimestrais do IBGE desde 1996, com valores nominais, taxas reais oficiais, comparação semestral derivada, setores e componentes da despesa. A página **Impostômetro** mostra arrecadação federal mensal nominal desde 1994, com acumulado apenas até o último mês publicado, variação nominal em 12 meses e, separadamente, carga tributária anual do Governo Geral (União, estados e municípios). A página **Poder de compra** compara o nível de preços desde julho de 1994 pelo IPCA, separando inflação acumulada da perda de poder de compra e de variações cambiais. Para atualizar os dados, use as instruções de coleta e processamento em `../data/README.md` e regenere o pacote do painel.

Inicie a aplicação pelo servidor Vite (`npm run dev`) ou sirva o resultado de `npm run build` com um servidor web. Abrir `index.html` diretamente pelo sistema de arquivos (`file://`) não funciona porque o navegador bloqueia as requisições dos dados.

O painel não faz chamadas a serviços externos em tempo de uso. Os links da página “Fontes e método” apontam para as publicações oficiais usadas na coleta.

## Estudos e métricas

A navegação separa os estudos de dívida, juros, PIB, orçamento e programas sociais. Cada página explica unidade, recorte, fórmulas, exemplos calculados a partir da base e limitações de interpretação. No PIB, valores correntes são separados de taxas de volume reais; taxas oficiais trimestrais não são misturadas com comparações semestrais derivadas. A página de programas sociais inclui a série anual agregada do BPC (2004–2024), o comparativo dos repasses Bolsa Família/BPC em 2024 e a cobertura média por ciclo bimestral do Auxílio Gás. Famílias e pessoas não são somadas nem tratadas como unidades equivalentes.

Nas páginas com gráficos, o controle **Início dos gráficos** alterna entre o histórico completo e a visualização desde 2012. Esse recorte afeta somente as séries desenhadas; cartões de resumo, tabelas do explorador e arquivos exportados mantêm o histórico integral. Na página PIB, o seletor adicional alterna a frequência trimestral, semestral ou anual.

A geração do bundle requer `data/processed/bpc_historico_anual.csv`, além das séries de dívida e orçamento. Execute o comando de geração a partir da raiz do repositório sempre que os dados ou scripts mudarem; a aplicação não baixa dados no navegador.
