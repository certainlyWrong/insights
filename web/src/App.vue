<script setup>
import { computed, onMounted, ref, watch } from "vue";
import Papa from "papaparse";
import TrendChart from "./components/TrendChart.vue";
import {
  ArrowLeft, ArrowRight, ArrowUpRight, BadgeCheck, BookOpenText, ChartColumnIncreasing,
  ChartNoAxesCombined, CircleDollarSign, Download, ExternalLink, HeartHandshake, House, Info, Landmark,
  Moon, Percent, ReceiptText, Search, Sun,
} from "@lucide/vue";
import dashboardUrl from "./assets/data/dashboard.json.gz?url";
import titlesUrl from "./assets/data/posicoes_por_titulo.csv.gz?url";

const menu = [
  ["overview", "Visão geral", House],
  ["debt", "Dívida pública", Landmark],
  ["interest", "Juros da dívida", Percent],
  ["pib", "PIB", ChartNoAxesCombined],
  ["purchasingPower", "Poder de compra", CircleDollarSign],
  ["taxes", "Impostômetro", ReceiptText],
  ["spending", "Orçamento federal", ChartColumnIncreasing],
  ["social", "Programas sociais", HeartHandshake],
  ["explorer", "Explorar dados", Search],
  ["sources", "Fontes e método", BookOpenText],
];
const page = ref("overview");
const theme = ref("light");
const chartStart = ref("all");
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
  get ink() { return theme.value === "dark" ? "#9fc4df" : "#20394f"; },
  get teal() { return theme.value === "dark" ? "#58c2b0" : "#188984"; },
  get coral() { return theme.value === "dark" ? "#ef927d" : "#d76e58"; },
  get gold() { return theme.value === "dark" ? "#e5bd68" : "#c89c46"; },
  get slate() { return theme.value === "dark" ? "#aab8c1" : "#8e9da7"; },
};
const chartTheme = computed(() => theme.value === "dark"
  ? { label: "#aebbc3", legend: "#b7c3ca", axis: "#3b4a55", grid: "#2a3741", tooltip: "#0c141c", pointer: "#8295a2" }
  : { label: "#80909a", legend: "#657588", axis: "#e6e9e7", grid: "#edf0ee", tooltip: "#142b40", pointer: "#9baab4" });

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
const navLabel = computed(() => menu.find((item) => item[0] === page.value)?.[1] || "");
function includesChartStart(value) {
  if (chartStart.value !== "2012") return true;
  return String(value ?? "") >= "2012";
}

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
const columns = computed(() => dataset.value.rows.length ? Object.keys(dataset.value.rows[0]) : []);
const filteredRows = computed(() => {
  const q = search.value.trim().toLocaleLowerCase("pt-BR");
  return q ? dataset.value.rows.filter((row) => Object.values(row).some((value) => String(value ?? "").toLocaleLowerCase("pt-BR").includes(q))) : dataset.value.rows;
});
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize)));
const visibleRows = computed(() => filteredRows.value.slice((pageNumber.value - 1) * pageSize, pageNumber.value * pageSize));

const tooltip = computed(() => ({
  trigger: "axis",
  backgroundColor: chartTheme.value.tooltip,
  borderWidth: 0,
  textStyle: { color: "#fffdf8", fontSize: 12, fontFamily: "Inter, sans-serif" },
  axisPointer: { type: "line", lineStyle: { color: chartTheme.value.pointer, type: "dashed" } },
}));
const baseXAxis = computed(() => ({ type: "time", axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, fontSize: 10, hideOverlap: true } }));
const baseYAxis = (name) => ({ type: "value", name, nameTextStyle: { color: chartTheme.value.label }, axisLabel: { color: chartTheme.value.label }, splitLine: { lineStyle: { color: chartTheme.value.grid } } });
const debtChart = computed(() => {
  const rows = (data.value?.debt.monthly || []).filter((r) => includesChartStart(r.data));
  const series = [
    ["DPF total", "dpf_bilhoes", palette.ink, 3],
    ["Interna · DPMFi", "dpmfi_bilhoes", palette.teal, 2],
    ["Externa · DPFe", "dpfe_bilhoes", palette.coral, 2],
  ].map(([name, key, color, width]) => ({
    name, type: "line", smooth: 0.24, showSymbol: false,
    lineStyle: { color, width }, itemStyle: { color },
    data: rows.map((r) => [r.data, r[key] / 1000]),
  }));
  return {
    color: [palette.ink, palette.teal, palette.coral], grid: { left: 58, right: 22, top: 34, bottom: 60 },
    tooltip: { ...tooltip.value, valueFormatter: (v) => "R$ " + pretty(v, 2) + " tri" },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 12, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: baseXAxis.value, yAxis: { ...baseYAxis("R$ trilhões"), axisLabel: { color: chartTheme.value.label, formatter: (v) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) } }, series,
  };
});
const macroChart = computed(() => {
  const rows = (data.value?.debt.macro || []).filter((r) => includesChartStart(r.data));
  const make = (name, key, color) => ({
    name, type: "line", smooth: 0.25, showSymbol: false, connectNulls: false,
    lineStyle: { color, width: 2.4 }, itemStyle: { color }, areaStyle: { color, opacity: 0.05 },
    data: rows.map((r) => [r.data, r[key]]),
  });
  return {
    color: [palette.coral, palette.gold], grid: { left: 54, right: 18, top: 30, bottom: 58 },
    tooltip: { ...tooltip.value, valueFormatter: (v) => pretty(v, 2) + "% do PIB" },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 12, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: baseXAxis.value, yAxis: { ...baseYAxis("% do PIB"), axisLabel: { color: chartTheme.value.label, formatter: "{value}%" } },
    series: [make("DBGG · bruta", "dbgg_percentual_pib", palette.coral), make("DLGG · líquida", "dlgg_percentual_pib", palette.gold)],
  };
});
const factorsChart = computed(() => {
  const names = ["I.2 - Juros  Apropriados", "I.1 - Emissão/Resgate Líquido", "Total dos Fatores (I + II)"];
  const rows = (data.value?.debt.factors || []).filter((r) => includesChartStart(r.data));
  const colors = [palette.coral, palette.teal, palette.ink];
  return {
    color: colors, grid: { left: 62, right: 18, top: 30, bottom: 62 },
    tooltip: { ...tooltip.value, valueFormatter: (v) => "R$ " + pretty(v) + " bi" },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 16, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { ...baseXAxis.value, axisLabel: { ...baseXAxis.value.axisLabel, hideOverlap: true, rotate: 25, margin: 12 } }, yAxis: baseYAxis("R$ bilhões"),
    series: names.map((name, i) => ({
      name: ["Juros apropriados", "Emissão líquida", "Fatores totais"][i], type: "line", smooth: 0.2, showSymbol: false,
      lineStyle: { color: colors[i], width: 2 }, data: rows.filter((r) => r.indicador === name).map((r) => [r.data, r.valor_r_bilhoes]),
    })),
  };
});
const interestChart = computed(() => {
  const rows = (data.value?.debt.interest.annual || []).filter((r) => includesChartStart(r.ano));
  const years = rows.map((r) => r.ano);
  return {
    color: [palette.ink, palette.teal],
    grid: { left: 58, right: 58, top: 32, bottom: 42 },
    tooltip: {
      ...tooltip.value,
      formatter(params) {
        const year = params[0]?.axisValue ?? "";
        return `<strong>${year}</strong><br/>` + params.map((p) => {
          const value = p.seriesName.toLocaleLowerCase("pt-BR").includes("taxa")
            ? (p.value == null ? "—" : percent(p.value))
            : `R$ ${pretty(p.value, 1)} bi`;
          return `${p.marker} ${p.seriesName}: ${value}`;
        }).join("<br/>");
      },
    },
    xAxis: { type: "category", data: years, axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, interval: 2 } },
    yAxis: [
      { ...baseYAxis("R$ bilhões correntes"), axisLabel: { color: chartTheme.value.label } },
      { ...baseYAxis("% aproximado"), position: "right", splitLine: { show: false }, axisLabel: { color: chartTheme.value.label, formatter: "{value}%" } },
    ],
    series: [
      { name: "Juros apropriados", type: "bar", barMaxWidth: 18, itemStyle: { color: palette.ink, borderRadius: [3, 3, 0, 0] }, data: rows.map((r) => r.juros_dpf_bilhoes) },
      { name: "Taxa aproximada", type: "line", yAxisIndex: 1, smooth: 0.2, showSymbol: false, lineStyle: { color: palette.coral, width: 2.5 }, itemStyle: { color: palette.coral }, data: rows.map((r) => r.custo_implicito_aproximado_percentual) },
    ],
  };
});
function spendingChart(capital = false) {
  const rows = (data.value?.spending || []).filter((r) => includesChartStart(r.ano));
  const years = [...new Set(rows.map((r) => r.ano))].sort((a, b) => a - b);
  const functions = ["Saúde", "Educação", "Segurança Pública"];
  const colors = [palette.coral, palette.teal, palette.gold];
  return {
    color: colors, grid: { left: 60, right: 20, top: 30, bottom: 62 },
    tooltip: { ...tooltip.value, valueFormatter: (v) => "R$ " + pretty(v, 1) + " bi" },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 16, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { type: "category", data: years, axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, interval: 2 } },
    yAxis: { ...baseYAxis(capital ? "R$ bi · preços de 2025" : "R$ bi · preços de 2025") },
    series: functions.map((name, i) => ({
      name, type: capital ? "bar" : "line", smooth: 0.24, showSymbol: false, barMaxWidth: 14,
      lineStyle: { color: colors[i], width: 2.4 }, itemStyle: { color: colors[i], borderRadius: capital ? [3, 3, 0, 0] : 0 },
      areaStyle: capital ? undefined : { opacity: 0.04 },
      data: years.map((year) => {
        const row = rows.find((r) => r.ano === year && r.funcao.trim() === name);
        if (!row) return 0;
        const field = capital ? "gnd4_investimento_pago_r$" : "despesa_paga_r$";
        return row[field] * realFactor(year) / 1e9;
      }),
    })),
  };
}
const spendingTrend = computed(() => spendingChart(false));
const capitalTrend = computed(() => spendingChart(true));
const overviewTrend = computed(() => ({ ...spendingTrend.value, grid: { left: 55, right: 16, top: 25, bottom: 62 } }));
const socialCoverageChart = computed(() => {
  const rows = (data.value?.social?.bpc_annual || []).filter((r) => includesChartStart(r.ano));
  return {
    color: [palette.teal, palette.gold], grid: { left: 62, right: 20, top: 26, bottom: 58 },
    tooltip: { ...tooltip.value, valueFormatter: (v) => pretty(v, 2) + " mi pessoas" },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 16, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { type: "category", data: rows.map((r) => r.ano), axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, interval: 2 } },
    yAxis: { ...baseYAxis("Milhões de pessoas"), axisLabel: { color: chartTheme.value.label } },
    series: [
      { name: "Deficiência", type: "line", smooth: .2, showSymbol: false, lineStyle: { color: palette.teal, width: 2.4 }, data: rows.map((r) => r.beneficiarios_pcd / 1e6) },
      { name: "Idosos", type: "line", smooth: .2, showSymbol: false, lineStyle: { color: palette.gold, width: 2.4 }, data: rows.map((r) => r.beneficiarios_idosos / 1e6) },
    ],
  };
});
const socialSpendChart = computed(() => {
  const rows = data.value?.social?.comparison_2024 || [];
  return {
    color: [palette.ink], grid: { left: 65, right: 22, top: 24, bottom: 35 },
    tooltip: { ...tooltip.value, valueFormatter: (v) => "R$ " + pretty(v, 2) + " bi" },
    xAxis: { type: "category", data: rows.map((r) => r.programa), axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label } },
    yAxis: { ...baseYAxis("R$ bilhões correntes"), axisLabel: { color: chartTheme.value.label } },
    series: [{ name: "Repasses", type: "bar", barMaxWidth: 44, itemStyle: { color: palette.ink, borderRadius: [4,4,0,0] }, data: rows.map((r) => r.repasses_brl / 1e9) }],
  };
});

