<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { prefersReducedMotion } from '@/composables/useMotion'

/** Число, которое «набегает» от 0, когда попадает на экран */
const props = withDefaults(defineProps<{ value: number; duration?: number }>(), { duration: 1400 })
const el = ref<HTMLElement | null>(null)
const shown = ref(0)
let observer: IntersectionObserver | null = null
let started = false

function run() {
  if (prefersReducedMotion()) {
    shown.value = props.value
    return
  }
  const start = performance.now()
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / props.duration)
    shown.value = Math.round(props.value * (1 - Math.pow(1 - t, 3)))
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

onMounted(() => {
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && !started) {
      started = true
      run()
      observer?.disconnect()
    }
  }, { threshold: 0.4 })
  if (el.value) observer.observe(el.value)
})
onUnmounted(() => observer?.disconnect())
watch(() => props.value, () => started && (shown.value = props.value))
</script>

<template>
  <span ref="el" class="count-up">{{ shown.toLocaleString('ru-RU') }}</span>
</template>

<style scoped>
.count-up {
  font-variant-numeric: tabular-nums;
}
</style>
