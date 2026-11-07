<script setup lang="ts">
import { computed } from 'vue'

import { useLocaleStore } from '@/stores/locale'

import { PRIVACY, PRIVACY_UPDATED_AT } from './privacyContent'

/** /privacy — политика конфиденциальности (текст в privacyContent.ts, заглушки [ВОТ ТАК] подсвечиваются) */
const locale = useLocaleStore()
const doc = computed(() => PRIVACY[locale.current] ?? PRIVACY.ru)

const PLACEHOLDER = /(\[[^\]]+\])/
const hasPlaceholders = computed(() => PLACEHOLDER.test(JSON.stringify(doc.value) + PRIVACY_UPDATED_AT))

/** Текст → куски; нечётные — заглушки в скобках (рендерятся как <mark>, без v-html) */
function parts(text: string) {
  return text.split(PLACEHOLDER).map((value, i) => ({ value, placeholder: i % 2 === 1 }))
}
</script>

<template>
  <div class="container privacy-page">
    <header class="privacy__head">
      <h1>{{ doc.title }}</h1>
      <p class="privacy__lead">{{ doc.lead }}</p>
      <p class="muted small">
        {{ doc.updatedLabel }}
        <template v-for="(p, i) in parts(PRIVACY_UPDATED_AT)" :key="i"><mark v-if="p.placeholder" class="ph">{{ p.value }}</mark><template v-else>{{ p.value }}</template></template>
      </p>
      <p v-if="hasPlaceholders" class="alert alert--warning">{{ doc.draftNote }}</p>
    </header>

    <section v-for="section in doc.sections" :key="section.title" class="privacy__section">
      <h2>{{ section.title }}</h2>
      <p v-for="(text, i) in section.paragraphs" :key="`p${i}`">
        <template v-for="(p, j) in parts(text)" :key="j"><mark v-if="p.placeholder" class="ph">{{ p.value }}</mark><template v-else>{{ p.value }}</template></template>
      </p>
      <ul v-if="section.items">
        <li v-for="(text, i) in section.items" :key="`i${i}`">
          <template v-for="(p, j) in parts(text)" :key="j"><mark v-if="p.placeholder" class="ph">{{ p.value }}</mark><template v-else>{{ p.value }}</template></template>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.privacy-page {
  max-width: 800px;
  display: grid;
  gap: var(--space-xl);
  padding-top: var(--space-xxl);
}
.privacy__head {
  display: grid;
  gap: var(--space-sm);
}
.privacy__head h1 {
  margin: 0;
  font-size: var(--fs-h2);
  line-height: 1.15;
  overflow-wrap: break-word;
  hyphens: auto;
}
.privacy__head p {
  margin: 0;
}
.privacy__lead {
  font-size: var(--fs-subtitle);
  line-height: 1.55;
  color: var(--text-secondary);
}
.privacy__section h2 {
  margin: 0 0 var(--space-sm);
  font-size: var(--fs-h4);
}
.privacy__section p,
.privacy__section li {
  line-height: 1.65;
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}
.privacy__section p {
  margin: 0 0 var(--space-sm);
}
.privacy__section ul {
  margin: 0;
  padding-left: 1.25em;
  display: grid;
  gap: var(--space-xs);
}
.ph {
  background: var(--warning-bg);
  color: var(--text-strong);
  border-radius: 4px;
  padding: 0 3px;
}
@media (max-width: 640px) {
  .privacy__head h1 {
    font-size: var(--fs-h3);
  }
  .privacy__section h2 {
    font-size: var(--fs-h5);
  }
}
</style>
