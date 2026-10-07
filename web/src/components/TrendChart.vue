<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { CircleHelp, X } from "@lucide/vue";
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
const dialogRoot = ref(null);
let chart;
let observer;
function openGuide() { dialogRoot.value?.showModal(); }
function closeGuide() { dialogRoot.value?.close(); }
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
    <button class="chart-guide-button" type="button" aria-haspopup="dialog" @click="openGuide"><CircleHelp class="ui-icon" :size="14" :stroke-width="1.8" /> Entenda este gráfico</button>
    <dialog ref="dialogRoot" class="chart-guide-dialog" @click.self="closeGuide">
      <div class="chart-guide-content">
        <header><div><span class="kicker">GUIA DE LEITURA DO GRÁFICO</span><h2>{{ guide.title }}</h2></div><button class="chart-guide-close" type="button" aria-label="Fechar explicação" @click="closeGuide"><X class="ui-icon" :size="17" /></button></header>
        <section><h3>O que representa</h3><p>{{ guide.represents }}</p></section>
        <section><h3>Como interpretar</h3><p>{{ guide.interpretation }}</p></section>
        <section><h3>Por que importa</h3><p>{{ guide.importance }}</p></section>
        <section class="chart-guide-study"><h3>O que estudar para entender melhor</h3><p>{{ guide.study }}</p></section>
        <footer><span>Leia junto com a unidade, o período e a fonte indicados no painel.</span><button type="button" @click="closeGuide">Entendi</button></footer>
      </div>
    </dialog>
  </div>
</template>
