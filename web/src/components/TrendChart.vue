<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { ArrowLeft, ArrowRight } from "@lucide/vue";
import { formatPeriodLabel, readableChartOption } from "../charts/readableChartOption.js";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, DataZoomComponent, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: "340px" },
  guide: { type: Object, required: true },
});
const root = ref(null);
const zoomRange = ref(null);
const readableOption = computed(() => readableChartOption(props.option));
const periodValues = computed(() => {
  const xAxis = Array.isArray(readableOption.value.xAxis) ? readableOption.value.xAxis[0] : readableOption.value.xAxis;
  if (Array.isArray(xAxis?.data)) return xAxis.data.map(String);
  const points = (readableOption.value.series || []).flatMap((series) => Array.isArray(series.data) ? series.data : []);
  return [...new Set(points.map((point) => Array.isArray(point) ? String(point[0]) : String(point)))].sort();
});
const visiblePeriodLabel = computed(() => {
  if (!zoomRange.value || !readableOption.value.dataZoom) return "";
  const periods = periodValues.value;
  if (!periods.length) return "";
  const first = Math.max(0, Math.floor((zoomRange.value.start / 100) * periods.length));
  const last = Math.min(periods.length - 1, Math.max(first, Math.ceil((zoomRange.value.end / 100) * periods.length) - 1));
  return `${formatPeriodLabel(periods[first])}–${formatPeriodLabel(periods[last])} · ${last - first + 1} períodos`;
});
let chart;
let observer;
function updateZoomRange(event) {
  const range = event.batch?.[0] || event;
  if (Number.isFinite(range.start) && Number.isFinite(range.end)) {
    zoomRange.value = { start: range.start, end: range.end };
  }
}
function pagePeriods(direction) {
  if (!chart || !zoomRange.value) return;
  const { start, end } = zoomRange.value;
  const span = end - start;
  let nextStart = Math.max(0, Math.min(100 - span, start + direction * span * 0.8));
  let nextEnd = nextStart + span;
  if (direction > 0 && nextEnd > 100) {
    nextEnd = 100;
    nextStart = 100 - span;
  }
  chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 1, start: nextStart, end: nextEnd });
}
onMounted(() => {
  chart = echarts.init(root.value);
  chart.setOption(readableOption.value);
  if (readableOption.value.dataZoom) {
    const slider = readableOption.value.dataZoom[1];
    zoomRange.value = { start: slider.start, end: slider.end };
    chart.on("datazoom", updateZoomRange);
  }
  observer = new ResizeObserver(() => {
    chart?.resize();
  });
  observer.observe(root.value);
});
watch(readableOption, (option) => {
  if (!chart) return;
  chart.setOption(option, true);
  zoomRange.value = option.dataZoom ? { start: option.dataZoom[1].start, end: option.dataZoom[1].end } : null;
  chart.off("datazoom", updateZoomRange);
  if (option.dataZoom) chart.on("datazoom", updateZoomRange);
}, { deep: true });
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.off("datazoom", updateZoomRange);
  chart?.dispose();
});
</script>

<template>
  <div class="chart-visual-wrap">
    <div ref="root" class="trend-chart" :style="{ height }" role="img" :aria-label="guide.title"></div>
    <nav v-if="readableOption.dataZoom" class="period-navigation" aria-label="Navegar pelos períodos do gráfico">
      <button type="button" :disabled="zoomRange?.start <= 0" aria-label="Mostrar períodos anteriores" @click="pagePeriods(-1)"><ArrowLeft class="ui-icon" :size="16" /></button>
      <span>{{ visiblePeriodLabel }}</span>
      <button type="button" :disabled="zoomRange?.end >= 100" aria-label="Mostrar períodos seguintes" @click="pagePeriods(1)"><ArrowRight class="ui-icon" :size="16" /></button>
    </nav>
    <div class="chart-guide">
      <p v-if="readableOption.dataZoom" class="period-navigation-hint">Use a faixa, as setas do gráfico ou o gesto de arrastar para percorrer os períodos. Todas as observações permanecem disponíveis.</p>
      <p class="chart-guide-summary">{{ guide.summary || guide.interpretation }}</p>
      <details>
        <summary>Interpretação, método e referências</summary>
        <div class="chart-guide-content">
          <section><h3>O que representa</h3><p>{{ guide.represents }}</p></section>
          <section><h3>Como interpretar</h3><p>{{ guide.interpretation }}</p></section>
          <section><h3>Por que importa</h3><p>{{ guide.importance }}</p></section>
          <section class="chart-guide-study"><h3>O que estudar para entender melhor</h3><p>{{ guide.study }}</p></section>
          <section><h3>Fontes e referências</h3><p>Consulte os links oficiais, datas de coleta e limitações reunidos em <RouterLink :to="{ name: 'sources' }">Fontes e método</RouterLink>.</p></section>
        </div>
      </details>
    </div>
  </div>
</template>
