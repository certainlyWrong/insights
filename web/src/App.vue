<script setup>
import { nextTick, provide, reactive, ref, toRefs, watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import {
  BadgeCheck, ChartNoAxesCombined, Info, Moon, Sun,
} from "@lucide/vue";
import SiteNavigation from "./components/SiteNavigation.vue";
import { useDashboard } from "./composables/useDashboard.js";

const state = reactive(useDashboard());
provide("dashboard", state);
const { menu, page, navLabel, theme, data, error, chartStart } = toRefs(state);
const route = useRoute();
const menuOpen = ref(false);
const menuButton = ref(null);
const sidebar = ref(null);
const chartPages = ["overview", "debt", "interest", "spending", "social", "pib", "taxes", "purchasingPower"];

function toggleTheme() { state.toggleTheme(); }
function closeMenu() { menuOpen.value = false; }
function handleEscape() { closeMenu(); }

watch(menuOpen, async (open, wasOpen) => {
  document.body.classList.toggle("menu-is-open", open);
  await nextTick();
  if (open) sidebar.value?.focusFirstLink();
  else if (wasOpen) menuButton.value?.focus();
});
watch(() => route.path, async () => {
  closeMenu();
  await nextTick();
  document.querySelector(".content h1")?.focus({ preventScroll: true });
});
watch(() => route.meta.title, (title) => {
  document.title = title ? `${title} · Insights Brasil` : "Insights Brasil";
}, { immediate: true });
</script>

<template>
  <div class="app-shell" @keydown.esc.window="handleEscape">
    <SiteNavigation
      ref="sidebar"
      :menu="menu"
      :active-page="page"
      :updated="data?.updated"
      :open="menuOpen"
      @close="closeMenu"
    />

    <main class="main-area" :inert="menuOpen">
      <header class="topbar">
        <button
          ref="menuButton"
          class="mobile-menu-button"
          type="button"
          aria-controls="primary-navigation"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          <span class="mobile-menu-lines" aria-hidden="true"><i></i><i></i><i></i></span>
          <span class="sr-only">{{ menuOpen ? "Fechar navegação" : "Abrir navegação" }}</span>
        </button>
        <div class="mobile-brand"><div class="brand-symbol"><ChartNoAxesCombined class="ui-icon" :size="19" :stroke-width="1.8" /></div><b>INSIGHTS BRASIL</b></div>
        <div class="breadcrumb"><span>Brasil</span><i>/</i><strong>{{ navLabel }}</strong></div>
        <div class="top-actions">
          <span class="official-badge"><BadgeCheck class="ui-icon" :size="14" :stroke-width="1.9" /> Fontes oficiais</span>
          <button class="theme-button" :aria-label="theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'" :aria-pressed="theme === 'dark'" @click="toggleTheme">
            <component :is="theme === 'dark' ? Sun : Moon" class="ui-icon" :size="15" :stroke-width="1.9" aria-hidden="true" />
            <b>{{ theme === 'dark' ? 'Claro' : 'Escuro' }}</b>
          </button>
          <button class="info-button" type="button" aria-label="Fontes e método" title="Fontes e método" @click="state.go('sources')"><Info class="ui-icon" :size="14" :stroke-width="1.8" /></button>
        </div>
      </header>

      <div v-if="data && chartPages.includes(page)" class="chart-range-control" role="group" aria-label="Período inicial dos gráficos">
        <span>INÍCIO DOS GRÁFICOS</span>
        <button type="button" :class="{ active: chartStart === 'all' }" :aria-pressed="chartStart === 'all'" @click="chartStart = 'all'">Histórico completo</button>
        <button type="button" :class="{ active: chartStart === '2012' }" :aria-pressed="chartStart === '2012'" @click="chartStart = '2012'">Desde 2012</button>
      </div>

      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
      <div v-else-if="!data" class="loading-screen" role="status" aria-live="polite"><span class="spinner"></span><p>Carregando as séries públicas…</p></div>
      <RouterView v-else />

      <footer v-if="data" class="footer"><span>INSIGHTS PÚBLICOS · BRASIL</span><span>Dados oficiais para análise independente</span><span>1996 — 2026</span></footer>
    </main>
  </div>
</template>
