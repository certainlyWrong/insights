<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, toRefs, watch } from "vue";
import { ArrowUpRight, ExternalLink } from "@lucide/vue";
import TrendChart from "../components/TrendChart.vue";

const state = inject("dashboard");
const { foodData, foodRegionalData, foodLoading, foodRegionalLoading, activeData, chartTheme, palette, chartGuides, percent, go } = toRefs(state);
const pretty = state.pretty;
const area = ref("");
const regionalPanel = ref(null);
const selectedProduct = ref("");
const selectedGroup = ref("");
const rankMetric = ref("valor");
const national = computed(() => foodData.value?.nacional || []);
const regional = computed(() => foodRegionalData.value?.regional || []);
const foodRows = computed(() => national.value.filter((row) => String(row.classificacao_codigo) === "7170"));
const latestFood = computed(() => foodRows.value.at(-1));
const products = computed(() => {
  const rows = national.value.filter((row) => row.nivel_territorial === "Brasil" && row.classificacao_caminho && String(row.classificacao_caminho).length >= 7 && /^[12]/.test(String(row.classificacao_caminho)));
  const found = new Map();
  rows.forEach((row) => found.set(String(row.classificacao_codigo), { code: String(row.classificacao_codigo), name: row.classificacao }));
  return [...found.values()].sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
});
const productOptions = computed(() => products.value.filter((product) => !selectedGroup.value || String(national.value.find((row) => String(row.classificacao_codigo) === product.code)?.classificacao_caminho || "").startsWith(selectedGroup.value)));
const territories = computed(() => [...new Map(regional.value.map((row) => [String(row.territorio_codigo), { code: String(row.territorio_codigo), name: row.territorio }])).values()].sort((a, b) => a.name.localeCompare(b.name, "pt-BR")));
const selectedAreaCode = computed(() => area.value || territories.value[0]?.code || "");
const selectedAreaName = computed(() => territories.value.find((item) => item.code === selectedAreaCode.value)?.name || "Brasil");
const foodGroupRows = computed(() => national.value.filter((row) => ["7170", "7171", "7432"].includes(String(row.classificacao_codigo))));
const colors = computed(() => [palette.value.ink, palette.value.teal, palette.value.coral, palette.value.gold, palette.value.slate]);
const common = computed(() => ({
  animation: false,
  tooltip: { trigger: "axis", backgroundColor: chartTheme.value.tooltip, borderWidth: 0, textStyle: { color: "#fff", fontSize: 12 } },
  grid: { left: 62, right: 24, top: 36, bottom: 78, containLabel: false },
  legend: { bottom: 8, left: "center", textStyle: { color: chartTheme.value.legend, fontSize: 12 }, itemGap: 18 },
  xAxis: { type: "time", axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, hideOverlap: true, fontSize: 12 }, splitLine: { show: false } },
  yAxis: { type: "value", axisLine: { show: false }, axisLabel: { color: chartTheme.value.label, formatter: "{value}%" }, splitLine: { lineStyle: { color: chartTheme.value.grid } } },
  dataZoom: [{ type: "inside", start: 0, end: 100 }, { type: "slider", start: 0, end: 100, height: 22, bottom: 38, borderColor: chartTheme.value.axis, fillerColor: `${palette.value.teal}33`, handleStyle: { color: palette.value.teal }, textStyle: { color: chartTheme.value.label } }],
}));
function lineSeries(rows, code, name, color, field = "valor") {
  return { name, type: "line", showSymbol: false, connectNulls: false, lineStyle: { color, width: 2.2 }, itemStyle: { color }, data: rows.filter((row) => String(row.classificacao_codigo) === code && row[field] != null).map((row) => [row.periodo, row[field]]) };
}
function comparisonChart(series, unit = "% ao mês") {
  return computed(() => ({ ...common.value, color: colors.value, tooltip: { ...common.value.tooltip, valueFormatter: (v) => `${pretty(v, 2)}${unit}` }, series: series().filter((s) => s.data.length) }));
}
const monthlyChart = comparisonChart(() => [lineSeries(national.value, "7170", "Alimentação e bebidas", colors.value[0]), lineSeries(national.value, "7169", "IPCA geral", colors.value[2])]);
const annualChart = comparisonChart(() => [lineSeries(national.value, "7170", "Alimentação e bebidas", colors.value[0], "variacao_12_meses_percentual"), lineSeries(national.value, "7169", "IPCA geral", colors.value[2], "variacao_12_meses_percentual")], "% em 12 meses");
const ytdChart = comparisonChart(() => [lineSeries(national.value, "7170", "Alimentação e bebidas", colors.value[0], "acumulado_ano_percentual"), lineSeries(national.value, "7169", "IPCA geral", colors.value[2], "acumulado_ano_percentual")], "% acumulado no ano");
const groupChart = comparisonChart(() => [lineSeries(foodGroupRows.value, "7170", "Alimentos e bebidas", colors.value[0]), lineSeries(foodGroupRows.value, "7171", "No domicílio", colors.value[1]), lineSeries(foodGroupRows.value, "7432", "Fora do domicílio", colors.value[2])]);
const rebasedChart = computed(() => {
  const foodStart = foodRows.value[0]?.periodo;
  const generalStart = national.value.find((row) => String(row.classificacao_codigo) === "7169")?.periodo;
  const commonStart = [foodStart, generalStart].filter(Boolean).sort().at(-1);
  const make = (rows, code, name, color) => {
    let index = 100;
    const points = rows.filter((row) => String(row.classificacao_codigo) === code && row.periodo >= commonStart && row.valor != null).sort((a, b) => a.periodo.localeCompare(b.periodo));
    return { name, type: "line", showSymbol: false, lineStyle: { color, width: 2.2 }, data: points.map((row, position) => { if (position > 0) index *= 1 + row.valor / 100; return [row.periodo, index]; }) };
  };
  return { ...common.value, yAxis: { ...common.value.yAxis, axisLabel: { color: chartTheme.value.label, formatter: "{value}" } }, tooltip: { ...common.value.tooltip, valueFormatter: (v) => pretty(v, 1) }, series: [make(national.value, "7170", "Alimentos (início = 100)", colors.value[0]), make(national.value, "7169", "IPCA geral (início = 100)", colors.value[2])] };
});
const selectedProductChart = computed(() => {
  const row = products.value.find((item) => item.code === selectedProduct.value);
  const detail = national.value.filter((item) => String(item.classificacao_codigo) === selectedProduct.value);
  return { ...common.value, tooltip: { ...common.value.tooltip, valueFormatter: (v) => `${pretty(v, 2)}%` }, legend: { show: false }, series: [{ name: row?.name || "Selecione um produto", type: "line", showSymbol: false, lineStyle: { color: colors.value[0], width: 2.3 }, data: detail.filter((item) => item.valor != null).map((item) => [item.periodo, item.valor]) }] };
});
const regionalChart = computed(() => {
  const localRows = regional.value.filter((row) => String(row.territorio_codigo) === selectedAreaCode.value && ["7170", "7171", "7432"].includes(String(row.classificacao_codigo)));
  if (selectedProduct.value) {
    const productRows = regional.value.filter((row) => String(row.territorio_codigo) === selectedAreaCode.value && String(row.classificacao_codigo) === selectedProduct.value);
    const product = products.value.find((item) => item.code === selectedProduct.value);
    return { ...common.value, tooltip: { ...common.value.tooltip, valueFormatter: (v) => `${pretty(v, 2)}%` }, legend: { show: false }, series: [lineSeries(productRows, selectedProduct.value, product?.name || "Subitem", colors.value[0])] };
  }
  const selectedCategoryCodes = selectedGroup.value === "11" ? ["7171"] : selectedGroup.value === "12" ? ["7432"] : ["7170", "7171", "7432"];
  const names = { "7170": "Alimentação e bebidas", "7171": "No domicílio", "7432": "Fora do domicílio" };
  return { ...common.value, tooltip: { ...common.value.tooltip, valueFormatter: (v) => `${pretty(v, 2)}%` }, series: selectedCategoryCodes.map((code, index) => lineSeries(localRows, code, names[code], colors.value[index])) };
});
const latestProducts = computed(() => {
  const detail = national.value.filter((row) => row.classificacao_caminho && String(row.classificacao_caminho).length >= 7 && /^[12]/.test(String(row.classificacao_caminho)));
  const latestPeriod = [...detail].map((row) => row.periodo).sort().at(-1);
  return detail.filter((row) => row.periodo === latestPeriod && row.valor != null && (!selectedGroup.value || String(row.classificacao_caminho).startsWith(selectedGroup.value))).sort((a, b) => b.valor - a.valor);
});
const rankingChart = computed(() => {
  const top = latestProducts.value.filter((row) => row[rankMetric.value] != null).sort((a, b) => b[rankMetric.value] - a[rankMetric.value]).slice(0, 8);
  const bottom = latestProducts.value.filter((row) => row[rankMetric.value] != null).sort((a, b) => a[rankMetric.value] - b[rankMetric.value]).slice(0, 8);
  const rows = [...top, ...bottom.filter((row) => !top.includes(row))].sort((a, b) => a[rankMetric.value] - b[rankMetric.value]);
  return { ...common.value, grid: { left: 190, right: 30, top: 26, bottom: 40 }, legend: { show: false }, xAxis: { type: "value", axisLabel: { color: chartTheme.value.label, formatter: "{value}%" }, splitLine: { lineStyle: { color: chartTheme.value.grid } } }, yAxis: { type: "category", data: rows.map((row) => row.classificacao), axisLabel: { color: chartTheme.value.label, width: 160, overflow: "break", fontSize: 11 } }, tooltip: { ...common.value.tooltip, trigger: "item", valueFormatter: (v) => `${pretty(v, 2)}%` }, series: [{ name: "Variação", type: "bar", barMaxWidth: 20, itemStyle: { color: (params) => params.value < 0 ? colors.value[2] : colors.value[0], borderRadius: [0, 3, 3, 0] }, data: rows.map((row) => row[rankMetric.value]) }] };
});
const seasonalChart = computed(() => {
  const map = Array.from({ length: 12 }, () => []);
  foodRows.value.forEach((row) => { if (row.valor != null) map[Number(row.periodo.slice(5, 7)) - 1].push(row.valor); });
  return { ...common.value, xAxis: { type: "category", data: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], axisLabel: { color: chartTheme.value.label } }, yAxis: { ...common.value.yAxis, name: "Média da variação mensal (%)" }, dataZoom: [], legend: { show: false }, series: [{ name: "Média histórica", type: "bar", barMaxWidth: 34, itemStyle: { color: colors.value[1], borderRadius: [4, 4, 0, 0] }, data: map.map((values) => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null) }] };
});
const diffusionChart = computed(() => {
  const period = latestFood.value?.periodo;
  const rows = national.value.filter((row) => row.periodo === period && row.classificacao_caminho && String(row.classificacao_caminho).length >= 7 && /^[12]/.test(String(row.classificacao_caminho)) && row.valor != null);
  const buckets = [{ label: "Queda acima de 1%", count: 0 }, { label: "Queda até 1%", count: 0 }, { label: "Estável (±0,1%)", count: 0 }, { label: "Alta até 1%", count: 0 }, { label: "Alta acima de 1%", count: 0 }];
  rows.forEach((row) => { const v = row.valor; const i = v < -1 ? 0 : v < -0.1 ? 1 : v <= 0.1 ? 2 : v <= 1 ? 3 : 4; buckets[i].count += 1; });
  return { ...common.value, xAxis: { type: "category", data: buckets.map((item) => item.label), axisLabel: { color: chartTheme.value.label, interval: 0, rotate: 15, fontSize: 11 } }, yAxis: { type: "value", axisLabel: { color: chartTheme.value.label }, splitLine: { lineStyle: { color: chartTheme.value.grid } } }, dataZoom: [], legend: { show: false }, tooltip: { ...common.value.tooltip, trigger: "item", valueFormatter: (value) => `${value} subitens` }, series: [{ name: "Subitens", type: "bar", barMaxWidth: 38, itemStyle: { color: colors.value[3], borderRadius: [4, 4, 0, 0] }, data: buckets.map((item) => item.count) }] };
});
const latestChange = computed(() => latestFood.value?.valor);
const source = computed(() => foodData.value?.source);
let regionalObserver;
function observeRegionalPanel() {
  if (regionalPanel.value && regionalObserver) regionalObserver.observe(regionalPanel.value);
}
onMounted(() => {
  if (!("IntersectionObserver" in window)) {
    state.loadFoodRegionalData();
    return;
  }
  regionalObserver = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      state.loadFoodRegionalData();
      regionalObserver.disconnect();
    }
  }, { rootMargin: "360px 0px" });
  observeRegionalPanel();
});
watch(foodData, async () => {
  await nextTick();
  observeRegionalPanel();
}, { flush: "post" });
onBeforeUnmount(() => regionalObserver?.disconnect());
</script>

