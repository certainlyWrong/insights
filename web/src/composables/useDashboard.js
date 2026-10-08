import { computed, markRaw, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Papa from "papaparse";
import { createChartOptions } from "../charts/chartOptions.js";
import { chartGuides } from "../content/chartGuides.js";
import {
  BookOpenText, ChartColumnIncreasing, ChartNoAxesCombined, CircleDollarSign,
  HeartHandshake, House, Landmark, Percent, ReceiptText, Search,
} from "@lucide/vue";
import dashboardUrl from "../assets/data/dashboard.json.gz?url";
import titlesUrl from "../assets/data/posicoes_por_titulo.csv.gz?url";

export function useDashboard() {

const menu = markRaw([
  { id: "overview", label: "Visão geral", path: "/", icon: House },
  { id: "debt", label: "Dívida pública", path: "/divida-publica", icon: Landmark },
  { id: "interest", label: "Juros da dívida", path: "/juros-da-divida", icon: Percent },
  { id: "pib", label: "PIB", path: "/pib", icon: ChartNoAxesCombined },
  { id: "purchasingPower", label: "Poder de compra", path: "/poder-de-compra", icon: CircleDollarSign },
  { id: "taxes", label: "Impostômetro", path: "/impostos", icon: ReceiptText },
  { id: "spending", label: "Orçamento federal", path: "/orcamento-federal", icon: ChartColumnIncreasing },
  { id: "social", label: "Programas sociais", path: "/programas-sociais", icon: HeartHandshake },
  { id: "explorer", label: "Explorar dados", path: "/explorar-dados", icon: Search },
  { id: "sources", label: "Fontes e método", path: "/fontes-e-metodo", icon: BookOpenText },
]);
const route = useRoute();
const router = useRouter();
const page = computed(() => route.meta.page || "notFound");
const theme = ref("light");
const pibPeriod = ref("quarterly");
const data = ref(null);
const error = ref("");
const activeData = ref("monthly");
const search = ref("");
const pageNumber = ref(1);
const pageSize = 25;
const detailRows = ref([]);
const detailCsv = ref("");
const detailLoading = ref(false);
const detailLoaded = ref(false);
const palette = {
  get ink() { return ({ dark: "#9fc4df", coffee: "#765033", forest: "#286b56" })[theme.value] || "#20394f"; },
  get teal() { return ({ dark: "#58c2b0", coffee: "#a76532", forest: "#3d8a65" })[theme.value] || "#188984"; },
  get coral() { return ({ dark: "#ef927d", coffee: "#c46b50", forest: "#c27653" })[theme.value] || "#d76e58"; },
  get gold() { return ({ dark: "#e5bd68", coffee: "#c08a3d", forest: "#b69749" })[theme.value] || "#c89c46"; },
  get slate() { return ({ dark: "#aab8c1", coffee: "#8d7968", forest: "#74877a" })[theme.value] || "#8e9da7"; },
};
const chartTheme = computed(() => {
  const presets = {
    light: { label: "#80909a", legend: "#657588", axis: "#e6e9e7", grid: "#edf0ee", tooltip: "#142b40", pointer: "#9baab4" },
    dark: { label: "#aebbc3", legend: "#b7c3ca", axis: "#3b4a55", grid: "#2a3741", tooltip: "#0c141c", pointer: "#8295a2" },
    coffee: { label: "#705a48", legend: "#604832", axis: "#d8c8b4", grid: "#e9ddcd", tooltip: "#4a3427", pointer: "#a1805b" },
    forest: { label: "#536b5b", legend: "#405b48", axis: "#cbd8cb", grid: "#dce6dc", tooltip: "#23392d", pointer: "#76937b" },
  };
  return presets[theme.value] || presets.light;
});

const debtLatest = computed(() => data.value?.debt.monthly.at(-1));
const interestLatest = computed(() => data.value?.debt.interest.monthly.at(-1));
const interestAnnualLast = computed(() => data.value?.debt.interest.annual.at(-1));
const completeInterestYears = computed(() => (data.value?.debt.interest.annual || []).filter((r) => r.custo_implicito_aproximado_percentual != null));
const latestInterestYear = computed(() => completeInterestYears.value.at(-1));
const previousInterestYear = computed(() => completeInterestYears.value.at(-2));
const interestYearChange = computed(() => latestInterestYear.value && previousInterestYear.value
  ? 100 * (latestInterestYear.value.juros_dpf_bilhoes / previousInterestYear.value.juros_dpf_bilhoes - 1)
  : null);
const cumulativeInterest = computed(() => completeInterestYears.value.reduce((total, row) => total + row.juros_dpf_bilhoes, 0));
const macroLatest = computed(() => [...(data.value?.debt.macro || [])].reverse().find((r) => r.dbgg_percentual_pib != null));
const latestYear = computed(() => Math.max(...(data.value?.spending || []).map((r) => r.ano)));
const spendingLatest = computed(() => data.value?.spending.filter((r) => r.ano === latestYear.value) || []);
const spendByFunction = computed(() => Object.fromEntries(spendingLatest.value.map((r) => [r.funcao.trim(), r])));
const socialLatest = computed(() => data.value?.social?.bpc_annual.at(-1));
const bpcPrevious = computed(() => data.value?.social?.bpc_annual.at(-2));
const bpcGrowth = computed(() => socialLatest.value && bpcPrevious.value ? 100 * (socialLatest.value.beneficiarios_total / bpcPrevious.value.beneficiarios_total - 1) : null);
const bpcRepassePerBeneficiary = computed(() => socialLatest.value ? socialLatest.value.repasse_total_brl / socialLatest.value.beneficiarios_total : null);
const pibQuarterly = computed(() => data.value?.pib?.quarterly || []);
const pibLatest = computed(() => pibQuarterly.value.at(-1));
const pibPrevious = computed(() => pibQuarterly.value.at(-2));
const pibSameQuarterLastYear = computed(() => pibQuarterly.value.length >= 5 ? pibQuarterly.value.at(-5) : null);
const pibLatestAggregate = computed(() => (data.value?.pib?.aggregates || []).filter((r) => r.tipo_periodo === "ano" && r.periodo_completo).at(-1));
const pibNominalGrowth = computed(() => {
  const index = pibQuarterly.value.length - 5;
  const prior = index >= 0 ? pibQuarterly.value[index] : null;
  return prior && pibLatest.value?.pib_nominal_milhoes && prior.pib_nominal_milhoes
    ? 100 * (pibLatest.value.pib_nominal_milhoes / prior.pib_nominal_milhoes - 1) : null;
});
const taxMonthly = computed(() => data.value?.taxes?.monthly || []);
const taxLatest = computed(() => taxMonthly.value.at(-1));
const taxAnnualRunning = computed(() => taxLatest.value?.acumulado_ano_milhoes);
const taxYoy = computed(() => taxLatest.value?.variacao_nominal_12_meses_percentual);
const taxGeneralLatest = computed(() => (data.value?.taxes?.general_annual || []).at(-1));
const purchasingPowerRows = computed(() => data.value?.purchasing_power?.monthly || []);
const purchasingPowerLatest = computed(() => purchasingPowerRows.value.at(-1));
const deflatorByYear = computed(() => {
  if (!data.value) return {};
  const months = data.value.debt.macro.filter((r) => r.ipca_variacao_mensal_percentual != null).slice().sort((a, b) => a.data.localeCompare(b.data));
  const annual = {};
  let index = 1;
  for (const row of months) {
    index *= 1 + row.ipca_variacao_mensal_percentual / 100;
    const year = row.data.slice(0, 4);
    annual[year] ||= [];
    annual[year].push(index);
  }
  const means = Object.fromEntries(Object.entries(annual).map(([year, values]) => [year, values.reduce((a, b) => a + b, 0) / values.length]));
  return Object.fromEntries(Object.entries(means).map(([year, value]) => [year, means["2025"] / value]));
});
function realFactor(year) { return deflatorByYear.value[String(year)] || 1; }
function pretty(value, digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? "—" : new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
}
function tri(value) { return value == null ? "—" : pretty(value / 1000, 2); }
function percent(value) { return value == null ? "—" : pretty(value, 2) + "%"; }
function month(value) {
  if (!value) return "—";
  const [year, m] = value.split("-");
  return m + "/" + year;
}
const navLabel = computed(() => menu.find((item) => item.id === page.value)?.label || "Página não encontrada");
function includesChartStart() { return true; }

const datasets = computed(() => {
  if (!data.value) return {};
  const d = data.value;
  return {
    monthly: { label: "Estoque mensal da DPF", rows: d.debt.monthly },
    composition: { label: "Componentes históricos do estoque", rows: d.debt.composition },
    macro: { label: "Indicadores do Banco Central", rows: d.debt.macro },
    factors: { label: "Fatores de variação da DPF", rows: d.debt.factors },
    interestMonthly: { label: "Juros apropriados mensais da DPF", rows: d.debt.interest.monthly },
    interestAnnual: { label: "Juros apropriados anuais da DPF", rows: d.debt.interest.annual },
    flows: { label: "Emissões e resgates", rows: d.debt.flows },
    holdings: { label: "Estoque por carteira e tipo", rows: d.debt.holdings },
    spending: { label: "Execução do orçamento por função", rows: d.spending },
    bpcAnnual: { label: "BPC — série histórica anual", rows: d.social.bpc_annual },
    social2024: { label: "Programas sociais — comparação 2024", rows: d.social.comparison_2024 },
    pibQuarterly: { label: "PIB — série trimestral do IBGE", rows: d.pib.quarterly },
    pibAggregates: { label: "PIB — agregações semestrais e anuais", rows: d.pib.aggregates },
    taxesMonthly: { label: "Impostos — arrecadação federal mensal", rows: d.taxes.monthly },
    taxesAnnual: { label: "Impostos — arrecadação federal anual", rows: d.taxes.annual },
    taxBurdenAnnual: { label: "Carga tributária bruta — governo geral", rows: d.taxes.general_annual },
    purchasingPowerMonthly: { label: "IPCA e poder de compra do real — série mensal", rows: d.purchasing_power.monthly },
    titles: { label: "Posições individuais por título", rows: detailRows.value },
  };
});
const dataset = computed(() => datasets.value[activeData.value] || { label: "", rows: [] });
const datasetDescriptions = {
  monthly: ["Estoque mensal da Dívida Pública Federal em poder do público, em valores nominais.", "Tesouro Nacional — Estoque da DPF"],
  composition: ["Componentes históricos que explicam a composição do estoque da dívida federal.", "Tesouro Nacional — Estoque da DPF"],
  macro: ["Indicadores mensais de dívida bruta e líquida do Governo Geral em relação ao PIB.", "Banco Central — Séries SGS"],
  factors: ["Fatores mensais que explicam a variação do estoque da DPF.", "Tesouro Nacional — Fatores de variação da DPF"],
  interestMonthly: ["Juros apropriados por competência na dívida pública federal.", "Tesouro Nacional — Fatores de variação da DPF"],
  interestAnnual: ["Soma anual dos juros apropriados; taxas aproximadas são calculadas somente para anos completos.", "Tesouro Nacional — Fatores de variação da DPF"],
  flows: ["Emissões e resgates de títulos da Dívida Pública Federal.", "Tesouro Nacional — Emissões e resgates"],
  holdings: ["Composição da dívida por carteira e tipo de título.", "Tesouro Nacional — Estoque da DPF"],
  spending: ["Pagamentos federais por função orçamentária, com os valores tratados em reais de 2025.", "SIOP — Dados Abertos do Orçamento"],
  bpcAnnual: ["Série anual de beneficiários e repasses do Benefício de Prestação Continuada.", "MDS/SAGICAD — VIS DATA"],
  social2024: ["Comparação contextual de valores de programas sociais em 2024; unidades de cobertura diferem.", "MDS — Balanço do Bolsa Família 2024"],
  pibQuarterly: ["Contas Nacionais Trimestrais, com valores correntes e métricas de volume do PIB.", "IBGE/SIDRA — Contas Nacionais Trimestrais"],
  pibAggregates: ["Agregações semestrais e anuais do PIB; períodos incompletos permanecem identificados.", "IBGE/SIDRA — Contas Nacionais Trimestrais"],
  taxesMonthly: ["Arrecadação federal mensal nominal e acumulados dos meses publicados.", "Receita Federal — Arrecadação federal"],
  taxesAnnual: ["Soma anual da arrecadação federal, sem correção pela inflação.", "Receita Federal — Arrecadação federal"],
  taxBurdenAnnual: ["Carga tributária bruta anual das esferas federal, estadual e municipal.", "Tesouro Nacional — Carga Tributária do Governo Geral"],
  purchasingPowerMonthly: ["Variação mensal do IPCA e índice de preços acumulado desde julho de 1994.", "Banco Central/IBGE — IPCA mensal"],
  titles: ["Posições individuais por título e vencimento; a série completa é carregada sob demanda.", "Tesouro Nacional — Estoque da DPF"],
};
const datasetInfo = computed(() => {
  const [description, sourceName] = datasetDescriptions[activeData.value] || ["Tabela processada para este painel.", ""];
  const source = data.value?.sources.find((entry) => entry.name.startsWith(sourceName));
  return { description, source };
});
const columns = computed(() => dataset.value.rows.length ? Object.keys(dataset.value.rows[0]) : []);
const knownColumnLabels = {
  data: "Data de referência", ano: "Ano", mes: "Mês", trimestre: "Trimestre", semestre: "Semestre",
  periodo: "Período", tipo_periodo: "Tipo de período", indicador: "Indicador", funcao: "Função orçamentária",
  dpf_bilhoes: "DPF (R$ bilhões)", dpmfi_bilhoes: "DPMFi (R$ bilhões)", dpfe_bilhoes: "DPFe (R$ bilhões)",
  valor_r_bilhoes: "Valor (R$ bilhões)", despesa_paga_r$: "Despesa paga (R$)", gnd4_investimento_pago_r$: "Investimentos GND 4 pagos (R$)",
  governo_geral_percentual_pib: "Governo Geral (% do PIB)", beneficiarios_total: "Beneficiários (pessoas)",
  arrecadacao_total_federal_milhoes: "Arrecadação federal (R$ milhões)", periodo_completo: "Período completo",
};
function columnLabel(key) {
  if (knownColumnLabels[key]) return knownColumnLabels[key];
  const words = key.replaceAll("_", " ").replace(/(^| )r\$/gi, "$1R$").split(" ").map((word) => {
    const normalized = word.toLocaleLowerCase("pt-BR");
    const terms = {
      dpf: "DPF", dpmfi: "DPMFi", dpfe: "DPFe", dbgg: "DBGG", dlgg: "DLGG", pib: "PIB", ipca: "IPCA", sgs: "SGS",
      bilhoes: "bilhões", milhoes: "milhões", variacao: "variação", arrecadacao: "arrecadação", beneficiarios: "beneficiários",
      indice: "índice", preco: "preço", mes: "mês", percentual: "%", r$: "R$",
    };
    return terms[normalized] || normalized;
  });
  return words.map((word, index) => index === 0 && !/^(R\$|DPF|DPMFi|DPFe|DBGG|DLGG|PIB|IPCA|SGS)$/.test(word)
    ? word.charAt(0).toLocaleUpperCase("pt-BR") + word.slice(1)
    : word).join(" ");
}
const filteredRows = computed(() => {
  const q = search.value.trim().toLocaleLowerCase("pt-BR");
  return q ? dataset.value.rows.filter((row) => Object.values(row).some((value) => String(value ?? "").toLocaleLowerCase("pt-BR").includes(q))) : dataset.value.rows;
});
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize)));
const visibleRows = computed(() => filteredRows.value.slice((pageNumber.value - 1) * pageSize, pageNumber.value * pageSize));

