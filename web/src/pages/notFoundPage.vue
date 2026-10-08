<template>
  <section class="content inner-content not-found-page">
    <div class="page-intro">
      <div>
        <div class="eyebrow"><span></span> PÁGINA NÃO ENCONTRADA</div>
        <h1 tabindex="-1">Este endereço não existe.</h1>
        <p>O painel não encontrou uma seção neste caminho. Use a Visão Geral para continuar explorando os dados.</p>
        <RouterLink class="not-found-link" :to="{ name: 'overview' }">Ir para a Visão Geral</RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
