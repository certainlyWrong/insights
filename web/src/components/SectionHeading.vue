<script setup>
defineProps({
  kicker: { type: String, required: true },
  title: { type: String, required: true },
  note: { type: String, default: "" },
  spacer: { type: Boolean, default: false },
  indexTitle: { type: Boolean, default: false },
});
</script>

<template>
  <div class="section-title" :class="{ 'section-spacer': spacer, 'overview-index-title': indexTitle }">
    <div><span>{{ kicker }}</span><h2>{{ title }}</h2></div>
    <small v-if="note">{{ note }}</small>
    <slot />
  </div>
</template>