const pibNominalChart = computed(() => {
  const quarterly = pibPeriod.value === "quarterly";
  const rows = (quarterly ? pibQuarterly.value : data.value?.pib?.aggregates || [])
    .filter((row) => quarterly ? includesChartStart(row.trimestre) : row.tipo_periodo === pibPeriod.value && includesChartStart(row.periodo));
  const labels = rows.map((row) => quarterly ? row.trimestre : row.periodo);
  const amount = (row, slug) => Number(row[`${slug}_nominal_milhoes`]) / 1e6;
  return {
    color: [palette.ink, palette.teal, palette.coral],
    grid: { left: 64, right: 18, top: 28, bottom: 56 },
    tooltip: { ...tooltip.value, valueFormatter: (value) => `R$ ${pretty(value, 2)} tri` },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 14, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { type: "category", data: labels, axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, interval: Math.max(0, Math.floor(labels.length / 14)) } },
    yAxis: { ...baseYAxis("R$ trilhões correntes"), axisLabel: { color: chartTheme.value.label } },
    series: [
      { name: "PIB", type: "line", smooth: .2, showSymbol: false, lineStyle: { color: palette.ink, width: 2.6 }, areaStyle: { color: palette.ink, opacity: .05 }, data: rows.map((row) => amount(row, "pib")) },
      { name: "Agropecuária", type: "line", smooth: .2, showSymbol: false, lineStyle: { color: palette.teal, width: 2 }, data: rows.map((row) => amount(row, "agropecuaria")) },
      { name: "Indústria", type: "line", smooth: .2, showSymbol: false, lineStyle: { color: palette.gold, width: 2 }, data: rows.map((row) => amount(row, "industria")) },
      { name: "Serviços", type: "line", smooth: .2, showSymbol: false, lineStyle: { color: palette.coral, width: 2 }, data: rows.map((row) => amount(row, "servicos")) },
    ],
  };
});
function pibGrowthRows() {
  if (pibPeriod.value === "quarterly") return pibQuarterly.value.filter((row) => includesChartStart(row.trimestre));
  return (data.value?.pib?.aggregates || []).filter((row) => row.tipo_periodo === pibPeriod.value && includesChartStart(row.periodo));
}
function pibRateField(slug) {
  if (pibPeriod.value === "quarterly") return `${slug}_yoy_percentual`;
  if (pibPeriod.value === "semestre") return `${slug}_real_semestre_derived_percentual`;
  return `${slug}_ytd_percentual`;
}
const pibGrowthChart = computed(() => {
  const rows = pibGrowthRows();
  const labels = rows.map((row) => pibPeriod.value === "quarterly" ? row.trimestre : row.periodo);
  const series = [
    { slug: "pib", name: "PIB · mesmo período do ano anterior", color: palette.ink },
    { slug: "agropecuaria", name: "Agropecuária", color: palette.gold },
    { slug: "industria", name: "Indústria", color: palette.coral },
    { slug: "servicos", name: "Serviços", color: palette.teal },
  ];
  if (pibPeriod.value === "quarterly") series.splice(1, 0, { slug: "pib_qoq_sa", name: "PIB · trimestre anterior, ajuste sazonal", color: palette.slate, direct: true });
  return {
    color: series.map((item) => item.color), grid: { left: 60, right: 18, top: 30, bottom: 60 },
    tooltip: { ...tooltip.value, valueFormatter: (value) => percent(value) },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 10, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { type: "category", data: labels, axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, interval: Math.max(0, Math.floor(labels.length / 14)) } },
    yAxis: { ...baseYAxis("Variação real (%)"), axisLabel: { color: chartTheme.value.label, formatter: "{value}%" } },
    series: series.map((item) => ({ name: item.name, type: "line", smooth: .15, showSymbol: false, connectNulls: false, lineStyle: { color: item.color, width: item.slug === "pib" ? 2.8 : 2 }, data: rows.map((row) => row[item.direct ? "pib_qoq_sa_percentual" : pibRateField(item.slug)]) })),
  };
});
const pibSpendingChart = computed(() => {
  const rows = pibGrowthRows();
  const labels = rows.map((row) => pibPeriod.value === "quarterly" ? row.trimestre : row.periodo);
  const items = [
    ["consumo_familias", "Consumo das famílias", palette.ink],
    ["consumo_governo", "Consumo do governo", palette.teal],
    ["formacao_capital", "Formação de capital", palette.coral],
    ["exportacoes", "Exportações", palette.gold],
    ["importacoes", "Importações", palette.slate],
  ];
  return {
    color: items.map((item) => item[2]), grid: { left: 60, right: 18, top: 28, bottom: 60 },
    tooltip: { ...tooltip.value, valueFormatter: (value) => percent(value) },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 10, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { type: "category", data: labels, axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label, interval: Math.max(0, Math.floor(labels.length / 14)) } },
    yAxis: { ...baseYAxis("Variação real (%)"), axisLabel: { color: chartTheme.value.label, formatter: "{value}%" } },
    series: items.map(([slug, name, color]) => ({ name, type: "line", smooth: .15, showSymbol: false, connectNulls: false, lineStyle: { color, width: 2 }, data: rows.map((row) => row[pibRateField(slug)]) })),
  };
});
const taxMonthlyChart = computed(() => {
  const rows = taxMonthly.value.filter((row) => includesChartStart(row.data));
  return {
    color: [palette.ink, palette.teal], grid: { left: 68, right: 22, top: 30, bottom: 56 },
    tooltip: { ...tooltip.value, valueFormatter: (value) => `R$ ${pretty(value, 2)} bi` },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 14, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: baseXAxis.value, yAxis: { ...baseYAxis("R$ bilhões correntes"), axisLabel: { color: chartTheme.value.label } },
    series: [
      { name: "Total federal", type: "line", smooth: .15, showSymbol: false, lineStyle: { color: palette.ink, width: 2.5 }, areaStyle: { color: palette.ink, opacity: .05 }, data: rows.map((row) => [row.data + "-01", row.arrecadacao_total_federal_milhoes / 1000]) },
      { name: "Administrada pela RFB", type: "line", smooth: .15, showSymbol: false, lineStyle: { color: palette.teal, width: 2 }, data: rows.map((row) => [row.data + "-01", row.arrecadacao_rfb_administrada_milhoes == null ? null : row.arrecadacao_rfb_administrada_milhoes / 1000]) },
    ],
  };
});
const taxBurdenChart = computed(() => {
  const rows = (data.value?.taxes?.general_annual || []).filter((row) => includesChartStart(row.ano));
  return {
    color: [palette.ink, palette.teal, palette.gold], grid: { left: 58, right: 20, top: 28, bottom: 48 },
    tooltip: { ...tooltip.value, valueFormatter: (value) => `${pretty(value, 2)}% do PIB` },
    legend: { bottom: 0, left: "center", icon: "circle", itemWidth: 8, itemHeight: 8, itemGap: 14, textStyle: { color: chartTheme.value.legend, fontSize: 9 } },
    xAxis: { type: "category", data: rows.map((row) => row.ano), axisLine: { lineStyle: { color: chartTheme.value.axis } }, axisLabel: { color: chartTheme.value.label } },
    yAxis: { ...baseYAxis("Carga tributária (% do PIB)"), axisLabel: { color: chartTheme.value.label, formatter: "{value}%" } },
    series: [
      ["Governo Geral", "governo_geral_percentual_pib", palette.ink],
      ["Governo Central", "governo_central_percentual_pib", palette.teal],
      ["Estados", "governos_estaduais_percentual_pib", palette.gold],
      ["Municípios", "governos_municipais_percentual_pib", palette.coral],
    ].map(([name, field, color]) => ({ name, type: "line", showSymbol: true, symbolSize: 5, lineStyle: { color, width: 2.3 }, itemStyle: { color }, data: rows.map((row) => row[field]) })),
  };
});
const purchasingPowerChart = computed(() => {
  const rows = purchasingPowerRows.value.filter((row) => includesChartStart(row.data));
  return {
    color: [palette.ink], grid: { left: 72, right: 22, top: 28, bottom: 54 },
    tooltip: { ...tooltip.value, valueFormatter: (value) => `R$ ${pretty(value, 2)}` },
    xAxis: baseXAxis.value,
    yAxis: { ...baseYAxis("R$ correntes para a cesta-base"), axisLabel: { color: chartTheme.value.label } },
    series: [{ name: "Cesta de R$ 100 em jul/1994", type: "line", smooth: .15, showSymbol: false, lineStyle: { color: palette.ink, width: 2.7 }, areaStyle: { color: palette.teal, opacity: .09 }, data: rows.map((row) => [row.data + "-01", row.preco_cesta_r_100_jul_1994]) }],
  };
});
const chartGuides = {
  debt: {
    title: "Estoque e composição da DPF",
    represents: "Mostra o saldo mensal da Dívida Pública Federal em poder do público, separado em dívida interna (DPMFi) e externa (DPFe), em reais correntes.",
    interpretation: "Compare a trajetória e a composição ao longo do tempo. Uma alta do estoque não é, por si só, igual a gasto novo: juros apropriados, emissões líquidas, câmbio e outros ajustes também alteram o saldo. Valores nominais não descontam inflação.",
    importance: "O estoque revela o tamanho e a estrutura das obrigações federais que o Tesouro precisa administrar e refinanciar.",
    study: "Estude títulos públicos, dívida bruta e líquida, resultado primário, necessidade de financiamento, indexadores, maturidade e risco cambial. Consulte também os fatores de variação da DPF.",
  },
  macro: {
    title: "Dívida bruta e líquida em proporção do PIB",
    represents: "Séries mensais do Banco Central para a Dívida Bruta do Governo Geral (DBGG) e a Dívida Líquida do Governo Geral (DLGG), expressas como percentual do PIB.",
    interpretation: "A razão relaciona o estoque de dívida ao tamanho anual da economia. DBGG e DLGG têm conceitos distintos e abrangem União, estados e municípios; não são a DPF do Tesouro. Mudanças podem refletir dívida, PIB, câmbio e outros ajustes.",
    importance: "A proporção ajuda a comparar o endividamento com a capacidade econômica do país e contextualiza a escala da dívida ao longo do tempo.",
    study: "Estude conceitos de dívida bruta e líquida, setor público não financeiro, metodologia fiscal do BCB, PIB nominal, resultado primário e dinâmica da dívida.",
  },
  factors: {
    title: "Fatores de variação do estoque da DPF",
    represents: "Decompõe a mudança mensal da DPF em fatores divulgados pelo Tesouro, como juros apropriados e emissão ou resgate líquido, além do total dos fatores.",
    interpretation: "Leia os valores como contribuições para a variação do saldo no mês. Juros apropriados são registrados por competência; emissão líquida é captação menos resgates. A soma dos fatores deve ser interpretada com as regras e ajustes do relatório do Tesouro.",
    importance: "A decomposição distingue a origem das mudanças do estoque e evita atribuir toda expansão da dívida a novas despesas primárias.",
    study: "Estude contabilidade por competência, emissão e resgate de títulos, resultado primário, reconhecimento de passivos, ajustes patrimoniais e a metodologia dos fatores da DPF.",
  },
  interest: {
    title: "Juros apropriados e taxa implícita aproximada",
    represents: "As barras somam os juros apropriados na DPF por ano. A linha mostra uma razão analítica entre esse fluxo e o estoque médio anual, apenas para anos completos.",
    interpretation: "A apropriação é um registro por competência e não equivale ao pagamento em caixa no mesmo período. A taxa calculada pelo painel é aproximada; não substitui o custo médio oficial da dívida divulgado pelo Tesouro.",
    importance: "Os juros ajudam a dimensionar o custo financeiro acumulado e a compreender como indexadores e taxas afetam a trajetória do estoque.",
    study: "Estude juros nominais e reais, apropriação versus caixa, custo médio oficial da DPF, indexadores dos títulos, prazo médio e risco de refinanciamento.",
  },
  spending: {
    title: "Execução paga por função orçamentária",
    represents: "Despesas pagas pelo orçamento federal nas funções Saúde, Educação e Segurança Pública, corrigidas pelo IPCA para reais de 2025.",
    interpretation: "Valores reais permitem comparar poder de compra entre anos. Pagamento não é o mesmo que dotação autorizada ou empenho. A classificação por função inclui diferentes tipos de despesa e não cobre automaticamente os orçamentos estaduais e municipais.",
    importance: "A série mostra a escala e a evolução dos recursos federais executados em áreas centrais de política pública.",
    study: "Estude ciclo orçamentário, funções e subfunções, empenho, liquidação e pagamento, IPCA, gasto obrigatório e discricionário e repartição federativa do financiamento.",
  },
  capital: {
    title: "Investimento de capital (GND 4)",
    represents: "Mostra a despesa paga classificada como Grupo de Natureza da Despesa 4 — Investimentos — nas três funções, em valores corrigidos para reais de 2025.",
    interpretation: "GND 4 é uma parte do total pago, não todo o gasto da política. O volume executado não informa sozinho se a obra foi concluída, se o ativo está operando ou qual resultado social foi alcançado.",
    importance: "Investimentos podem ampliar ou modernizar a capacidade de prestação de serviços, mas sua leitura exige acompanhar execução física e manutenção futura.",
    study: "Estude classificação por GND, investimento público, restos a pagar, execução física, avaliação de projetos, custo do ciclo de vida e orçamento de capital.",
  },
  bpc: {
    title: "Beneficiários do BPC por grupo",
    represents: "Série anual de pessoas beneficiárias do Benefício de Prestação Continuada, separadas entre pessoas idosas e pessoas com deficiência.",
    interpretation: "As contagens refletem cobertura registrada na série administrativa anual. Mudanças podem decorrer de demografia, critérios legais, concessões, revisões cadastrais e gestão; não medem isoladamente pobreza ou impacto causal.",
    importance: "O BPC é uma transferência de renda de grande escala e a evolução da cobertura ajuda a acompanhar o alcance dessa política de proteção social.",
    study: "Estude a LOAS, critérios de elegibilidade do BPC, envelhecimento populacional, deficiência, Cadastro Único, cobertura e avaliação de políticas sociais.",
  },
  socialSpend: {
    title: "Repasses informados para Bolsa Família e BPC",
    represents: "Compara valores nominais reportados em 2024 para repasses do Bolsa Família e do BPC, em bilhões de reais.",
    interpretation: "Os números vêm de fontes e perímetros administrativos distintos. Famílias alcançadas pelo Bolsa Família e beneficiários do BPC são unidades diferentes; não some coberturas nem interprete valores como benefício médio individual comparável.",
    importance: "A comparação contextualiza a escala fiscal de programas importantes de transferência de renda, preservando diferenças de público e contabilidade.",
    study: "Estude desenho de transferências condicionadas e não condicionadas, benefícios previdenciários e assistenciais, cobertura, focalização e indicadores de pobreza.",
  },
  pibNominal: {
    title: "PIB nominal e atividade por setor",
    represents: "Mostra valores correntes trimestrais, semestrais ou anuais do PIB e de setores selecionados, segundo as Contas Nacionais Trimestrais do IBGE.",
    interpretation: "Valores correntes somam preços e quantidades do período. Crescer nominalmente não significa produzir mais em termos reais. Os setores apresentados são componentes do PIB e não devem ser somados novamente ao total.",
    importance: "O PIB mede a escala da atividade econômica e fornece contexto para dívida, arrecadação e gasto público.",
    study: "Estude Sistema de Contas Nacionais, valor adicionado, preços correntes e constantes, deflator do PIB, índice de volume encadeado e ajuste sazonal.",
  },
  pibGrowth: {
    title: "Crescimento real do PIB por setor",
    represents: "Apresenta taxas de variação do índice de volume do PIB e dos setores, incluindo comparações oficiais do IBGE e, quando selecionado, a taxa semestral derivada pelo projeto.",
    interpretation: "Trimestre contra trimestre com ajuste sazonal, mesmo trimestre do ano anterior, acumulado no ano e comparação semestral são medidas diferentes. A taxa derivada de semestre não é uma publicação oficial independente do IBGE.",
    importance: "As taxas reais isolam a mudança de volume da variação dos preços e ajudam a identificar ciclos e diferenças entre setores.",
    study: "Estude índices de volume, ajuste sazonal, efeitos de base, séries encadeadas, crescimento acumulado e revisões das Contas Nacionais.",
  },
  pibSpending: {
    title: "Componentes da despesa do PIB",
    represents: "Mostra a variação real de consumo das famílias e do governo, formação de capital, exportações e importações nas Contas Nacionais do IBGE.",
    interpretation: "São componentes da ótica da despesa. Importações entram com sinal negativo na identidade contábil, mas a taxa de crescimento do componente não é sua contribuição direta para o crescimento do PIB.",
    importance: "A composição da despesa mostra quais componentes acompanham ou explicam a dinâmica da atividade, sem confundir crescimento de um componente com contribuição em pontos percentuais.",
    study: "Estude identidade do PIB pela despesa, consumo, formação bruta de capital fixo, variação de estoques, exportações líquidas e decomposição de crescimento.",
  },
  taxes: {
    title: "Arrecadação federal mensal",
    represents: "Soma nominal das receitas federais administradas pela Receita Federal e por outros órgãos, em valores mensais divulgados pela RFB.",
    interpretation: "A linha administrada pela RFB é detalhada a partir de 2021; o total federal é a série de referência. Valores correntes e variação nominal em 12 meses não descontam inflação nem isolam efeitos de atividade, legislação ou composição.",
    importance: "A arrecadação é uma fonte de financiamento do governo federal e ajuda a contextualizar o espaço fiscal, sem equivaler a receita disponível após transferências e despesas.",
    study: "Estude receita corrente, tributos e contribuições, repartição de receitas, carga tributária, elasticidade da arrecadação, inflação e resultado fiscal.",
  },
  taxBurden: {
    title: "Carga tributária bruta do Governo Geral",
    represents: "Carga tributária anual calculada pelo Tesouro Nacional para Governo Central, estados e municípios, apresentada como percentual do PIB.",
    interpretation: "A série consolidada mede tributos em relação ao PIB e tem frequência anual. Não deve ser somada à arrecadação federal mensal, pois os escopos e períodos diferem.",
    importance: "O indicador permite acompanhar a participação da arrecadação tributária na economia e comparar a distribuição entre esferas públicas.",
    study: "Estude carga tributária bruta, incidência e base tributária, federalismo fiscal, repartição de receitas, PIB nominal e comparabilidade internacional.",
  },
  purchasingPower: {
    title: "Preços desde a implementação do real",
    represents: "O gráfico mostra quanto custaria, em cada mês, uma cesta de consumo que custava R$ 100 em julho de 1994. A série é construída com as variações mensais do IPCA.",
    interpretation: "O preço acumulado é composto multiplicando os fatores mensais de agosto de 1994 até o último IPCA disponível. A diferença representa inflação acumulada; a perda do poder de compra de R$ 1 é calculada como 1 menos o inverso desse fator. É uma medida de preços no Brasil, não da cotação do real frente ao dólar.",
    importance: "A série mostra por que valores nominais de décadas diferentes não são diretamente comparáveis e quantifica a erosão do poder de compra da moeda ao longo do tempo.",
    study: "Estude IPCA e cesta de consumo, números-índice, inflação acumulada e composta, inflação média versus inflação pessoal, indexação e correção monetária.",
  },
};