const { tooltip, baseXAxis, baseYAxis, debtChart, macroChart, factorsChart, interestChart, spendingChart, spendingTrend, capitalTrend, overviewTrend, socialCoverageChart, socialSpendChart, pibNominalChart, pibGrowthRows, pibRateField, pibGrowthChart, pibSpendingChart, taxMonthlyChart, taxBurdenChart, purchasingPowerChart } = createChartOptions({ data, chartTheme, palette, includesChartStart, pretty, percent, realFactor, pibPeriod, pibQuarterly, taxMonthly, purchasingPowerRows });

function initTheme() {
  const saved = localStorage.getItem("insights-theme");
  const validThemes = ["light", "dark", "coffee", "forest"];
  theme.value = validThemes.includes(saved) ? saved : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = theme.value;
}
function setTheme(value) {
  if (!["light", "dark", "coffee", "forest"].includes(value)) return;
  theme.value = value;
  document.documentElement.dataset.theme = theme.value;
  localStorage.setItem("insights-theme", theme.value);
}

async function readAssetText(response) {
  const bytes = await response.arrayBuffer();
  const signature = new Uint8Array(bytes, 0, Math.min(2, bytes.byteLength));

  // GitHub Pages serves .gz as application/gzip without Content-Encoding.
  // In that case Fetch returns the compressed bytes, unlike Vite's dev server.
  if (signature[0] === 0x1f && signature[1] === 0x8b) {
    if (!("DecompressionStream" in window)) {
      throw new Error("Este navegador não oferece suporte à leitura dos dados compactados.");
    }
    const decompressed = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Response(decompressed).text();
  }

  // When a server sends Content-Encoding: gzip, Fetch decodes the response
  // before exposing it here, so the bytes already contain the original text.
  return new TextDecoder("utf-8").decode(bytes);
}

