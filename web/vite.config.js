import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  // O projeto é publicado em https://<usuario>.github.io/insights/ no Pages.
  // Localmente, o Vite continua servindo a partir da raiz.
  base: process.env.GITHUB_ACTIONS ? "/insights/" : "/",
  plugins: [vue()],
  // Vite recognizes many static formats automatically, but .gz needs to be
  // explicitly marked as an asset for imports to work in the dev server.
  assetsInclude: ["**/*.gz"],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/node_modules/echarts/")) return "charts";
          if (id.includes("/node_modules/zrender/")) return "renderer";
          if (id.includes("/node_modules/vue/") || id.includes("/node_modules/@vue/")) return "vue";
        },
      },
    },
  },
});