function initTheme() {
  const saved = localStorage.getItem("insights-theme");
  theme.value = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = theme.value;
}
function toggleTheme() {
  theme.value = theme.value === "dark" ? "light" : "dark";
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
  if (value === "titles") await loadTitles();
});
watch(search, () => { pageNumber.value = 1; });
function go(id) {
  page.value = id;
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
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-symbol"><ChartNoAxesCombined class="ui-icon" :size="19" :stroke-width="1.8" /></div><div><b>INSIGHTS</b><small>BRASIL · DADOS PÚBLICOS</small></div></div>
      <div class="side-label">PAINEL</div>
      <nav class="side-nav" aria-label="Navegação principal">
        <button v-for="item in menu" :key="item[0]" :class="{ active: page === item[0] }" :aria-label="item[1]" :title="item[1]" @click="go(item[0])"><span class="nav-glyph"><component :is="item[2]" class="ui-icon" :size="17" :stroke-width="1.8" /></span><span>{{ item[1] }}</span><i v-if="page === item[0]" class="active-mark"></i></button>
      </nav>
      <div class="sidebar-bottom">
        <div class="federal-badge"><span>RECORTE ATUAL</span><strong>Governo Federal</strong><small>Brasil · fontes oficiais</small></div>
        <div class="sync-status"><i></i> Base local sincronizada <span>06.10.2026</span></div>
      </div>
    </aside>

    <main class="main-area">
      <header class="topbar">
        <div class="mobile-brand"><div class="brand-symbol"><ChartNoAxesCombined class="ui-icon" :size="19" :stroke-width="1.8" /></div><b>INSIGHTS BRASIL</b></div>
        <div class="breadcrumb"><span>Brasil</span><i>/</i><strong>{{ navLabel }}</strong></div>
        <div class="top-actions"><span class="official-badge"><BadgeCheck class="ui-icon" :size="14" :stroke-width="1.9" /> Fontes oficiais</span><button class="theme-button" :aria-label="theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'" :aria-pressed="theme === 'dark'" :title="theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'" @click="toggleTheme"><component :is="theme === 'dark' ? Sun : Moon" class="ui-icon" :size="15" :stroke-width="1.9" aria-hidden="true" /><b>{{ theme === 'dark' ? 'Claro' : 'Escuro' }}</b></button><button class="info-button" title="Fontes e método" @click="go('sources')"><Info class="ui-icon" :size="14" :stroke-width="1.8" /></button></div>
      </header>
      <div v-if="data && ['overview', 'debt', 'interest', 'spending', 'social', 'pib', 'taxes', 'purchasingPower'].includes(page)" class="chart-range-control" role="group" aria-label="Período inicial dos gráficos">
        <span>INÍCIO DOS GRÁFICOS</span>
        <button :class="{ active: chartStart === 'all' }" :aria-pressed="chartStart === 'all'" @click="chartStart = 'all'">Histórico completo</button>
        <button :class="{ active: chartStart === '2012' }" :aria-pressed="chartStart === '2012'" @click="chartStart = '2012'">Desde 2012</button>
      </div>

      <div v-if="error" class="error-banner">{{ error }}</div>
      <div v-else-if="!data" class="loading-screen"><span class="spinner"></span><p>Carregando as séries públicas…</p></div>
      <template v-else>
        <section v-if="page === 'overview'" class="content">
          <section class="hero">
            <div class="hero-copy">
              <div class="eyebrow"><span></span> UM RETRATO DOS RECURSOS PÚBLICOS</div>
              <h1>O que devemos.<br /><em>O que escolhemos financiar.</em></h1>
              <p>Acompanhe quanto o governo deve, quanto arrecada e como distribui os recursos. Indicadores oficiais mostram séries históricas, métodos e limites de interpretação.</p>
              <button class="hero-link" @click="go('explorer')">Explorar todas as bases <ArrowUpRight class="ui-icon" :size="15" /></button>
            </div>
            <div class="hero-visual" aria-hidden="true">
              <div class="orbit orbit-a"></div><div class="orbit orbit-b"></div><div class="orbit orbit-c"></div>
              <div class="visual-core"><span>BR</span></div>
              <i class="orb-node n1"></i><i class="orb-node n2"></i><i class="orb-node n3"></i>
              <span class="visual-word word-a">DÍVIDA</span><span class="visual-word word-b">ORÇAMENTO</span><span class="visual-word word-c">BRASIL</span>
            </div>
            <div class="hero-range"><span>RECORTE HISTÓRICO</span><strong>1994 <i>—</i> 2026</strong></div>
          </section>

          <div class="section-title"><div><span>EM NÚMEROS</span><h2>Panorama mais recente</h2></div><small>Últimos dados disponíveis</small></div>
          <div class="metrics">
            <article class="metric metric-blue"><div class="metric-label">ESTOQUE DA DPF <span><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></span></div><strong>R$ {{ tri(debtLatest?.dpf_bilhoes) }} <small>tri</small></strong><div class="metric-foot"><span>{{ month(debtLatest?.data) }}</span><i>Dívida federal · Tesouro</i></div><div class="sparkline"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></article>
            <article class="metric metric-red"><div class="metric-label">DÍVIDA BRUTA / PIB <span>%</span></div><strong>{{ percent(macroLatest?.dbgg_percentual_pib) }}</strong><div class="metric-foot"><span>{{ month(macroLatest?.data) }}</span><i>Governo geral · BCB</i></div><div class="sparkline"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></article>
            <article class="metric metric-gold"><div class="metric-label">JUROS APROPRIADOS · ANO COMPLETO</div><strong>R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 1) }} <small>bi</small></strong><div class="metric-foot"><span>{{ latestInterestYear?.ano }}</span><i>Competência · Tesouro</i></div><div class="sparkline"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></article>
            <article class="metric metric-teal"><div class="metric-label">ARRECADAÇÃO FEDERAL · {{ taxLatest?.ano }}</div><strong>R$ {{ pretty(taxAnnualRunning / 1e6, 2) }} <small>tri</small></strong><div class="metric-foot"><span>Até {{ month(taxLatest?.data) }}</span><i>Total publicado · RFB</i></div><div class="sparkline"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></div></article>
          </div>

          <div class="section-title overview-index-title"><div><span>EXPLORE OS ESTUDOS</span><h2>Sete perspectivas sobre as contas públicas</h2></div><small>Indicadores com fontes e método</small></div>
          <div class="overview-links">
            <button @click="go('debt')"><div class="overview-link-head"><Landmark class="overview-topic-icon" :size="16"/><span>DÍVIDA PÚBLICA</span></div><strong>Estoque, composição e fatores</strong><small>DPF · Tesouro Nacional <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('interest')"><div class="overview-link-head"><Percent class="overview-topic-icon" :size="16"/><span>JUROS</span></div><strong>R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 0) }} bi apropriados em {{ latestInterestYear?.ano }}</strong><small>Competência e custo aproximado <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('pib')"><div class="overview-link-head"><ChartNoAxesCombined class="overview-topic-icon" :size="16"/><span>ATIVIDADE ECONÔMICA</span></div><strong>PIB real: {{ percent(pibLatest?.pib_yoy_percentual) }} no último trimestre</strong><small>IBGE · Contas Nacionais <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('purchasingPower')"><div class="overview-link-head"><CircleDollarSign class="overview-topic-icon" :size="16"/><span>PODER DE COMPRA</span></div><strong>O real mantém {{ percent(purchasingPowerLatest?.poder_compra_remanescente_percentual) }} do poder de compra inicial</strong><small>IPCA desde julho de 1994 <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('spending')"><div class="overview-link-head"><ChartColumnIncreasing class="overview-topic-icon" :size="16"/><span>ORÇAMENTO FEDERAL</span></div><strong>Saúde, educação e segurança</strong><small>Pagamentos e investimento público <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('social')"><div class="overview-link-head"><HeartHandshake class="overview-topic-icon" :size="16"/><span>PROTEÇÃO SOCIAL</span></div><strong>{{ pretty(socialLatest?.beneficiarios_total, 0) }} pessoas no BPC em {{ socialLatest?.ano }}</strong><small>BPC, Bolsa Família e Auxílio Gás <ArrowUpRight class="ui-icon" :size="12" /></small></button>
            <button @click="go('taxes')"><div class="overview-link-head"><ReceiptText class="overview-topic-icon" :size="16"/><span>ARRECADAÇÃO DE IMPOSTOS</span></div><strong>R$ {{ pretty(taxAnnualRunning / 1e6, 2) }} tri no ano até {{ month(taxLatest?.data) }}</strong><small>Receita federal · sem projeção <ArrowUpRight class="ui-icon" :size="12" /></small></button>
          </div>

          <div class="dashboard-grid">
            <article class="panel panel-debt">
              <div class="panel-heading"><div><span class="kicker">{{ chartStart === '2012' ? '2012 — 2026' : '2000 — 2026' }}</span><h3>Trajetória da dívida federal</h3></div><button class="subtle-link" @click="go('debt')">Ver análise <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></div>
              <TrendChart :option="debtChart" :guide="chartGuides.debt" height="315px" />
              <div class="legend-row"><span><i class="legend blue"></i> DPF total</span><span><i class="legend teal"></i> Interna</span><span><i class="legend coral"></i> Externa</span><small>R$ trilhões correntes</small></div>
            </article>
            <article class="panel panel-macro">
              <div class="panel-heading"><div><span class="kicker">BANCO CENTRAL</span><h3>Dívida e tamanho da economia</h3></div><span class="unit-pill">% do PIB</span></div>
              <TrendChart :option="macroChart" :guide="chartGuides.macro" height="265px" />
              <p class="panel-caption">A DBGG inclui também estados e municípios. Seu escopo é mais amplo que a DPF.</p>
            </article>
          </div>
          <div class="section-title section-spacer"><div><span>ORÇAMENTO FEDERAL</span><h2>Recursos pagos por área</h2></div><button class="subtle-link" @click="go('spending')">Ver saúde, educação e segurança <b><ArrowRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></div>
          <article class="panel">
            <div class="panel-heading"><div><span class="kicker">2001 — {{ latestYear }} · VALORES REAIS</span><h3>Gasto federal corrigido pela inflação</h3></div><span class="unit-pill">IPCA · R$ de 2025</span></div>
            <TrendChart :option="overviewTrend" :guide="chartGuides.spending" height="300px" />
            <div class="legend-row"><span><i class="legend coral"></i> Saúde</span><span><i class="legend teal"></i> Educação</span><span><i class="legend gold"></i> Segurança Pública</span><small>Valores corrigidos pelo IPCA</small></div>
          </article>
          <div class="section-title section-spacer"><div><span>PROTEÇÃO SOCIAL</span><h2>Programas de grande escala</h2></div><button class="subtle-link" @click="go('social')">Ver série e método <b><ArrowRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></div>
          <div class="spending-cards"><article class="spend-card education-card"><span>BPC · BENEFICIÁRIOS · {{ socialLatest?.ano }}</span><strong>{{ pretty(socialLatest?.beneficiarios_total, 0) }}</strong><small>R$ {{ pretty(socialLatest?.repasse_total_brl / 1e9, 1) }} bi em repasses nominais</small></article><article class="spend-card health-card"><span>BOLSA FAMÍLIA · 2024</span><strong>R$ 168,3 bi</strong><small>Mais de 20,86 milhões de famílias alcançadas</small></article><article class="spend-card security-card"><span>AUXÍLIO GÁS · 2024</span><strong>5,7 mi</strong><small>Famílias por ciclo bimestral em média</small></article></div>
          <aside class="scope-callout"><span><Info class="ui-icon" :size="14" /></span><p><strong>Escopos diferentes, dados complementares.</strong> A DPF mede obrigações federais sob responsabilidade do Tesouro; DBGG/PIB abrange o governo geral. Os gastos por área são da execução orçamentária federal e não incluem despesas próprias de estados e municípios.</p><button @click="go('sources')">Entenda o método <b><ArrowRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></aside>
        </section>

        <section v-else-if="page === 'debt'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> DÍVIDA PÚBLICA FEDERAL</div><h1>Uma trajetória de <em>25 anos.</em></h1><p>Estoque, juros apropriados e composição para acompanhar o endividamento federal.</p></div><aside>ÚLTIMA COMPETÊNCIA<strong>{{ month(debtLatest?.data) }}</strong></aside></div>
          <div class="metrics">
            <article class="metric metric-blue"><div class="metric-label">ESTOQUE DPF</div><strong>R$ {{ tri(debtLatest?.dpf_bilhoes) }} <small>tri</small></strong><div class="metric-foot"><span>Em poder do público</span></div></article>
            <article class="metric metric-teal"><div class="metric-label">DPMFi · INTERNA</div><strong>R$ {{ tri(debtLatest?.dpmfi_bilhoes) }} <small>tri</small></strong><div class="metric-foot"><span>{{ percent(100 * debtLatest?.dpmfi_bilhoes / debtLatest?.dpf_bilhoes) }} do estoque</span></div></article>
            <article class="metric metric-red"><div class="metric-label">DPFe · EXTERNA</div><strong>R$ {{ tri(debtLatest?.dpfe_bilhoes) }} <small>tri</small></strong><div class="metric-foot"><span>{{ percent(100 * debtLatest?.dpfe_bilhoes / debtLatest?.dpf_bilhoes) }} do estoque</span></div></article>
            <article class="metric metric-gold"><div class="metric-label">JUROS APROPRIADOS · MÊS</div><strong>R$ {{ pretty(interestLatest?.juros_dpf_bilhoes, 1) }} <small>bi</small></strong><div class="metric-foot"><span>{{ month(interestLatest?.data) }}</span><i>Competência · Tesouro</i></div></article>
          </div>
          <div class="interest-summary">
            <article><span>ACUMULADO NO ANO ATÉ {{ month(interestLatest?.data) }}</span><strong>R$ {{ pretty(interestAnnualLast?.juros_dpf_bilhoes, 1) }} bi</strong></article>
            <article><span>JUROS EM {{ latestInterestYear?.ano }}</span><strong>R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 1) }} bi</strong></article>
            <article><span>VARIAÇÃO ANUAL</span><strong>{{ percent(interestYearChange) }}</strong></article>
            <article><span>ACUMULADO {{ completeInterestYears[0]?.ano }}–{{ latestInterestYear?.ano }}</span><strong>R$ {{ tri(cumulativeInterest) }} tri</strong></article>
          </div>
          <div class="stacked-panels">
            <article class="panel"><div class="panel-heading"><div><span class="kicker">{{ chartStart === '2012' ? 'DESDE 2012 · R$ CORRENTES' : 'R$ CORRENTES' }}</span><h3>Estoque total e composição</h3></div><span class="unit-pill">{{ chartStart === '2012' ? '2012–2026' : '2000–2026' }}</span></div><TrendChart :option="debtChart" :guide="chartGuides.debt" height="385px" /><p class="panel-caption">DPMFi e DPFe compõem o total da DPF em poder do público.</p></article>
            <div class="dashboard-grid">
              <article class="panel"><div class="panel-heading"><div><span class="kicker">BANCO CENTRAL · SGS</span><h3>Dívida bruta e líquida</h3></div><span class="unit-pill">% do PIB</span></div><TrendChart :option="macroChart" :guide="chartGuides.macro" height="295px" /><p class="panel-caption">Indicadores de governo geral; perímetro diferente da DPF.</p></article>
            </div>
            <article class="panel"><div class="panel-heading"><div><span class="kicker">TESOURO NACIONAL</span><h3>Fatores de variação da DPF</h3></div><span class="unit-pill">R$ bilhões · série mensal</span></div><TrendChart :option="factorsChart" :guide="chartGuides.factors" height="360px" /><p class="panel-caption">Juros apropriados, emissão líquida e total dos fatores. O gráfico ocupa a largura da página para facilitar a leitura das séries longas.</p></article>
            <article class="panel"><div class="panel-heading"><div><span class="kicker">{{ chartStart === '2012' ? '2012' : '2007' }} — {{ interestAnnualLast?.ano }}</span><h3>Juros apropriados por ano</h3></div><span class="unit-pill">R$ bi · taxa aproximada</span></div><TrendChart :option="interestChart" :guide="chartGuides.interest" height="330px" /><div class="interest-legend"><span><i></i> Juros apropriados no ano</span><span><i></i> Taxa implícita aproximada</span></div><p class="panel-caption">O valor anual soma a apropriação por competência dos juros e encargos da DPF. A taxa aproximada divide esse fluxo pelo estoque médio anual e só é calculada para anos completos. 2026 está parcial até {{ month(interestLatest?.data) }}. Essa razão não substitui o custo médio oficial do Tesouro.</p></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">MÉTRICAS E EXEMPLO</span><h3>DPF, DBGG e proporção sobre o PIB</h3></div></div><div class="method-row"><span>01</span><div><strong>Estoque da DPF</strong><p>Saldo da dívida federal sob responsabilidade do Tesouro, em R$ correntes na série mostrada. Exemplo de composição na última competência: {{ percent(100 * debtLatest?.dpmfi_bilhoes / debtLatest?.dpf_bilhoes) }} é dívida interna (DPMFi) e {{ percent(100 * debtLatest?.dpfe_bilhoes / debtLatest?.dpf_bilhoes) }} é externa (DPFe).</p></div></div><div class="method-row"><span>02</span><div><strong>Razão dívida / PIB</strong><p>O BCB publica DBGG/PIB e DLGG/PIB como séries próprias. A razão relaciona saldo de dívida ao fluxo anual do PIB; não confundir com a DPF do Tesouro, pois DBGG inclui estados e municípios e usa outro perímetro e metodologia.</p></div></div><div class="method-row"><span>03</span><div><strong>Variação do estoque</strong><p>A mudança do saldo entre meses pode refletir emissões líquidas, juros apropriados, câmbio, reconhecimento de passivos e outros ajustes. Não se interpreta toda alta do estoque como gasto primário novo.</p></div></div><div class="method-row"><span>04</span><div><strong>Juros</strong><p>Juros apropriados são contabilizados por competência e não significam pagamento em caixa do mesmo mês. A página dedicada descreve cálculo, exemplo e limitações da taxa implícita aproximada.</p><button class="subtle-link" @click="go('interest')">Abrir estudo de juros <ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></button></div></div></article>
            <article class="panel data-jump"><div><span class="kicker">SÉRIE MENSAL COMPLETA</span><h3>Explore os 309 registros agregados</h3><p>Veja também componentes por tipo de título, indicadores macroeconômicos, fatores, emissões, resgates e carteiras.</p></div><button @click="activeData = 'monthly'; go('explorer')">Abrir explorador <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></article>
          </div>
        </section>

        <section v-else-if="page === 'spending'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> EXECUÇÃO DO ORÇAMENTO FEDERAL</div><h1>Saúde. Educação. <em>Segurança.</em></h1><p>Quanto foi pago em cada função — e qual parcela foi registrada como investimento de capital (GND 4).</p></div><aside>ÚLTIMO EXERCÍCIO<strong>{{ latestYear }}</strong></aside></div>
          <div class="spending-cards"><article v-for="name in ['Saúde', 'Educação', 'Segurança Pública']" :key="name" class="spend-card" :class="name === 'Saúde' ? 'health-card' : name === 'Educação' ? 'education-card' : 'security-card'"><span>{{ name.toUpperCase() }} · PAGO {{ latestYear }}</span><strong>R$ {{ pretty((spendByFunction[name]?.['despesa_paga_r$'] || 0) / 1e9, 2) }} bi</strong><small>GND 4 · R$ {{ pretty((spendByFunction[name]?.['gnd4_investimento_pago_r$'] || 0) / 1e9, 2) }} bi</small></article></div>
          <div class="stacked-panels">
            <article class="panel"><div class="panel-heading"><div><span class="kicker">{{ chartStart === '2012' ? '2012 EM DIANTE' : '25 EXERCÍCIOS' }} · VALORES REAIS</span><h3>Execução paga por função</h3></div><span class="unit-pill">IPCA · R$ de 2025</span></div><TrendChart :option="spendingTrend" :guide="chartGuides.spending" height="380px" /><p class="panel-caption">O total inclui pessoal, custeio, transferências e capital. Valores anuais ajustados pelo IPCA.</p></article>
            <article class="panel"><div class="panel-heading"><div><span class="kicker">GND 4 · {{ chartStart === '2012' ? 'DESDE 2012' : 'SÉRIE HISTÓRICA' }}</span><h3>Investimento de capital pago</h3></div><span class="unit-pill">IPCA · R$ de 2025</span></div><TrendChart :option="capitalTrend" :guide="chartGuides.capital" height="340px" /><p class="panel-caption">A rubrica GND 4 é uma parte do gasto total da função; não representa todo o financiamento da área.</p></article>
            <article class="panel data-jump"><div><span class="kicker">SÉRIE ANUAL COMPLETA</span><h3>75 registros · 3 funções · 2001–2025</h3><p>Inclui despesas pagas e liquidadas, além do GND 4 em cada função.</p></div><button @click="activeData = 'spending'; go('explorer')">Abrir tabela anual <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">MÉTODO E EXEMPLO</span><h3>Como ler execução e valores reais</h3></div></div><div class="method-row"><span>01</span><div><strong>Despesa paga</strong><p>É o desembolso registrado no exercício. Exemplo: em {{ latestYear }}, {{ spendByFunction['Saúde']?.['despesa_paga_r$'] ? 'Saúde somou R$ ' + pretty(spendByFunction['Saúde']['despesa_paga_r$']/1e9, 2) + ' bilhões pagos em valores correntes' : 'a despesa paga é a soma disponibilizada pelo SIOP' }}. Não confundir com dotação autorizada ou empenho.</p></div></div><div class="method-row"><span>02</span><div><strong>Correção pelo IPCA</strong><p>Para comparar poder de compra, cada valor nominal do ano t é multiplicado pela razão entre o índice médio de 2025 e o índice médio do ano t. Assim, R$ de anos diferentes ficam expressos em preços médios de 2025; não é crescimento nominal.</p></div></div><div class="method-row"><span>03</span><div><strong>GND 4 — Investimentos</strong><p>É uma parcela de capital dentro da função. A proporção GND 4 / total pago ajuda a visualizar sua participação, mas não mede a qualidade, conclusão ou resultado dos projetos.</p></div></div></article>
          </div>
        </section>

        <section v-else-if="page === 'interest'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> CUSTO FINANCEIRO DA DÍVIDA</div><h1>Juros apropriados.<br /><em>Métrica e método.</em></h1><p>Uma leitura separada de juros por competência, evolução anual e taxa implícita aproximada da DPF.</p></div><aside>ÚLTIMA COMPETÊNCIA<strong>{{ month(interestLatest?.data) }}</strong></aside></div>
          <div class="metrics three"><article class="metric metric-gold"><div class="metric-label">JUROS NO MÊS</div><strong>R$ {{ pretty(interestLatest?.juros_dpf_bilhoes, 1) }} <small>bi</small></strong><div class="metric-foot"><span>{{ month(interestLatest?.data) }}</span><i>R$ correntes</i></div></article><article class="metric metric-blue"><div class="metric-label">ÚLTIMO ANO COMPLETO · {{ latestInterestYear?.ano }}</div><strong>R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 1) }} <small>bi</small></strong><div class="metric-foot"><span>Apropriação anual</span><i>Tesouro Nacional</i></div></article><article class="metric metric-red"><div class="metric-label">RAZÃO JUROS / ESTOQUE MÉDIO</div><strong>{{ percent(latestInterestYear?.custo_implicito_aproximado_percentual) }}</strong><div class="metric-foot"><span>Indicador aproximado</span><i>Não é custo oficial</i></div></article></div>
          <div class="stacked-panels"><article class="panel"><div class="panel-heading"><div><span class="kicker">SÉRIE ANUAL · ANOS COMPLETOS</span><h3>Juros e razão aproximada</h3></div><span class="unit-pill">R$ bi · %</span></div><TrendChart :option="interestChart" :guide="chartGuides.interest" height="350px"/><div class="interest-legend"><span><i></i> Juros apropriados no ano</span><span><i></i> Taxa implícita aproximada</span></div><p class="panel-caption">Anos parciais ficam fora da comparação da taxa; a apropriação parcial ainda pode ser consultada na tabela mensal.</p></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">DEFINIÇÃO OPERACIONAL</span><h3>O que entra no cálculo</h3></div></div><div class="method-row"><span>01</span><div><strong>Juros apropriados</strong><p>O Tesouro registra mensalmente juros e encargos apropriados por competência. É reconhecimento econômico no período, não necessariamente dinheiro pago naquele mês.</p></div></div><div class="method-row"><span>02</span><div><strong>Taxa implícita aproximada</strong><p><code>100 × soma dos juros apropriados no ano ÷ média dos estoques mensais da DPF</code>. Para {{ latestInterestYear?.ano }}, isso corresponde a R$ {{ pretty(latestInterestYear?.juros_dpf_bilhoes, 1) }} bi ÷ R$ {{ pretty(latestInterestYear?.estoque_medio_dpf_bilhoes, 1) }} bi = {{ percent(latestInterestYear?.custo_implicito_aproximado_percentual) }}.</p></div></div><div class="method-row"><span>03</span><div><strong>Limitações</strong><p>A razão é uma aproximação analítica: depende do estoque médio observado, da composição e indexadores da dívida e da contabilização por competência. Não equivale ao custo médio oficial nem ao serviço da dívida pago em caixa.</p></div></div></article>
            <article class="panel data-jump"><div><span class="kicker">DADOS PARA REPRODUZIR</span><h3>Juros mensais e anuais da DPF</h3><p>Inclui juros da dívida interna, externa e total, com estoque médio usado no indicador aproximado.</p></div><button @click="activeData = 'interestAnnual'; go('explorer')">Abrir a tabela <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></article></div>
        </section>

        <section v-else-if="page === 'social'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> TRANSFERÊNCIA DE RENDA E PROTEÇÃO SOCIAL</div><h1>Programas sociais.<br /><em>Escala e cobertura.</em></h1><p>Série histórica do BPC e um retrato comparável dos principais repasses federais em 2024, com unidades e limites claramente identificados.</p></div><aside>ÚLTIMO ANO HISTÓRICO<strong>{{ socialLatest?.ano }}</strong></aside></div>
          <div class="metrics"><article class="metric metric-blue"><div class="metric-label">BPC · BENEFICIÁRIOS</div><strong>{{ pretty(socialLatest?.beneficiarios_total, 0) }}</strong><div class="metric-foot"><span>PCD e idosos</span><i>{{ socialLatest?.ano }} · MDS</i></div></article><article class="metric metric-teal"><div class="metric-label">BPC · REPASSES</div><strong>R$ {{ pretty(socialLatest?.repasse_total_brl / 1e9, 2) }} <small>bi</small></strong><div class="metric-foot"><span>Valores correntes</span><i>{{ socialLatest?.ano }} · VIS Data</i></div></article><article class="metric metric-gold"><div class="metric-label">BPC · CRESCIMENTO ANUAL</div><strong>{{ percent(bpcGrowth) }}</strong><div class="metric-foot"><span>Beneficiários</span><i>{{ socialLatest?.ano }} sobre {{ bpcPrevious?.ano }}</i></div></article><article class="metric metric-red"><div class="metric-label">AUXÍLIO GÁS · COBERTURA</div><strong>{{ pretty(data.social.auxilio_gas_2024.cobertura_media_ciclo / 1e6, 1) }} <small>mi</small></strong><div class="metric-foot"><span>Famílias por ciclo</span><i>Bimestral · 2024</i></div></article></div>
          <div class="stacked-panels"><article class="panel"><div class="panel-heading"><div><span class="kicker">BPC · {{ chartStart === '2012' ? '2012' : '2004' }}–{{ socialLatest?.ano }}</span><h3>Beneficiários por grupo</h3></div><span class="unit-pill">Milhões de pessoas</span></div><TrendChart :option="socialCoverageChart" :guide="chartGuides.bpc" height="340px"/><p class="panel-caption">O painel anual do MDS reporta grupos e total de beneficiários; a tabela histórica também registra repasses correntes.</p></article><article class="panel"><div class="panel-heading"><div><span class="kicker">TRANSFERÊNCIAS REPORTADAS · 2024</span><h3>Bolsa Família e BPC</h3></div><span class="unit-pill">R$ bilhões correntes</span></div><TrendChart :option="socialSpendChart" :guide="chartGuides.socialSpend" height="270px"/><p class="panel-caption">Bolsa Família: R$ 168,3 bi e mais de 20,86 milhões de famílias contempladas ao longo do ano. BPC: R$ 102,27 bi na série anual VIS Data. Fontes e perímetros contábeis podem diferir.</p></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">MÉTRICAS, EXEMPLO E LIMITES</span><h3>Como interpretar</h3></div></div><div class="method-row"><span>01</span><div><strong>BPC — cobertura e repasse</strong><p>Em {{ socialLatest?.ano }}, a base registra {{ pretty(socialLatest?.beneficiarios_total, 0) }} beneficiários e R$ {{ pretty(socialLatest?.repasse_total_brl / 1e9, 2) }} bilhões em repasses. A divisão dá aproximadamente R$ {{ pretty(bpcRepassePerBeneficiary, 0) }} por pessoa contada na referência anual; é apenas razão descritiva, não valor mensal individual.</p></div></div><div class="method-row"><span>02</span><div><strong>Bolsa Família — famílias</strong><p>O MDS informou mais de 20,86 milhões de famílias contempladas ao longo de 2024 e R$ 168,3 bilhões transferidos. A cobertura anual não deve ser interpretada como número simultâneo de famílias em um mês.</p></div></div><div class="method-row"><span>03</span><div><strong>Auxílio Gás — pagamento bimestral</strong><p>O MDS informa cobertura média de 5,7 milhões de famílias por ciclo entre fevereiro e dezembro de 2024. Ciclos não equivalem a famílias únicas no ano. Não somamos grupos de programas: além de unidades distintas, públicos podem se sobrepor.</p></div></div><div class="method-row"><span>04</span><div><strong>Valores nominais</strong><p>Repasses do BPC crescem com cobertura, reajuste do salário mínimo e preços. A série não está deflacionada e não mede impacto causal, redução da pobreza ou poder de compra.</p></div></div></article>
            <article class="panel data-jump"><div><span class="kicker">TABELAS FONTE</span><h3>Série anual e comparação de programas</h3><p>Dados agregados preservados no bundle do painel; não usamos CPF, NIS ou pagamentos individualizados.</p></div><button @click="activeData = 'bpcAnnual'; go('explorer')">Explorar as tabelas <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></article></div>
        </section>

        <section v-else-if="page === 'pib'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> CONTAS NACIONAIS TRIMESTRAIS · IBGE</div><h1>O PIB brasileiro.<br /><em>Valor e crescimento real.</em></h1><p>Contas Nacionais Trimestrais do Brasil, com valores nominais, taxas oficiais de volume e composição da produção e da despesa. A série disponível cobre {{ data.pib.source.period_start }} a {{ data.pib.source.period_end }}.</p></div><aside>ÚLTIMO TRIMESTRE<strong>{{ pibLatest?.trimestre }}</strong><small>Coleta {{ data.pib.source.collected_at.slice(0, 10) }}</small></aside></div>
          <div class="metrics">
            <article class="metric metric-blue"><div class="metric-label">PIB NOMINAL · {{ pibLatest?.trimestre }}</div><strong>R$ {{ pretty(pibLatest?.pib_nominal_milhoes / 1e6, 2) }} <small>tri</small></strong><div class="metric-foot"><span>Valores correntes</span><i>{{ percent(pibNominalGrowth) }} nominal em 12 meses</i></div></article>
            <article class="metric metric-teal"><div class="metric-label">CRESCIMENTO REAL · ANO CONTRA ANO</div><strong>{{ percent(pibLatest?.pib_yoy_percentual) }}</strong><div class="metric-foot"><span>{{ pibLatest?.trimestre }} sobre mesmo tri anterior</span><i>IBGE · índice de volume</i></div></article>
            <article class="metric metric-gold"><div class="metric-label">CRESCIMENTO REAL · TRIMESTRE</div><strong>{{ percent(pibLatest?.pib_qoq_sa_percentual) }}</strong><div class="metric-foot"><span>Contra trimestre anterior</span><i>Ajuste sazonal · IBGE</i></div></article>
            <article class="metric metric-red"><div class="metric-label">ACUMULADO EM QUATRO TRIMESTRES</div><strong>{{ percent(pibLatest?.pib_four_quarters_percentual) }}</strong><div class="metric-foot"><span>Comparado aos quatro anteriores</span><i>Taxa publicada pelo IBGE</i></div></article>
          </div>
          <div class="pib-period-control panel" role="group" aria-label="Período de agregação do PIB">
            <span>PERÍODO DOS GRÁFICOS</span>
            <button :class="{ active: pibPeriod === 'quarterly' }" @click="pibPeriod = 'quarterly'">Trimestre</button>
            <button :class="{ active: pibPeriod === 'semestre' }" @click="pibPeriod = 'semestre'">Semestre</button>
            <button :class="{ active: pibPeriod === 'ano' }" @click="pibPeriod = 'ano'">Ano</button>
          </div>
          <div class="stacked-panels">
            <article class="panel"><div class="panel-heading"><div><span class="kicker">{{ pibPeriod === 'quarterly' ? 'VALORES TRIMESTRAIS' : pibPeriod === 'semestre' ? 'SOMA DOS TRIMESTRES DO SEMESTRE' : 'SOMA DOS TRIMESTRES DO ANO' }} · R$ CORRENTES</span><h3>PIB nominal e atividade econômica</h3></div><span class="unit-pill">R$ trilhões correntes</span></div><TrendChart :option="pibNominalChart" :guide="chartGuides.pibNominal" height="350px"/><p class="panel-caption">Valores correntes refletem volume produzido e preços do período. Agropecuária e serviços aparecem junto ao PIB para dar escala; não se somam ao PIB.</p></article>
            <article class="panel"><div class="panel-heading"><div><span class="kicker">ÍNDICE DE VOLUME · VARIAÇÃO REAL</span><h3>Crescimento por setor</h3></div><span class="unit-pill">{{ pibPeriod === 'semestre' ? 'Derivado · mesmo semestre anterior' : pibPeriod === 'ano' ? 'Acumulado no ano · IBGE' : 'Mesmo trimestre anterior · IBGE' }}</span></div><TrendChart :option="pibGrowthChart" :guide="chartGuides.pibGrowth" height="350px"/><p class="panel-caption">No modo trimestral, crescimento ano contra ano e trimestre contra trimestre ajustado sazonalmente são comparações diferentes. Semestre usa comparação derivada com o semestre equivalente anterior.</p></article>
            <article class="panel"><div class="panel-heading"><div><span class="kicker">COMPONENTES DA DESPESA · VOLUME</span><h3>Consumo, investimento e setor externo</h3></div><span class="unit-pill">Variação real (%)</span></div><TrendChart :option="pibSpendingChart" :guide="chartGuides.pibSpending" height="350px"/><p class="panel-caption">As séries seguem as taxas por componente publicadas pelo IBGE. Importações entram na identidade do PIB com sinal negativo; a taxa do componente não deve ser interpretada como contribuição direta ao crescimento total.</p></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">MÉTRICAS, EXEMPLO E LIMITES</span><h3>Como ler as séries do PIB</h3></div></div>
              <div class="method-row"><span>01</span><div><strong>Nominal e real</strong><p>O valor nominal é o PIB em milhões de reais correntes. Sua variação combina mudança de quantidade e de preços. Para medir crescimento da produção, usamos índices de volume e taxas reais oficiais, que retiram a variação de preços.</p></div></div>
              <div class="method-row"><span>02</span><div><strong>Trimestre a trimestre com ajuste sazonal</strong><p>Compara o trimestre com o imediatamente anterior após ajuste sazonal do IBGE. Ajuda a observar a direção recente sem confundir padrões recorrentes do calendário com mudança de atividade.</p></div></div>
              <div class="method-row"><span>03</span><div><strong>Semestre e ano</strong><p>Os valores nominais são somados entre trimestres. Exemplo: o PIB de {{ pibLatest?.trimestre }} é R$ {{ pretty(pibLatest?.pib_nominal_milhoes / 1e6, 2) }} trilhões; a comparação nominal usa {{ pibSameQuarterLastYear?.trimestre }} (R$ {{ pretty(pibSameQuarterLastYear?.pib_nominal_milhoes / 1e6, 2) }} tri), resultando em {{ percent(pibNominalGrowth) }}. Para o semestre, a taxa real derivada compara a média dos índices encadeados dos dois trimestres com a média do semestre equivalente anterior; exige os dois trimestres em ambos os períodos e não é uma taxa semestral publicada pelo IBGE. O índice encadeado não representa nível monetário aditivo.</p></div></div>
              <div class="method-row"><span>04</span><div><strong>Acumulado no ano e em quatro trimestres</strong><p>São taxas publicadas pelo IBGE, não intercambiáveis com a variação trimestral. No gráfico anual, a taxa acumulada no ano vem do último trimestre disponível de cada ano; anos incompletos são mantidos como parciais.</p></div></div>
              <div class="method-row"><span>05</span><div><strong>Setores e componentes da despesa</strong><p>Agropecuária, indústria e serviços detalham a produção. Consumo das famílias e do governo, formação de capital, estoques, exportações e importações detalham a despesa. São perspectivas contábeis do mesmo PIB e não devem ser somadas umas às outras.</p></div></div>
              <div class="method-row"><span>06</span><div><strong>Revisões e preservação</strong><p>O IBGE revê a série quando incorpora fontes e resultados anuais do Sistema de Contas Nacionais. As respostas consultadas e a data da coleta ficam preservadas em <code>data/raw/ibge/</code>; esta visualização usa a versão mais recente coletada em {{ data.pib.source.collected_at.slice(0, 10) }}.</p></div></div>
            </article>
            <article class="panel data-jump"><div><span class="kicker">SÉRIE COMPLETA · 1996–2026</span><h3>Dados e fontes para reprodução</h3><p>122 trimestres, tabelas oficiais do SIDRA 1846, 1620 e 5932; arquivo bruto preservado e tabelas processadas disponíveis para download no explorador.</p></div><button @click="activeData = 'pibQuarterly'; go('explorer')">Explorar PIB <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></article>
          </div>
        </section>

        <section v-else-if="page === 'purchasingPower'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> IPCA · PODER DE COMPRA DO REAL</div><h1>O real desde 1994.<br /><em>O que a inflação mudou.</em></h1><p>Quanto os preços subiram desde a entrada em circulação do real e quanto do poder de compra original permanece, com base no IPCA oficial até {{ purchasingPowerLatest?.data }}.</p></div><aside>BASE DE COMPARAÇÃO<strong>Julho de 1994</strong><small>Atualizado até {{ purchasingPowerLatest?.data }}</small></aside></div>
          <div class="metrics">
            <article class="metric metric-blue"><div class="metric-label">INFLAÇÃO ACUMULADA DESDE 1994</div><strong>{{ percent(purchasingPowerLatest?.inflacao_acumulada_desde_jul_1994_percentual) }}</strong><div class="metric-foot"><span>IPCA composto</span><i>Jul/1994–{{ purchasingPowerLatest?.data }}</i></div></article>
            <article class="metric metric-red"><div class="metric-label">PODER DE COMPRA PERDIDO</div><strong>{{ percent(purchasingPowerLatest?.perda_poder_compra_percentual) }}</strong><div class="metric-foot"><span>De R$ 1 em jul/1994</span><i>Medida doméstica</i></div></article>
            <article class="metric metric-teal"><div class="metric-label">R$ 100 DE JULHO/1994</div><strong>R$ {{ pretty(purchasingPowerLatest?.preco_cesta_r_100_jul_1994, 2) }}</strong><div class="metric-foot"><span>Cesta-base equivalente</span><i>Valores correntes de {{ purchasingPowerLatest?.data }}</i></div></article>
            <article class="metric metric-gold"><div class="metric-label">IPCA DO ÚLTIMO MÊS</div><strong>{{ percent(purchasingPowerLatest?.ipca_mensal_percentual) }}</strong><div class="metric-foot"><span>{{ purchasingPowerLatest?.data }}</span><i>IBGE · Brasil</i></div></article>
          </div>
          <div class="stacked-panels">
            <article class="panel"><div class="panel-heading"><div><span class="kicker">PREÇOS ACUMULADOS · JULHO/1994 = 100</span><h3>Quanto custa hoje uma cesta de R$ 100 de 1994</h3></div><span class="unit-pill">R$ correntes</span></div><TrendChart :option="purchasingPowerChart" :guide="chartGuides.purchasingPower" height="390px"/><p class="panel-caption">O índice é construído pelas variações mensais do IPCA, com julho de 1994 como base e composição a partir de agosto. É uma referência média nacional de preços, não uma cesta fixa observada em lojas nem o custo de vida pessoal de cada família.</p></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">CÁLCULO, EXEMPLO E LIMITES</span><h3>Inflação não é o mesmo que perda de poder de compra</h3></div></div>
              <div class="method-row"><span>01</span><div><strong>Inflação acumulada</strong><p>As variações mensais são compostas: o fator total é o produto de (1 + IPCA do mês). Desde agosto de 1994, o fator acumulado é {{ pretty(purchasingPowerLatest?.indice_precos_jul_1994_100 / 100, 4) }}; isso corresponde a {{ percent(purchasingPowerLatest?.inflacao_acumulada_desde_jul_1994_percentual) }} de aumento no nível de preços medido pelo IPCA.</p></div></div>
              <div class="method-row"><span>02</span><div><strong>Perda do poder de compra</strong><p>A perda é calculada pelo inverso do aumento dos preços: 1 − (1 ÷ {{ pretty(purchasingPowerLatest?.indice_precos_jul_1994_100 / 100, 4) }}). Assim, R$ 1 mantém cerca de {{ percent(purchasingPowerLatest?.poder_compra_remanescente_percentual) }} do poder de compra que tinha na base; a perda é {{ percent(purchasingPowerLatest?.perda_poder_compra_percentual) }}. Esse percentual não é igual à inflação acumulada.</p></div></div>
              <div class="method-row"><span>03</span><div><strong>Exemplo em reais</strong><p>Uma cesta que custava R$ 100 em julho de 1994 custaria aproximadamente R$ {{ pretty(purchasingPowerLatest?.preco_cesta_r_100_jul_1994, 2) }} em {{ purchasingPowerLatest?.data }}, se seu preço tivesse acompanhado exatamente o IPCA médio. Esse exemplo serve para converter valores nominais de épocas diferentes, não para dizer quanto qualquer produto específico custa hoje.</p></div></div>
              <div class="method-row"><span>04</span><div><strong>Data-base e moeda</strong><p>O real entrou em circulação em 1º de julho de 1994. Julho é a base do índice; por isso, o acumulado começa com a variação de agosto, evitando incluir a inflação de junho para julho como se toda ela tivesse ocorrido sob o real. Esta análise trata do poder de compra interno, não da taxa de câmbio do real frente ao dólar ou outras moedas.</p></div></div>
              <div class="method-row"><span>05</span><div><strong>IPCA e experiência de cada família</strong><p>O IPCA representa uma cesta e uma população de referência nacionais. A inflação sentida por cada pessoa pode ser maior ou menor conforme renda, região e composição do consumo. O índice também pode ser revisto quando o IBGE corrige dados.</p><a href="https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html" target="_blank" rel="noreferrer">Metodologia e séries históricas do IPCA no IBGE <ExternalLink class="ui-icon" :size="12" /></a></div></div>
              <div class="method-row"><span>06</span><div><strong>O que estudar</strong><p>Índices de preços, inflação composta, números-índice, cesta de consumo, correção monetária, inflação pessoal e diferença entre preços, salários e taxa de câmbio.</p></div></div>
            </article>
            <article class="panel data-jump"><div><span class="kicker">SÉRIE MENSAL · {{ data.purchasing_power.source.period_start }}–{{ data.purchasing_power.source.period_end }}</span><h3>IPCA mensal usado no cálculo</h3><p>Variações mensais oficiais preservadas desde a base do real e série acumulada calculada pelo painel. Coleta em {{ data.purchasing_power.source.collected_at }}.</p></div><button @click="activeData = 'purchasingPowerMonthly'; go('explorer')">Explorar série <ArrowUpRight class="ui-icon" :size="12" /></button></article>
          </div>
        </section>

        <section v-else-if="page === 'taxes'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> ARRECADAÇÃO DAS RECEITAS FEDERAIS · RECEITA FEDERAL</div><h1>Impostos arrecadados.<br /><em>Um contador oficial.</em></h1><p>Arrecadação federal mensal em valores correntes, desde {{ data.taxes.source.period_start }}. O contador soma apenas os meses publicados no ano e é atualizado quando a Receita divulga novos resultados.</p></div><aside>ÚLTIMO MÊS PUBLICADO<strong>{{ month(taxLatest?.data) }}</strong><small>Coleta {{ data.taxes.source.collected_at }}</small></aside></div>
          <div class="metrics">
            <article class="metric metric-blue"><div class="metric-label">ACUMULADO FEDERAL · {{ taxLatest?.ano }}</div><strong>R$ {{ pretty(taxAnnualRunning / 1e6, 3) }} <small>tri</small></strong><div class="metric-foot"><span>Jan–{{ String(taxLatest?.mes).padStart(2, '0') }}/{{ taxLatest?.ano }}</span><i>Total geral · valores correntes</i></div></article>
            <article class="metric metric-teal"><div class="metric-label">ARRECADAÇÃO NO MÊS</div><strong>R$ {{ pretty(taxLatest?.arrecadacao_total_federal_milhoes / 1000, 2) }} <small>bi</small></strong><div class="metric-foot"><span>{{ month(taxLatest?.data) }}</span><i>RFB + outros órgãos</i></div></article>
            <article class="metric metric-gold"><div class="metric-label">VARIAÇÃO NOMINAL · 12 MESES</div><strong>{{ percent(taxYoy) }}</strong><div class="metric-foot"><span>Mesmo mês do ano anterior</span><i>Sem descontar inflação</i></div></article>
            <article class="metric metric-red"><div class="metric-label">CARGA TRIBUTÁRIA · GOVERNO GERAL</div><strong>{{ percent(taxGeneralLatest?.governo_geral_percentual_pib) }}</strong><div class="metric-foot"><span>União, estados e municípios</span><i>{{ taxGeneralLatest?.ano }} · Tesouro Nacional</i></div></article>
          </div>
          <div class="stacked-panels">
            <article class="panel"><div class="panel-heading"><div><span class="kicker">{{ data.taxes.source.period_start }} — {{ data.taxes.source.period_end }} · VALORES NOMINAIS</span><h3>Arrecadação federal por mês</h3></div><span class="unit-pill">R$ bilhões correntes</span></div><TrendChart :option="taxMonthlyChart" :guide="chartGuides.taxes" height="360px"/><p class="panel-caption">A linha “Total federal” inclui receitas administradas pela Receita Federal e por outros órgãos. A parcela administrada pela RFB está disponível no detalhamento mais recente (2021 em diante). Valores não corrigidos pela inflação.</p></article>
            <article class="panel"><div class="panel-heading"><div><span class="kicker">CARGA TRIBUTÁRIA BRUTA · 2010–{{ taxGeneralLatest?.ano }}</span><h3>Tributos arrecadados em relação ao PIB</h3></div><span class="unit-pill">Percentual do PIB</span></div><TrendChart :option="taxBurdenChart" :guide="chartGuides.taxBurden" height="340px"/><p class="panel-caption">Indicador anual do Governo Geral, que soma as esferas federal, estadual e municipal. É uma medida de carga tributária do sistema público inteiro, não um complemento mensal da arrecadação federal.</p></article>
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">MÉTRICA, EXEMPLO E LIMITES</span><h3>Como funciona o contador</h3></div></div>
              <div class="method-row"><span>01</span><div><strong>Acumulado observado</strong><p>O contador exibe R$ {{ pretty(taxAnnualRunning / 1e6, 3) }} trilhões de arrecadação federal entre janeiro e {{ month(taxLatest?.data) }} de {{ taxLatest?.ano }}. É a soma dos valores mensais já divulgados, sem projeção diária e sem estimar dias ainda não publicados.</p></div></div>
              <div class="method-row"><span>02</span><div><strong>O que entra no total federal</strong><p>A série histórica da Receita Federal define o total como receitas administradas pela RFB mais receitas administradas por outros órgãos. A planilha histórica cobre 1994–2025; para 2021 em diante usamos os dados mensais do anexo mais recente, que também detalha as duas parcelas.</p></div></div>
              <div class="method-row"><span>03</span><div><strong>Valores nominais e inflação</strong><p>Os valores são nominais. A variação de {{ percent(taxYoy) }} em 12 meses compara {{ month(taxLatest?.data) }} com o mesmo mês do ano anterior e mistura mudanças de preços, atividade econômica, alíquotas e regras. Não representa crescimento real da carga.</p></div></div>
              <div class="method-row"><span>04</span><div><strong>Carga tributária bruta</strong><p>O Tesouro Nacional calcula a carga tributária do Governo Geral por esfera e como proporção do PIB. É uma série anual consolidada — em {{ taxGeneralLatest?.ano }}, {{ percent(taxGeneralLatest?.governo_geral_percentual_pib) }} do PIB — com escopo diferente da arrecadação mensal federal.</p></div></div>
              <div class="method-row"><span>05</span><div><strong>Revisões e atualização</strong><p>A Receita pode revisar os dados históricos e publica relatórios mensais. O material bruto consultado fica em <code>data/raw/tributos/</code> e a data de coleta é registrada acima. Para atualizar no futuro, substitua os arquivos oficiais e rode <code>uv run python scripts/processar_impostos.py</code> e <code>uv run python web/scripts/build_data.py</code>.</p></div></div>
            </article>
            <article class="panel data-jump"><div><span class="kicker">SÉRIES COMPLETAS · 1994–2026</span><h3>Dados para explorar e baixar</h3><p>Arrecadação federal mensal e anual, detalhamento por esfera e carga tributária bruta do Governo Geral.</p></div><button @click="activeData = 'taxesMonthly'; go('explorer')">Explorar dados <b><ArrowUpRight class="ui-icon" :size="12" :stroke-width="2" /></b></button></article>
          </div>
        </section>

        <section v-else-if="page === 'explorer'" class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> EXPLORADOR DE DADOS</div><h1>Os dados, <em>em detalhe.</em></h1><p>Pesquise, percorra e baixe as tabelas que alimentam este painel.</p></div></div>
          <div class="explorer-controls panel">
            <label><span>CONJUNTO DE DADOS</span><select v-model="activeData"><option v-for="(item, id) in datasets" :key="id" :value="id">{{ item.label }}</option></select></label>
            <label class="search-box"><span>BUSCAR</span><div><Search class="ui-icon" :size="14" /><input v-model="search" type="search" placeholder="Data, indicador, função ou valor" /></div></label>
            <button class="download-button" :disabled="activeData === 'titles' && !detailLoaded" @click="exportTable"><Download class="ui-icon" :size="15" /> Baixar dados</button>
          </div>
          <div v-if="activeData === 'titles' && detailLoading" class="loading-row panel"><span class="spinner"></span> Preparando as posições individuais por título…</div>
          <article class="table-panel panel">
            <div class="table-header"><div><strong>{{ dataset.label }}</strong><span>{{ filteredRows.length.toLocaleString('pt-BR') }} registros<template v-if="search"> · filtrados</template></span></div><small>Página {{ pageNumber }} / {{ totalPages }}</small></div>
            <div class="table-scroll"><table><thead><tr><th v-for="key in columns" :key="key">{{ key }}</th></tr></thead><tbody><tr v-for="(row, index) in visibleRows" :key="index"><td v-for="key in columns" :key="key" :class="{ numeric: typeof row[key] === 'number' }">{{ typeof row[key] === 'number' ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(row[key]) : row[key] ?? '—' }}</td></tr><tr v-if="visibleRows.length === 0"><td :colspan="columns.length" class="empty-row">Nenhum registro encontrado.</td></tr></tbody></table></div>
            <div class="table-footer"><span>{{ filteredRows.length ? (pageNumber - 1) * pageSize + 1 : 0 }}–{{ Math.min(pageNumber * pageSize, filteredRows.length) }} de {{ filteredRows.length.toLocaleString('pt-BR') }}</span><div><button :disabled="pageNumber <= 1" @click="pageNumber--"><ArrowLeft class="ui-icon" :size="13" /> Anterior</button><button :disabled="pageNumber >= totalPages" @click="pageNumber++">Próxima <ArrowRight class="ui-icon" :size="13" /></button></div></div>
          </article>
          <p class="table-explainer">As tabelas preservam as unidades dos arquivos tratados. Séries financeiras usam R$ bilhões; posições individuais incluem valores em reais. O seletor “Posições individuais” carrega cerca de 165 mil linhas ao ser aberto.</p>
        </section>

        <section v-else class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> TRANSPARÊNCIA E CONTEXTO</div><h1>De onde vêm <em>os dados.</em></h1><p>Fontes primárias, perímetros e decisões de leitura usados no painel.</p></div></div>
          <div class="sources-layout">
            <article class="panel methods"><div class="panel-heading"><div><span class="kicker">COMO LER</span><h3>Conceitos com escopos diferentes</h3></div></div>
              <div class="method-row"><span>01</span><div><strong>Dívida Pública Federal (DPF)</strong><p>Estoque sob responsabilidade do Tesouro Nacional, separado entre dívida interna e externa. Série agregada mensal desde dezembro de 2000.</p></div></div>
              <div class="method-row"><span>02</span><div><strong>Juros apropriados na DPF</strong><p>Valor por competência publicado pelo Tesouro nos fatores de variação da dívida. É diferente de pagamento em caixa. A taxa apresentada é uma razão aproximada sobre o estoque médio anual, não o custo médio oficial da DPF.</p><a href="https://www.tesourotransparente.gov.br/ckan/dataset/fatores-de-variacao-da-divida-publica-federal" target="_blank" rel="noreferrer">Fatores de variação da DPF <ExternalLink class="ui-icon" :size="12" /></a></div></div>
              <div class="method-row"><span>03</span><div><strong>DBGG e dívida líquida / PIB</strong><p>Séries do Banco Central que abrangem o governo geral, incluindo níveis subnacionais. Não são equivalentes à DPF.</p></div></div>
              <div class="method-row"><span>04</span><div><strong>PIB — Contas Nacionais Trimestrais</strong><p>Valores correntes, índices encadeados de volume e taxas publicadas pelo IBGE. Crescimento nominal não é crescimento real. A série DBGG/PIB continua sendo o indicador publicado pelo Banco Central e não é recalculada com os valores do PIB desta página.</p><a href="https://sidra.ibge.gov.br/pesquisa/cnt/tabelas" target="_blank" rel="noreferrer">Tabelas do IBGE/SIDRA <ExternalLink class="ui-icon" :size="12" /></a></div></div>
              <div class="method-row"><span>05</span><div><strong>Arrecadação federal e carga tributária</strong><p>A série mensal da Receita Federal soma receitas administradas pela RFB e por outros órgãos; o acumulado é apenas a soma dos meses publicados, sem projeção. A carga tributária do Tesouro é anual e cobre Governo Geral (União, estados e municípios), com escopo distinto.</p><a href="https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/serie-historica" target="_blank" rel="noreferrer">Série histórica da Receita Federal <ExternalLink class="ui-icon" :size="12" /></a></div></div>
              <div class="method-row"><span>03</span><div><strong>Execução por função</strong><p>Pagamentos do orçamento federal nas funções Saúde, Educação e Segurança Pública. Inclui gastos correntes e de capital.</p></div></div>
              <div class="method-row"><span>04</span><div><strong>GND 4 — Investimentos</strong><p>Classificação de investimento de capital no orçamento. É um subconjunto do total pago na função, não um indicador de resultado.</p></div></div>
              <div class="method-row"><span>05</span><div><strong>Programas sociais agregados</strong><p>A série anual do BPC separa pessoas com deficiência e pessoas idosas, com beneficiários e repasses. Bolsa Família é reportado em famílias; Auxílio Gás, por famílias atendidas em ciclos bimestrais. As unidades não são intercambiáveis e os públicos podem se sobrepor.</p></div></div>
              <div class="method-row"><span>06</span><div><strong>Repasses sociais e valores reais</strong><p>O histórico do BPC está em valores nominais. A página social não o soma ao Bolsa Família nem ao Auxílio Gás e evita inferir efeito sobre pobreza ou bem-estar a partir do volume transferido.</p></div></div>
            </article>
            <div class="source-stack"><article v-for="(source, index) in data.sources" :key="source.name" class="source-card"><span>{{ String(index + 1).padStart(2, '0') }}</span><div><strong>{{ source.name }}</strong><small>Dados oficiais · fonte primária</small></div><a :href="source.url" target="_blank" rel="noreferrer" :aria-label="`Abrir fonte: ${source.name}`"><ExternalLink class="ui-icon" :size="13" /></a></article></div>
          </div>
          <div class="source-footer"><b><Info class="ui-icon" :size="14" /></b><p>Os dados tratados e os arquivos brutos ficam no diretório <code>data/</code>. A série do PIB foi coletada em {{ data.pib.source.collected_at.slice(0, 10) }}; outros conjuntos têm suas próprias datas de atualização. As fontes podem retificar as séries. O código GND 4 corresponde à rubrica Investimentos no orçamento federal.</p></div>
        </section>
      </template>
      <footer v-if="data" class="footer"><span>INSIGHTS PÚBLICOS · BRASIL</span><span>Dados oficiais para análise independente</span><span>1996 — 2026</span></footer>
    </main>
  </div>
</template>
