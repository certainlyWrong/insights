<script setup>
import { nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, toRefs, watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import {
  BadgeCheck, ChartNoAxesCombined, Info, PanelLeftClose, PanelLeftOpen,
} from "@lucide/vue";
import SiteNavigation from "./components/SiteNavigation.vue";
import { useDashboard } from "./composables/useDashboard.js";

const state = reactive(useDashboard());
provide("dashboard", state);
const { menu, page, navLabel, theme, data, error } = toRefs(state);
const route = useRoute();
const menuOpen = ref(false);
const sidebarCollapsed = ref(false);
const menuButton = ref(null);
const sidebar = ref(null);
const themePicker = ref(null);
const themePickerButton = ref(null);
const themePickerOpen = ref(false);
const themeOptions = [
  { id: "light", label: "Claro" },
  { id: "dark", label: "Escuro" },
  { id: "coffee", label: "Café" },
  { id: "forest", label: "Floresta" },
];

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem("insights-sidebar-collapsed", String(sidebarCollapsed.value));
}
function closeMenu() { menuOpen.value = false; }
function handleEscape() { closeMenu(); }
async function openThemePicker() {
  themePickerOpen.value = !themePickerOpen.value;
  if (themePickerOpen.value) {
    await nextTick();
    themePicker.value?.querySelector('[role="menuitemradio"][aria-checked="true"]')?.focus();
  }
}
function closeThemePicker(restoreFocus = false) {
  themePickerOpen.value = false;
  if (restoreFocus) nextTick(() => themePickerButton.value?.focus());
}
function selectTheme(value) {
  state.setTheme(value);
  closeThemePicker(true);
}
function handleThemeMenuKeydown(event) {
  const items = [...themePicker.value.querySelectorAll('[role="menuitemradio"]')];
  const current = items.indexOf(document.activeElement);
  let next = current;
  if (event.key === "ArrowDown") next = (current + 1) % items.length;
  else if (event.key === "ArrowUp") next = (current - 1 + items.length) % items.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = items.length - 1;
  else if (event.key === "Escape") { event.preventDefault(); closeThemePicker(true); return; }
  else if (event.key === "Tab") { closeThemePicker(); return; }
  else return;
  event.preventDefault();
  items[next]?.focus();
}
function handleOutsideThemeClick(event) {
  if (themePickerOpen.value && !themePicker.value?.contains(event.target)) closeThemePicker();
}

onMounted(() => {
  sidebarCollapsed.value = localStorage.getItem("insights-sidebar-collapsed") === "true";
  document.addEventListener("pointerdown", handleOutsideThemeClick);
});
onBeforeUnmount(() => document.removeEventListener("pointerdown", handleOutsideThemeClick));

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
  <div class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }" @keydown.esc.window="handleEscape">
    <SiteNavigation
      ref="sidebar"
      :menu="menu"
      :active-page="page"
      :updated="data?.updated"
      :open="menuOpen"
      :collapsed="sidebarCollapsed"
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
          <button
            class="sidebar-toggle-button"
            type="button"
            :aria-label="sidebarCollapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'"
            :aria-expanded="!sidebarCollapsed"
            aria-controls="primary-navigation"
            :title="sidebarCollapsed ? 'Expandir menu' : 'Recolher menu'"
            @click="toggleSidebar"
          >
            <component :is="sidebarCollapsed ? PanelLeftOpen : PanelLeftClose" class="ui-icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
          </button>
          <span class="official-badge"><BadgeCheck class="ui-icon" :size="14" :stroke-width="1.9" /> Fontes oficiais</span>
          <div ref="themePicker" class="theme-picker">
            <button
              ref="themePickerButton"
              class="theme-button"
              type="button"
              aria-label="Tema visual"
              aria-haspopup="menu"
              :aria-expanded="themePickerOpen"
              aria-controls="theme-menu"
              @click="openThemePicker"
            >
              <span class="theme-swatch" :class="`theme-swatch-${theme}`" aria-hidden="true"></span>
              <span>{{ themeOptions.find((option) => option.id === theme)?.label }}</span>
              <span class="theme-chevron" aria-hidden="true"></span>
            </button>
            <div v-if="themePickerOpen" id="theme-menu" class="theme-menu" role="menu" aria-label="Escolher tema" @keydown="handleThemeMenuKeydown">
              <span class="theme-menu-heading">APARÊNCIA</span>
              <button
                v-for="option in themeOptions"
                :key="option.id"
                class="theme-menu-option"
                :class="{ selected: theme === option.id }"
                type="button"
                role="menuitemradio"
                :aria-checked="theme === option.id"
                @click="selectTheme(option.id)"
              >
                <span class="theme-swatch" :class="`theme-swatch-${option.id}`" aria-hidden="true"></span>
                <span>{{ option.label }}</span>
                <span v-if="theme === option.id" class="theme-option-check" aria-hidden="true">✓</span>
              </button>
            </div>
          </div>
          <button class="info-button" type="button" aria-label="Fontes e método" title="Fontes e método" @click="state.go('sources')"><Info class="ui-icon" :size="14" :stroke-width="1.8" /></button>
        </div>
      </header>

      <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
      <div v-else-if="!data" class="loading-screen" role="status" aria-live="polite"><span class="spinner"></span><p>Carregando as séries públicas…</p></div>
      <RouterView v-else />

      <footer v-if="data" class="footer"><span>INSIGHTS PÚBLICOS · BRASIL</span><span>Dados oficiais para análise independente</span><span>1996 — 2026</span></footer>
    </main>
  </div>
</template>
