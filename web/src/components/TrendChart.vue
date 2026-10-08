<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: "340px" },
  guide: { type: Object, required: true },
});
const root = ref(null);
let chart;
let observer;
onMounted(() => {
  chart = echarts.init(root.value);
  chart.setOption(props.option);
  observer = new ResizeObserver(() => chart?.resize());
  observer.observe(root.value);
});
watch(() => props.option, (option) => chart?.setOption(option, true), { deep: true });
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
});
</script>

<template>
  <div class="chart-visual-wrap">
    <div ref="root" class="trend-chart" :style="{ height }" role="img" :aria-label="guide.title"></div>
    <div class="chart-guide">
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
