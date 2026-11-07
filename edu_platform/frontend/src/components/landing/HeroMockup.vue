<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import AppIcon from '@/components/ui/AppIcon.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import { prefersReducedMotion, vParallax } from '@/composables/useMotion'

/**
 * Иллюстрация интерфейса (экран теста) для героя главной — декоративная, без реальных данных.
 * Оживает: таймер идёт, через секунду «выбирается» ответ A, прогресс растёт, карточки всплывают.
 */
const options = ['1/2', '√3/2', '1', '0']
const seconds = ref(24 * 60 + 15)
const picked = ref(prefersReducedMotion())
const ring = ref(prefersReducedMotion() ? 68 : 0)
let timer: number | undefined
let pickTimer: number | undefined

const clock = computed(() => `${Math.floor(seconds.value / 60)}:${String(seconds.value % 60).padStart(2, '0')}`)

onMounted(() => {
  if (prefersReducedMotion()) return
  timer = window.setInterval(() => (seconds.value = seconds.value > 0 ? seconds.value - 1 : 24 * 60 + 15), 1000)
  pickTimer = window.setTimeout(() => {
    picked.value = true
    ring.value = 68
  }, 1300)
})
onUnmounted(() => {
  window.clearInterval(timer)
  window.clearTimeout(pickTimer)
})
</script>

<template>
  <div class="mock" aria-hidden="true">
    <div v-parallax="0.08" class="mock__layer">
      <div class="mock__card">
        <div class="mock__head">
          <span class="mock__subject">{{ $t('landing.mockSubject') }}</span>
          <span class="mock__timer"><AppIcon name="clock" :size="14" /> {{ clock }}</span>
        </div>
        <div class="mock__bar"><span :class="{ grown: picked }" /></div>
        <span class="mock__progress">{{ $t('landing.mockProgress') }}</span>
        <p class="mock__question">{{ $t('landing.mockQuestion') }}</p>
        <ul class="mock__options">
          <li v-for="(o, i) in options" :key="o" :class="{ picked: picked && i === 0 }" :style="{ '--i': i }">
            <span class="mock__letter">{{ 'ABCD'[i] }}</span> {{ o }}
            <AppIcon v-if="picked && i === 0" name="check" :size="16" class="mock__ok" />
          </li>
        </ul>
      </div>
    </div>

    <div v-parallax="0.22" class="mock__chip-wrap mock__chip-wrap--analysis">
      <div class="mock__chip mock__chip--analysis">
        <span class="mock__dot"><AppIcon name="check" :size="12" /></span> {{ $t('landing.mockAnalysis') }}
      </div>
    </div>
    <div v-parallax="-0.12" class="mock__chip-wrap mock__chip-wrap--topic">
      <div class="mock__chip mock__chip--topic">
        <ProgressRing :value="ring" :size="44" />
        <span>
          <strong>{{ $t('landing.mockTopic') }}</strong>
          <small>{{ $t('landing.mockMastery') }}</small>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mock {
  position: relative;
  padding: var(--space-xl) var(--space-xl) var(--space-xxxl);
}
.mock__card {
  background: var(--canvas);
  color: var(--text-strong);
  border-radius: var(--radius-xl);
  padding: var(--space-xl);
  display: grid;
  gap: var(--space-sm);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
  transform: rotate(-1.5deg);
  animation: card-in 1s var(--ease-out-expo) both, card-float 7s ease-in-out 1s infinite;
}
.mock__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-sm);
}
.mock__subject {
  font: 600 var(--fs-caption) / 1.2 var(--font-sans);
  color: var(--text-secondary);
}
.mock__timer {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: var(--surface-soft);
  font: 600 var(--fs-caption) / 1 var(--font-sans);
  font-variant-numeric: tabular-nums;
}
.mock__bar {
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--surface-soft);
  overflow: hidden;
}
.mock__bar span {
  display: block;
  height: 100%;
  width: 22%;
  background: var(--green-500);
  transition: width 1.2s var(--ease-out-expo);
}
.mock__bar span.grown {
  width: 30%;
}
.mock__progress {
  font-size: var(--fs-micro);
  color: var(--text-tertiary);
}
.mock__question {
  margin: var(--space-xs) 0;
  font: 500 var(--fs-h5) / 1.35 var(--font-sans);
}
.mock__options {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-xs);
}
.mock__options li {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--fs-body-sm);
  transition: background 0.4s, border-color 0.4s, transform 0.4s var(--ease-out-expo);
  animation: option-in 0.6s var(--ease-out-expo) backwards;
  animation-delay: calc(0.35s + var(--i) * 0.08s);
}
.mock__options li.picked {
  border-color: var(--green-dark);
  background: var(--surface-feature);
  transform: scale(1.02);
}
.mock__letter {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--surface-soft);
  font: 600 var(--fs-micro) / 1 var(--font-sans);
  transition: background 0.4s, color 0.4s;
}
.picked .mock__letter {
  background: var(--green-500);
  color: var(--teal-900);
}
.mock__ok {
  margin-left: auto;
  color: var(--green-dark);
  animation: pop 0.45s var(--ease-out-expo) both;
}

/* Внешняя обёртка — параллакс (--py), внутренняя карточка — своё «покачивание» */
.mock__chip-wrap {
  position: absolute;
  z-index: 1;
}
.mock__chip-wrap--analysis {
  top: 42%;
  right: -12px;
}
.mock__chip-wrap--topic {
  bottom: 0;
  left: 0;
}
.mock__chip {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  background: var(--canvas);
  color: var(--text-strong);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
  font: 600 var(--fs-caption) / 1.2 var(--font-sans);
}
.mock__chip--analysis {
  animation: chip-in 0.7s var(--ease-out-expo) 1.4s backwards, chip-float 5s ease-in-out 2.1s infinite;
}
.mock__chip--topic {
  animation: chip-in 0.7s var(--ease-out-expo) 1.7s backwards, chip-float 6s ease-in-out 2.4s infinite reverse;
}
.mock__chip--topic span {
  display: grid;
}
.mock__chip small {
  font-weight: 400;
  color: var(--text-secondary);
}
.mock__dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--green-500);
  color: var(--teal-900);
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(40px) rotate(-6deg) scale(0.96);
  }
  to {
    opacity: 1;
    transform: rotate(-1.5deg);
  }
}
@keyframes card-float {
  0%,
  100% {
    transform: rotate(-1.5deg) translateY(0);
  }
  50% {
    transform: rotate(-0.5deg) translateY(-10px);
  }
}
@keyframes option-in {
  from {
    opacity: 0;
    transform: translateX(-12px);
  }
}
@keyframes pop {
  from {
    opacity: 0;
    transform: scale(0.3);
  }
}
@keyframes chip-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.85);
  }
}
@keyframes chip-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}
</style>
