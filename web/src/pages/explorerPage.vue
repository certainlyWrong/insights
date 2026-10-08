<script setup>
import { inject, toRefs } from "vue";
import { Search, Download, ExternalLink } from "@lucide/vue";
import DataExplorerTable from "../components/DataExplorerTable.vue";
const { activeData, search, pageNumber, pageSize, detailLoading, detailLoaded, datasets, dataset, datasetInfo, columns, filteredRows, totalPages, visibleRows, exportTable, columnLabel } = toRefs(inject("dashboard"));
</script>

<template>
<section class="content inner-content">
          <div class="page-intro"><div><div class="eyebrow"><span></span> EXPLORADOR DE DADOS</div><h1 tabindex="-1">Os dados, <em>em detalhe.</em></h1><p>Pesquise, percorra e baixe as tabelas que alimentam este painel.</p></div></div>
          <div class="explorer-controls panel">
            <label><span>CONJUNTO DE DADOS</span><select v-model="activeData"><option v-for="(item, id) in datasets" :key="id" :value="id">{{ item.label }}</option></select></label>
            <label class="search-box"><span>BUSCAR</span><div><Search class="ui-icon" :size="14" /><input v-model="search" type="search" placeholder="Data, indicador, função ou valor" /></div></label>
            <button class="download-button" :disabled="activeData === 'titles' && !detailLoaded" @click="exportTable"><Download class="ui-icon" :size="15" /> Baixar dados</button>
          </div>
          <div class="dataset-context panel">
            <p>{{ datasetInfo.description }}</p>
            <a v-if="datasetInfo.source" :href="datasetInfo.source.url" target="_blank" rel="noreferrer">Fonte: {{ datasetInfo.source.name }} <ExternalLink class="ui-icon" :size="12" /></a>
            <span v-else>Fonte documentada na seção Fontes e método.</span>
          </div>
          <div v-if="activeData === 'titles' && detailLoading" class="loading-row panel"><span class="spinner"></span> Preparando as posições individuais por título…</div>
          <DataExplorerTable
            :dataset="dataset"
            :dataset-info="datasetInfo"
            :search="search"
            :filtered-rows="filteredRows"
            :page-number="pageNumber"
            :total-pages="totalPages"
            :columns="columns"
            :visible-rows="visibleRows"
            :page-size="pageSize"
            :column-label="columnLabel"
            @update:page-number="pageNumber = $event"
          />
          <p class="table-explainer">As tabelas preservam as unidades dos arquivos tratados. Séries financeiras usam R$ bilhões; posições individuais incluem valores em reais. O seletor “Posições individuais” carrega cerca de 165 mil linhas ao ser aberto.</p>
        </section>
</template>
