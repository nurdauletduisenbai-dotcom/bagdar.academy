import { onMounted, onUnmounted, ref, type Directive } from 'vue'

/**
 * Анимации публичных страниц: появление при прокрутке, параллакс, прогресс прокрутки.
 * Один общий IntersectionObserver и один обработчик scroll (через requestAnimationFrame).
 * Если в системе включено «уменьшить движение» — всё показывается сразу, без движения.
 */
export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

// ---------- Появление: v-reveal, v-reveal:left / :right / :scale, v-reveal="{ delay: 120 }" ----------
let revealObserver: IntersectionObserver | null = null

function getRevealObserver() {
  if (!revealObserver) {
    revealObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add('is-visible')
          revealObserver!.unobserve(entry.target)
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
    )
  }
  return revealObserver
}

export const vReveal: Directive<HTMLElement, { delay?: number } | number | undefined> = {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (binding.arg) el.classList.add(`reveal--${binding.arg}`)
    const delay = typeof binding.value === 'number' ? binding.value : binding.value?.delay
    if (delay) el.style.setProperty('--reveal-delay', `${delay}ms`)
    if (prefersReducedMotion() || !('IntersectionObserver' in window)) {
      el.classList.add('is-visible')
      return
    }
    getRevealObserver().observe(el)
  },
  unmounted(el) {
    revealObserver?.unobserve(el)
  },
}

// ---------- Параллакс: v-parallax="0.2" — сдвиг относительно центра экрана (через --py) ----------
const parallaxItems = new Map<HTMLElement, number>()
let frame = 0
const scrollListeners = new Set<() => void>()

function tick() {
  frame = 0
  const mid = window.innerHeight / 2
  for (const [el, speed] of parallaxItems) {
    const rect = el.getBoundingClientRect()
    if (rect.bottom < -200 || rect.top > window.innerHeight + 200) continue
    const offset = (rect.top + rect.height / 2 - mid) * -speed
    el.style.setProperty('--py', `${offset.toFixed(1)}px`)
  }
  for (const fn of scrollListeners) fn()
}

function onScroll() {
  if (!frame) frame = requestAnimationFrame(tick)
}

function attachScroll() {
  if (parallaxItems.size + scrollListeners.size === 1) {
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })
  }
  onScroll()
}

function detachScroll() {
  if (parallaxItems.size + scrollListeners.size === 0) {
    window.removeEventListener('scroll', onScroll)
    window.removeEventListener('resize', onScroll)
  }
}

export const vParallax: Directive<HTMLElement, number> = {
  mounted(el, binding) {
    if (prefersReducedMotion()) return
    el.classList.add('parallax')
    parallaxItems.set(el, binding.value ?? 0.15)
    attachScroll()
  },
  unmounted(el) {
    if (parallaxItems.delete(el)) detachScroll()
  },
}

/** Доля прокрутки страницы 0…1 — для полоски прогресса */
export function useScrollProgress() {
  const progress = ref(0)
  const update = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight
    progress.value = max > 0 ? Math.min(1, window.scrollY / max) : 0
  }
  onMounted(() => {
    scrollListeners.add(update)
    attachScroll()
  })
  onUnmounted(() => {
    scrollListeners.delete(update)
    detachScroll()
  })
  return progress
}

/** Насколько элемент «прокручен» через экран 0…1 (0 — только показался снизу, 1 — центр выше середины) */
export function useSectionProgress(target: { value: HTMLElement | null }) {
  const progress = ref(prefersReducedMotion() ? 1 : 0)
  const update = () => {
    if (!target.value || prefersReducedMotion()) return
    const rect = target.value.getBoundingClientRect()
    const vh = window.innerHeight
    progress.value = Math.min(1, Math.max(0, (vh - rect.top) / (vh * 0.6 + rect.height / 2)))
  }
  onMounted(() => {
    scrollListeners.add(update)
    attachScroll()
  })
  onUnmounted(() => {
    scrollListeners.delete(update)
    detachScroll()
  })
  return progress
}
