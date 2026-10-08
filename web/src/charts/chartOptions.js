import { computed } from "vue";

export function createChartOptions({ data, chartTheme, palette, includesChartStart, pretty, percent, realFactor, pibPeriod, pibQuarterly, taxMonthly, purchasingPowerRows }) {
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
  return { tooltip, baseXAxis, baseYAxis, debtChart, macroChart, factorsChart, interestChart, spendingChart, spendingTrend, capitalTrend, overviewTrend, socialCoverageChart, socialSpendChart, pibNominalChart, pibGrowthRows, pibRateField, pibGrowthChart, pibSpendingChart, taxMonthlyChart, taxBurdenChart, purchasingPowerChart };
}
