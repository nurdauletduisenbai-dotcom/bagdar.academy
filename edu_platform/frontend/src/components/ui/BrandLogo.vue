<script setup lang="ts">
import { computed } from 'vue'

// Вариант без ночной подложки #0B1A18 — встаёт на любые тёмные фоны сайта (brand-deep, фоны «дуги», «компас»)
import logoDark from '@/assets/brand/logo-horizontal-on-dark.svg'
import logoLight from '@/assets/brand/logo-horizontal.svg'
import markPrimary from '@/assets/brand/mark-primary.svg'
import markWhite from '@/assets/brand/mark-white.svg'

/**
 * Логотип из дизайн-системы bagdar.academy (SVG в кривых, шрифт не нужен).
 * Всегда латиницей «bagdar.academy» — от языка интерфейса не зависит (logo-kz.svg лежит в assets/brand про запас).
 * В SVG уже заложено охранное поле, поэтому height — это высота вместе с полем; знак не меньше 24 px.
 */
const props = withDefaults(defineProps<{ dark?: boolean; mark?: boolean; height?: number }>(), { height: 44 })

const src = computed(() => {
  if (props.mark) return props.dark ? markWhite : markPrimary
  return props.dark ? logoDark : logoLight
})
</script>

<template>
  <img :src="src" alt="bagdar.academy" :height="height" class="brand-logo" :style="{ height: `${height}px` }" />
</template>

<style scoped>
.brand-logo {
  display: block;
  width: auto;
  max-width: 100%;
}
</style>