<template>
  <section class="content inner-content">
    <div v-if="foodLoading || !foodData" class="loading-screen" role="status"><span class="spinner"></span><p>Carregando as séries oficiais do IPCA…</p></div>
    <template v-else>
      <div class="page-intro"><div><div class="eyebrow"><span></span> IPCA · IBGE E BANCO CENTRAL</div><h1 tabindex="-1">Inflação dos alimentos.<br /><em>O preço de comer.</em></h1><p>Variações dos preços ao consumidor, comparações com o IPCA geral, produtos, sazonalidade e áreas pesquisadas. A série longa de alimentação cobre {{ source.period_start }} a {{ source.period_end }}.</p></div><aside>ÚLTIMO MÊS DISPONÍVEL<strong>{{ latestFood?.periodo }}</strong><small>Alimentos {{ percent(latestChange) }} · coleta {{ source.collected_at.slice(0, 10) }}</small></aside></div>
      <div class="stacked-panels">
        <article class="panel"><div class="panel-heading"><div><span class="kicker">{{ source.period_start }} — {{ source.period_end }} · VARIAÇÃO MENSAL</span><h3>Alimentos e IPCA geral</h3></div><span class="unit-pill">Percentual no mês</span></div><TrendChart :option="monthlyChart" :guide="chartGuides.foodInflation" height="405px"/><p class="panel-caption">A série de alimentação começa em 1991 pelo SGS do Banco Central; as classificações detalhadas do SIDRA começam em 1999 e têm tabelas sucessivas.</p></article>
        <div class="metrics">
          <article class="metric metric-blue"><div class="metric-label">ALIMENTAÇÃO E BEBIDAS · MÊS</div><strong>{{ percent(latestChange) }}</strong><div class="metric-foot"><span>{{ latestFood?.periodo }}</span><i>Variação mensal IPCA</i></div></article>
          <article class="metric metric-teal"><div class="metric-label">ALIMENTAÇÃO · 12 MESES</div><strong>{{ percent(latestFood?.variacao_12_meses_percentual) }}</strong><div class="metric-foot"><span>Composição de 12 taxas mensais</span><i>IBGE/BCB · derivado</i></div></article>
          <article class="metric metric-gold"><div class="metric-label">SUBITENS ALIMENTARES</div><strong>{{ products.length }}</strong><div class="metric-foot"><span>Classificação do IPCA</span><i>Detalhe nacional</i></div></article>
          <article class="metric metric-red"><div class="metric-label">ÁREAS IPCA</div><strong>{{ territories.length }}</strong><div class="metric-foot"><span>Municípios e regiões metropolitanas</span><i>Pesquisa do IBGE</i></div></article>
        </div>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">COMPOSIÇÃO DAS VARIAÇÕES MENSAIS</span><h3>Inflação acumulada em 12 meses</h3></div><span class="unit-pill">Percentual · composto</span></div><TrendChart :option="annualChart" :guide="chartGuides.foodInflation" height="385px"/><p class="panel-caption">Calculado por multiplicação dos fatores mensais dos últimos doze meses. A taxa anual não é a soma simples das variações.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">JANEIRO ATÉ O ÚLTIMO MÊS DISPONÍVEL</span><h3>Inflação acumulada no ano</h3></div><span class="unit-pill">Percentual · composto</span></div><TrendChart :option="ytdChart" :guide="chartGuides.foodInflation" height="380px"/><p class="panel-caption">Compara a inflação acumulada desde janeiro em cada ano. O ano corrente aparece parcial e as taxas são compostas dentro do ano-calendário.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">ÍNDICE RELATIVO · BASE 100 NO INÍCIO DA SÉRIE</span><h3>Trajetória acumulada dos preços</h3></div><span class="unit-pill">Índice rebaseado</span></div><TrendChart :option="rebasedChart" :guide="chartGuides.foodInflation" height="385px"/><p class="panel-caption">O primeiro ponto de cada série é fixado em 100. O índice compara ritmos acumulados, não informa preço em reais nem garante cesta idêntica entre os períodos.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">GRUPOS ALIMENTARES · DESDE 1999</span><h3>Em casa e fora de casa</h3></div><span class="unit-pill">Variação mensal</span></div><TrendChart :option="groupChart" :guide="chartGuides.foodInflation" height="385px"/><p class="panel-caption">A classificação detalha alimentação no domicílio e fora do domicílio. As séries refletem os pesos e a cesta do IPCA em cada período.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">DETALHE NACIONAL · SÉRIE POR SUBITEM</span><h3>Explore um produto</h3></div><div class="food-filters"><label class="unit-pill">Grupo <select v-model="selectedGroup" aria-label="Filtrar grupo de alimentos"><option value="">Todos os alimentos</option><option value="11">No domicílio</option><option value="12">Fora do domicílio</option></select></label><label class="unit-pill">Produto <select v-model="selectedProduct" aria-label="Selecionar produto alimentar"><option value="">Selecione um subitem</option><option v-for="item in productOptions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label></div></div><TrendChart v-if="selectedProduct" :option="selectedProductChart" :guide="chartGuides.foodInflation" height="380px"/><p v-else class="panel-caption">Escolha um grupo e um subitem para ver sua variação mensal. A série segue a disponibilidade histórica e a classificação do IBGE.</p></article>
        <article ref="regionalPanel" class="panel"><div class="panel-heading"><div><span class="kicker">COMPARAÇÃO GEOGRÁFICA · ÁREAS IPCA</span><h3>Inflação de alimentos por área</h3></div><div class="food-filters"><label class="unit-pill">Localidade <select v-model="area" aria-label="Selecionar área do IPCA"><option v-for="item in territories" :key="item.code" :value="item.code">{{ item.name }}</option></select></label><label class="unit-pill">Grupo <select v-model="selectedGroup" aria-label="Filtrar grupo na área"><option value="">Todos</option><option value="11">No domicílio</option><option value="12">Fora do domicílio</option></select></label><label class="unit-pill">Produto <select v-model="selectedProduct" aria-label="Selecionar produto para a área"><option value="">Grupos</option><option v-for="item in productOptions" :key="item.code" :value="item.code">{{ item.name }}</option></select></label></div></div><TrendChart v-if="foodRegionalData" :option="regionalChart" :guide="chartGuides.foodInflation" height="385px"/><div v-else-if="foodRegionalLoading" class="chart-loading" role="status">Carregando as observações regionais do IPCA…</div><button v-else class="chart-load-button" type="button" @click="state.loadFoodRegionalData()">Carregar comparação regional</button><p class="panel-caption">Área selecionada: {{ selectedAreaName }}. A lista segue as áreas e níveis territoriais publicados pelo IPCA; produtos detalhados estão disponíveis desde 2020 e podem variar por área.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">ÚLTIMA OBSERVAÇÃO DETALHADA · {{ latestProducts.at(-1)?.periodo }}</span><h3>Maiores altas e quedas por produto</h3></div><div class="food-filters"><label class="unit-pill">Período <select v-model="rankMetric" aria-label="Período do ranking"><option value="valor">No mês</option><option value="acumulado_ano_percentual">No ano</option><option value="variacao_12_meses_percentual">Em 12 meses</option></select></label><label class="unit-pill">Grupo <select v-model="selectedGroup" aria-label="Filtrar ranking por grupo"><option value="">Todos os alimentos</option><option value="11">No domicílio</option><option value="12">Fora do domicílio</option></select></label></div></div><TrendChart :option="rankingChart" :guide="chartGuides.foodInflation" height="470px"/><p class="panel-caption">Mostra até oito maiores altas e oito maiores quedas entre subitens nacionais para o período selecionado. Sem os pesos da cesta, o ranking não mede contribuição à inflação.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">PADRÕES DE CALENDÁRIO · HISTÓRICO DISPONÍVEL</span><h3>Sazonalidade média por mês</h3></div><span class="unit-pill">Média das variações</span></div><TrendChart :option="seasonalChart" :guide="chartGuides.foodInflation" height="365px"/><p class="panel-caption">Média aritmética das taxas mensais de alimentação e bebidas em cada mês do calendário. É uma descrição do passado, não previsão nem ajuste sazonal oficial.</p></article>
        <article class="panel"><div class="panel-heading"><div><span class="kicker">DISPERSÃO DOS SUBITENS · {{ latestFood?.periodo }}</span><h3>Quantos subiram e quantos caíram?</h3></div><span class="unit-pill">Contagem de itens</span></div><TrendChart :option="diffusionChart" :guide="chartGuides.foodInflation" height="365px"/><p class="panel-caption">Contagem de subitens nas faixas de variação mensal. Cada subitem conta uma vez; isso não considera seu peso no IPCA.</p></article>
        <article class="panel methods"><div class="panel-heading"><div><span class="kicker">MÉTRICAS, FONTES E LIMITES</span><h3>Como ler os preços dos alimentos</h3></div></div>
          <div class="method-row"><span>01</span><div><strong>Inflação não é preço em reais</strong><p>O IPCA mede variações relativas de preços ao consumidor e índices ponderados. Não é uma série de preço por quilo/unidade e não permite converter uma taxa em preço de varejo fictício.</p></div></div>
          <div class="method-row"><span>02</span><div><strong>Séries longas e classificação</strong><p>Para o grupo alimentação, a série do SGS 1635 começa em 1991; as tabelas do SIDRA detalham grupos desde 1999 em tabelas sucessivas (655, 2938, 1419 e 7060). Produtos e áreas detalhadas da tabela atual têm janela mais curta. Mudanças de classificação e ponderação devem ser consideradas.</p></div></div>
          <div class="method-row"><span>03</span><div><strong>Acumulados e índice rebaseado</strong><p>Acumulados compõem fatores mensais: (1 + taxa₁) × … × (1 + taxaₙ) − 1. O índice rebaseado encadeia as taxas e define 100 no primeiro ponto comparável; comparar inclinações não equivale a comparar preços absolutos.</p></div></div>
          <div class="method-row"><span>04</span><div><strong>Áreas pesquisadas</strong><p>A comparação regional usa apenas localidades e níveis territoriais presentes na pesquisa IPCA. Não representa o conjunto de municípios do Brasil. Os dados podem ser revisados e pesos variam ao longo do tempo.</p></div></div>
          <div class="method-row"><span>05</span><div><strong>Fontes e reprodução</strong><p>Dados consultados em {{ source.collected_at }}. Respostas brutas preservadas em <code>data/raw/ibge/</code> e tabelas tratadas em <code>data/processed/</code>. O pacote do site é local e não faz chamadas externas durante a navegação.</p><a href="https://sidra.ibge.gov.br/tabela/7060" target="_blank" rel="noreferrer">IBGE/SIDRA — tabela 7060 <ExternalLink class="ui-icon" :size="12" /></a> · <a href="https://api.bcb.gov.br/dados/serie/bcdata.sgs.1635/dados?formato=json" target="_blank" rel="noreferrer">BCB — SGS 1635 <ExternalLink class="ui-icon" :size="12" /></a></div></div>
        </article>
        <article class="panel data-jump"><div><span class="kicker">DADOS PARA REPRODUÇÃO</span><h3>Explore as observações do IPCA</h3><p>Variações por período, grupo, subitem e área geográfica. Confira as colunas de unidade e classificação no explorador.</p></div><div class="food-filters"><button @click="activeData = 'foodInflationNational'; go('explorer')">Dados nacionais <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button><button @click="activeData = 'foodInflationRegional'; go('explorer')">Dados regionais <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></div></article>
      </div>
    </template>
  </section>
</template>
