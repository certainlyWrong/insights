<script setup>
defineProps({
  tone: { type: String, default: "blue" },
  label: { type: String, default: "" },
});
</script>

<template>
  <article class="metric" :class="`metric-${tone}`">
    <div class="metric-label"><slot name="label">{{ label }}</slot></div>
    <strong><slot name="value" /></strong>
    <div class="metric-foot"><slot name="foot" /></div>
    <slot name="decoration" />
  </article>
</template>
