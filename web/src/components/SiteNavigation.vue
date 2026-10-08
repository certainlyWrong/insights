<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";
import { ChartNoAxesCombined, X } from "@lucide/vue";

const props = defineProps({
  menu: { type: Array, required: true },
  activePage: { type: String, required: true },
  updated: { type: String, default: "" },
  open: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);
const root = ref(null);
function focusFirstLink() { root.value?.querySelector("nav a")?.focus(); }
function trapFocus(event) {
  if (!props.open) return;
  const focusable = [...root.value.querySelectorAll("a[href], button:not([disabled])")];
  const edge = event.shiftKey ? focusable[0] : focusable.at(-1);
  if (edge === document.activeElement) {
    event.preventDefault();
    (event.shiftKey ? focusable.at(-1) : focusable[0])?.focus();
  }
}
defineExpose({ focusFirstLink });
</script>

<template>
  <button v-if="open" class="navigation-backdrop" type="button" aria-label="Fechar navegação" @click="emit('close')"></button>
  <aside id="primary-navigation" ref="root" class="sidebar" :class="{ 'mobile-open': open }" aria-label="Navegação do painel" @keydown.tab="trapFocus">
      <button class="sidebar-close-button" type="button" aria-label="Fechar navegação" @click="emit('close')"><X class="ui-icon" :size="17" :stroke-width="1.8" /></button>
      <RouterLink class="brand" :to="{ name: 'overview' }" aria-label="Insights Brasil — Visão Geral" title="Visão Geral" @click="emit('close')">
        <div class="brand-symbol"><ChartNoAxesCombined class="ui-icon" :size="19" :stroke-width="1.8" /></div>
        <div><b>INSIGHTS</b><small>BRASIL · DADOS PÚBLICOS</small></div>
      </RouterLink>
      <div class="side-label">PAINEL</div>
      <nav class="side-nav" aria-label="Navegação principal">
        <RouterLink
          v-for="item in menu"
          :key="item.id"
          :to="item.path"
          class="side-nav-link"
          :class="{ active: activePage === item.id }"
          :aria-label="item.label"
          :title="item.label"
          :data-label="item.label"
          :aria-current="activePage === item.id ? 'page' : undefined"
          @click="emit('close')"
        >
          <span class="nav-glyph"><component :is="item.icon" class="ui-icon" :size="17" :stroke-width="1.8" /></span>
          <span>{{ item.label }}</span>
          <i v-if="activePage === item.id" class="active-mark"></i>
        </RouterLink>
      </nav>
      <div class="sidebar-bottom">
        <div class="federal-badge"><span>RECORTE ATUAL</span><strong>Governo Federal</strong><small>Brasil · fontes oficiais</small></div>
        <div class="sync-status"><i></i> Dados compilados <span>{{ updated ? updated.split("-").reverse().join(".") : "—" }}</span></div>
      </div>
  </aside>
</template>
