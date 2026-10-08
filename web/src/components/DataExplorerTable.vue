<script setup>
import { ArrowLeft, ArrowRight } from "@lucide/vue";

defineProps({
  dataset: { type: Object, required: true },
  datasetInfo: { type: Object, required: true },
  search: { type: String, default: "" },
  filteredRows: { type: Array, required: true },
  pageNumber: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  columns: { type: Array, required: true },
  visibleRows: { type: Array, required: true },
  pageSize: { type: Number, required: true },
  columnLabel: { type: Function, required: true },
});
const emit = defineEmits(["update:page-number"]);
</script>

<template>
  <article class="table-panel panel">
    <div class="table-header">
      <div><strong>{{ dataset.label }}</strong><span>{{ filteredRows.length.toLocaleString('pt-BR') }} registros<template v-if="search"> · filtrados</template></span></div>
      <small>Página {{ pageNumber }} / {{ totalPages }}</small>
    </div>
    <div class="table-scroll">
      <table :aria-label="dataset.label">
        <caption class="sr-only">{{ dataset.label }}. {{ datasetInfo.description }}</caption>
        <thead><tr><th v-for="key in columns" :key="key" scope="col">{{ columnLabel(key) }}</th></tr></thead>
        <tbody>
          <tr v-for="(row, index) in visibleRows" :key="index">
            <td v-for="key in columns" :key="key" :class="{ numeric: typeof row[key] === 'number' }">
              {{ typeof row[key] === 'number' ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(row[key]) : row[key] ?? '—' }}
            </td>
          </tr>
          <tr v-if="visibleRows.length === 0"><td :colspan="columns.length" class="empty-row">Nenhum registro encontrado.</td></tr>
        </tbody>
      </table>
    </div>
    <div class="table-footer">
      <span>{{ filteredRows.length ? (pageNumber - 1) * pageSize + 1 : 0 }}–{{ Math.min(pageNumber * pageSize, filteredRows.length) }} de {{ filteredRows.length.toLocaleString('pt-BR') }}</span>
      <div>
        <button type="button" :disabled="pageNumber <= 1" @click="emit('update:page-number', pageNumber - 1)"><ArrowLeft class="ui-icon" :size="13" /> Anterior</button>
        <button type="button" :disabled="pageNumber >= totalPages" @click="emit('update:page-number', pageNumber + 1)">Próxima <ArrowRight class="ui-icon" :size="13" /></button>
      </div>
    </div>
  </article>
</template>
