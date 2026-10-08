import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "overview", component: () => import("../pages/overviewPage.vue"), meta: { page: "overview", title: "Visão geral" } },
  { path: "/divida-publica", name: "debt", component: () => import("../pages/debtPage.vue"), meta: { page: "debt", title: "Dívida pública" } },
  { path: "/juros-da-divida", name: "interest", component: () => import("../pages/interestPage.vue"), meta: { page: "interest", title: "Juros da dívida" } },
  { path: "/pib", name: "pib", component: () => import("../pages/pibPage.vue"), meta: { page: "pib", title: "PIB" } },
  { path: "/poder-de-compra", name: "purchasingPower", component: () => import("../pages/purchasingPowerPage.vue"), meta: { page: "purchasingPower", title: "Poder de compra" } },
  { path: "/impostos", name: "taxes", component: () => import("../pages/taxesPage.vue"), meta: { page: "taxes", title: "Impostômetro" } },
  { path: "/inflacao-dos-alimentos", name: "foodInflation", component: () => import("../pages/foodInflationPage.vue"), meta: { page: "foodInflation", title: "Inflação dos alimentos" } },
  { path: "/orcamento-federal", name: "spending", component: () => import("../pages/spendingPage.vue"), meta: { page: "spending", title: "Orçamento federal" } },
  { path: "/programas-sociais", name: "social", component: () => import("../pages/socialPage.vue"), meta: { page: "social", title: "Programas sociais" } },
  { path: "/explorar-dados", name: "explorer", component: () => import("../pages/explorerPage.vue"), meta: { page: "explorer", title: "Explorar dados" } },
  { path: "/fontes-e-metodo", name: "sources", component: () => import("../pages/sourcesPage.vue"), meta: { page: "sources", title: "Fontes e método" } },
  { path: "/:pathMatch(.*)*", name: "notFound", component: () => import("../pages/notFoundPage.vue"), meta: { page: "notFound", title: "Página não encontrada" } },
];

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    return to.path === from.path ? false : { top: 0, behavior: "smooth" };
  },
});