async function loadData() {
  try {
    const response = await fetch(dashboardUrl);
    if (!response.ok) throw new Error(`A base local não foi encontrada (HTTP ${response.status}).`);
    data.value = JSON.parse(await readAssetText(response));
    const requestedDataset = String(route.query.dataset || "");
    if (requestedDataset && datasets.value[requestedDataset]) activeData.value = requestedDataset;
  } catch (e) {
    error.value = location.protocol === "file:"
      ? "Abra o painel por um servidor web. Na pasta web, execute npm run dev e acesse o endereço exibido no terminal."
      : `Não foi possível ler os dados do painel: ${e.message}. Atualize a página; se o problema persistir após uma nova publicação, confira o pacote em web/src/assets/data/.`;
  }
}
async function loadTitles() {
  if (detailLoaded.value || detailLoading.value) return;
  detailLoading.value = true;
  try {
    const response = await fetch(titlesUrl);
    if (!response.ok) throw new Error(`O arquivo de títulos não foi encontrado (HTTP ${response.status}).`);
    detailCsv.value = await readAssetText(response);
    detailRows.value = Papa.parse(detailCsv.value, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;
    detailLoaded.value = true;
  } catch (e) {
    error.value = e.message;
  } finally {
    detailLoading.value = false;
  }
}
watch(activeData, async (value) => {
  search.value = "";
  pageNumber.value = 1;
  if (page.value === "explorer") {
    const query = value === "monthly" ? {} : { dataset: value };
    router.replace({ name: "explorer", query });
  }
  if (value === "titles") await loadTitles();
});
watch(search, () => { pageNumber.value = 1; });
function go(id) {
  const item = menu.find((entry) => entry.id === id);
  if (!item) return;
  const query = id === "explorer" && activeData.value !== "monthly" ? { dataset: activeData.value } : {};
  router.push({ name: id, query });
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function exportTable() {
  if (activeData.value === "titles") {
    const url = URL.createObjectURL(new Blob(["\ufeff", detailCsv.value], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = "posicoes_por_titulo.csv"; a.click(); URL.revokeObjectURL(url); return;
  }
  const header = columns.value.map(csvEscape).join(",");
  const body = dataset.value.rows.map((row) => columns.value.map((key) => csvEscape(row[key])).join(","));
  const url = URL.createObjectURL(new Blob(["\ufeff", [header, ...body].join("\r\n")], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = activeData.value + ".csv"; a.click(); URL.revokeObjectURL(url);
}
function csvEscape(value) { return '"' + String(value ?? "").replaceAll('"', '""') + '"'; }
onMounted(() => {
  initTheme();
  loadData();
});
  return {
    menu,
    page,
    theme,
    pibPeriod,
    data,
    error,
    activeData,
    search,
    pageNumber,
    pageSize,
    detailRows,
    detailCsv,
    detailLoading,
    detailLoaded,
    palette,
    chartTheme,
    debtLatest,
    interestLatest,
    interestAnnualLast,
    completeInterestYears,
    latestInterestYear,
    previousInterestYear,
    interestYearChange,
    cumulativeInterest,
    macroLatest,
    latestYear,
    spendingLatest,
    spendByFunction,
    socialLatest,
    bpcPrevious,
    bpcGrowth,
    bpcRepassePerBeneficiary,
    pibQuarterly,
    pibLatest,
    pibPrevious,
    pibSameQuarterLastYear,
    pibLatestAggregate,
    pibNominalGrowth,
    taxMonthly,
    taxLatest,
    taxAnnualRunning,
    taxYoy,
    taxGeneralLatest,
    purchasingPowerRows,
    purchasingPowerLatest,
    deflatorByYear,
    realFactor,
    pretty,
    tri,
    percent,
    month,
    navLabel,
    includesChartStart,
    datasets,
    dataset,
    datasetDescriptions,
    datasetInfo,
    columns,
    knownColumnLabels,
    columnLabel,
    filteredRows,
    totalPages,
    visibleRows,
    debtChart,
    macroChart,
    factorsChart,
    interestChart,
    spendingChart,
    spendingTrend,
    capitalTrend,
    overviewTrend,
    socialCoverageChart,
    socialSpendChart,
    pibNominalChart,
    pibGrowthRows,
    pibRateField,
    pibGrowthChart,
    pibSpendingChart,
    taxMonthlyChart,
    taxBurdenChart,
    purchasingPowerChart,
    chartGuides,
    initTheme,
    setTheme,
    readAssetText,
    loadData,
    loadTitles,
    go,
    exportTable,
    csvEscape
  };
}
