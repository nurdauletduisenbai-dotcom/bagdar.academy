<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { coursesApi } from '@/api/courses'
import { newsApi } from '@/api/news'
import CourseCard from '@/components/course/CourseCard.vue'
import ContactForm from '@/components/landing/ContactForm.vue'
import FaqList from '@/components/landing/FaqList.vue'
import HeroMockup from '@/components/landing/HeroMockup.vue'
import UntCountdown from '@/components/landing/UntCountdown.vue'
import PostCard from '@/components/news/PostCard.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CountUp from '@/components/ui/CountUp.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAsync } from '@/composables/useAsync'
import { useScrollProgress, useSectionProgress, vParallax, vReveal } from '@/composables/useMotion'
import type { PlatformStats } from '@/types/api'

/**
 * Публичная главная. Структура — по разбору лендингов:
 *  JUZ40 — результат и таймер до ҰБТ, «всё на одной платформе», заявка менеджеру;
 *  Khan Academy — выбор роли в герое, цифры, «как это работает», вкладки по аудиториям, FAQ;
 *  Padlet — один главный CTA, «бесплатно и за минуту», показываем сам продукт.
 */
const news = useAsync(() => newsApi.list({ page_size: 4 }))
const stats = useAsync(() => newsApi.stats())
const courses = useAsync(() => coursesApi.list({ page: 1 }))

const featured = computed(() => news.data.value?.results[0] ?? null)
const latest = computed(() => news.data.value?.results.slice(1, 4) ?? [])
const topCourses = computed(() => courses.data.value?.results.slice(0, 3) ?? [])

const statKeys: (keyof PlatformStats)[] = ['courses', 'students', 'teachers', 'schools']

const roles = [
  { key: 'Student', icon: 'play', to: '/register?role=student' },
  { key: 'Parent', icon: 'user', to: '/register?role=parent' },
  { key: 'School', icon: 'edit', to: '/schools/apply' },
] as const

const features = [
  { key: 'Tests', icon: 'check' },
  { key: 'Video', icon: 'play' },
  { key: 'Homework', icon: 'upload' },
  { key: 'Progress', icon: 'circle' },
  { key: 'Support', icon: 'user' },
  { key: 'Schedule', icon: 'bell' },
] as const

const audiences = [
  { key: 'Student', to: '/register?role=student' },
  { key: 'Parent', to: '/register?role=parent' },
  { key: 'Teacher', to: { path: '/', hash: '#contact' } },
  { key: 'School', to: '/schools/apply' },
] as const
const tab = ref<(typeof audiences)[number]['key']>('Student')
const activeAudience = computed(() => audiences.find((a) => a.key === tab.value)!)

// ---------- Движение ----------
const { t } = useI18n()
const pageProgress = useScrollProgress()
const howEl = ref<HTMLElement | null>(null)
const howProgress = useSectionProgress(howEl)
// Бегущая строка предметов (дважды подряд — для бесшовного цикла)
const subjects = computed(() => t('landing.ticker').split(', '))
// Плавающие символы в герое: позиция, размер и скорость параллакса у каждого свои
const glyphs = [
  { s: '∑', x: 6, y: 18, size: 64, speed: 0.35 },
  { s: 'π', x: 44, y: 8, size: 44, speed: 0.2 },
  { s: '√x', x: 88, y: 12, size: 40, speed: 0.45 },
  { s: '∫', x: 52, y: 78, size: 72, speed: 0.28 },
  { s: 'x²', x: 92, y: 70, size: 36, speed: 0.5 },
  { s: 'Δ', x: 3, y: 82, size: 40, speed: 0.18 },
  { s: '∞', x: 70, y: 92, size: 34, speed: 0.4 },
]
</script>

<template>
  <div class="motion-scope">
  <div class="scroll-progress" :style="{ transform: `scaleX(${pageProgress})` }" aria-hidden="true" />

  <!-- 1. Герой: слоган, выбор роли (Khan), «бесплатно за минуту» (Padlet), интерфейс продукта -->
  <section class="hero">
    <div class="hero__deco" aria-hidden="true">
      <span class="orb orb--green" />
      <span class="orb orb--teal" />
      <span v-for="g in glyphs" :key="g.s" v-parallax="g.speed" class="glyph-wrap"
            :style="{ left: `${g.x}%`, top: `${g.y}%` }">
        <span class="glyph" :style="{ fontSize: `${g.size}px`, animationDelay: `${g.speed * -10}s` }">{{ g.s }}</span>
      </span>
    </div>
    <div class="container hero__inner">
      <div class="hero__copy">
        <div class="eyebrow hero-in" style="--d: 0">{{ $t('landing.heroEyebrow') }}</div>
        <h1 class="hero__title hero-in" style="--d: 1">{{ $t('landing.heroTitle') }}</h1>
        <p class="hero__text hero-in" style="--d: 2">{{ $t('landing.heroText') }}</p>

        <div class="hero__roles hero-in" style="--d: 3">
          <span class="hero__roles-title">{{ $t('landing.roleTitle') }}</span>
          <div class="roles">
            <RouterLink v-for="r in roles" :key="r.key" :to="r.to" class="role">
              <span class="role__icon"><AppIcon :name="r.icon" :size="18" /></span>
              <span class="role__text">
                <strong>{{ $t(`landing.role${r.key}`) }}</strong>
                <small>{{ $t(`landing.role${r.key}Hint`) }}</small>
              </span>
              <AppIcon name="arrow-right" :size="16" class="role__arrow" />
            </RouterLink>
          </div>
          <p class="hero__note">
            {{ $t('landing.freeNote') }} {{ $t('landing.haveAccount') }}
            <RouterLink to="/login">{{ $t('public.login') }}</RouterLink>
          </p>
        </div>
      </div>
      <HeroMockup class="hero__mock" />
    </div>
  </section>

  <!-- Бегущая строка предметов -->
  <div class="ticker" aria-hidden="true">
    <div class="ticker__track">
      <span v-for="(subj, i) in [...subjects, ...subjects]" :key="i" class="ticker__item">{{ subj }}<i>✦</i></span>
    </div>
  </div>

  <div class="container landing">
    <!-- 2. Цифры платформы (реальные, из API) + таймер до ҰБТ (JUZ40) -->
    <section v-reveal class="proof">
      <dl v-if="stats.data.value" class="proof__stats">
        <div v-for="k in statKeys" :key="k" class="proof__stat">
          <dt class="stat"><CountUp :value="stats.data.value[k]" /></dt>
          <dd class="muted small">{{ $t(`landing.stats.${k}`) }}</dd>
        </div>
      </dl>
      <UntCountdown />
    </section>

    <!-- 3. Всё на одной платформе (JUZ40) -->
    <section id="about" class="section">
      <header v-reveal class="section__head">
        <div class="eyebrow">{{ $t('landing.featuresEyebrow') }}</div>
        <h2>{{ $t('landing.featuresTitle') }}</h2>
      </header>
      <div class="features">
        <article v-for="(f, i) in features" :key="f.key" v-reveal="(i % 3) * 110" class="feature">
          <span class="feature__icon"><AppIcon :name="f.icon" :size="20" /></span>
          <h3>{{ $t(`landing.feat${f.key}Title`) }}</h3>
          <p class="muted">{{ $t(`landing.feat${f.key}Text`) }}</p>
        </article>
      </div>
    </section>

    <!-- 4. Как проходит обучение (Khan) -->
    <section ref="howEl" v-reveal:scale class="band how">
      <span class="how__glow" aria-hidden="true" />
      <header class="section__head">
        <div class="eyebrow">{{ $t('landing.howEyebrow') }}</div>
        <h2>{{ $t('landing.howTitle') }}</h2>
      </header>
      <ol class="how__steps" :style="{ '--line': howProgress }">
        <li v-for="n in 3" :key="n" v-reveal="n * 160" class="how__step" :class="{ lit: howProgress > (n - 1) / 3 + 0.05 }">
          <span class="how__num">{{ n }}</span>
          <div>
            <h3>{{ $t(`landing.how${n}Title`) }}</h3>
            <p class="muted">{{ $t(`landing.how${n}Text`) }}</p>
          </div>
        </li>
      </ol>
    </section>

    <!-- 5. Для кого: вкладки по аудиториям (Khan) -->
    <section class="section">
      <header v-reveal class="section__head">
        <div class="eyebrow">{{ $t('landing.audEyebrow') }}</div>
        <h2>{{ $t('landing.audTitle') }}</h2>
      </header>
      <div v-reveal class="tabs" role="tablist">
        <button v-for="a in audiences" :key="a.key" type="button" role="tab" :aria-selected="tab === a.key"
                :class="{ active: tab === a.key }" @click="tab = a.key">
          {{ $t(`landing.aud${a.key}Tab`) }}
        </button>
      </div>
      <div v-reveal class="card audience" role="tabpanel">
        <Transition name="swap" mode="out-in">
          <div :key="tab" class="audience__inner">
            <div class="audience__copy">
              <h3>{{ $t(`landing.aud${tab}Title`) }}</h3>
              <p class="muted">{{ $t(`landing.aud${tab}Text`) }}</p>
              <RouterLink :to="activeAudience.to" class="btn">{{ $t(`landing.aud${tab}Cta`) }}</RouterLink>
            </div>
            <ul class="audience__list">
              <li v-for="b in 4" :key="b" :style="{ '--i': b }"><AppIcon name="check" :size="16" /> {{ $t(`landing.aud${tab}B${b}`) }}</li>
            </ul>
          </div>
        </Transition>
      </div>
    </section>

    <!-- 6. Курсы из публичного каталога (аналог тарифов JUZ40: цена видна сразу) -->
    <section v-if="topCourses.length" id="courses" class="section">
      <header v-reveal class="section__head section__head--row">
        <div>
          <div class="eyebrow">{{ $t('landing.coursesEyebrow') }}</div>
          <h2>{{ $t('landing.coursesTitle') }}</h2>
        </div>
        <span class="muted small">{{ $t('landing.coursesNote') }}</span>
      </header>
      <div class="courses-grid">
        <CourseCard v-for="(c, i) in topCourses" :key="c.id" v-reveal="i * 120" :course="c" class="lift" />
      </div>
    </section>

    <!-- 7. Новости -->
    <section id="news" class="section">
      <header v-reveal class="section__head section__head--row">
        <div>
          <div class="eyebrow">{{ $t('landing.newsEyebrow') }}</div>
          <h2>{{ $t('landing.newsTitle') }}</h2>
        </div>
        <RouterLink to="/news" class="btn btn--text">{{ $t('landing.allNews') }} <AppIcon name="arrow-right" :size="14" /></RouterLink>
      </header>
      <StateBlock :loading="news.loading.value" :error="news.error.value" :empty="!featured"
                  :empty-text="$t('landing.emptyNews')" @retry="news.run">
        <div class="stack">
          <PostCard v-if="featured" v-reveal :post="featured" featured class="lift" />
          <div v-if="latest.length" class="grid news-grid">
            <PostCard v-for="(p, i) in latest" :key="p.id" v-reveal="i * 120" :post="p" class="lift" />
          </div>
        </div>
      </StateBlock>
    </section>

    <!-- 8. FAQ (Khan) + заявка менеджеру (JUZ40) -->
    <section class="split-2">
      <div id="faq" v-reveal:left class="section">
        <header class="section__head">
          <div class="eyebrow">{{ $t('landing.faqEyebrow') }}</div>
          <h2>{{ $t('landing.faqTitle') }}</h2>
        </header>
        <FaqList />
      </div>
      <div id="contact" v-reveal:right class="card card--subtle section contact">
        <header class="section__head">
          <div class="eyebrow">{{ $t('landing.contactEyebrow') }}</div>
          <h2>{{ $t('landing.contactTitle') }}</h2>
          <p class="muted">{{ $t('landing.contactText') }}</p>
        </header>
        <ContactForm />
      </div>
    </section>

    <!-- 9. Финальный призыв -->
    <section v-reveal:scale class="band cta">
      <div>
        <h2>{{ $t('landing.ctaTitle') }}</h2>
        <p class="muted">{{ $t('landing.ctaText') }}</p>
      </div>
      <div class="row cta__actions">
        <RouterLink to="/register" class="btn btn--lg">{{ $t('public.register') }}</RouterLink>
        <RouterLink to="/invite" class="btn btn--ghost btn--lg">{{ $t('auth.haveInvite') }}</RouterLink>
      </div>
    </section>
  </div>
  </div>
</template>

<style scoped>
/* ---------- Герой ---------- */
.hero {
  position: relative;
  background: radial-gradient(120% 120% at 0% 0%, var(--teal-700) 0%, var(--teal-900) 65%);
  color: var(--text-on-dark);
  padding: var(--space-section) 0;
  overflow: hidden;
  isolation: isolate;
}
.hero__inner {
  position: relative;
  z-index: 1;
}

/* Полоска прогресса прокрутки под шапкой */
.scroll-progress {
  position: fixed;
  top: var(--nav-height);
  left: 0;
  right: 0;
  height: 3px;
  z-index: 29;
  background: var(--green-500);
  transform-origin: 0 50%;
  pointer-events: none;
}

/* Декор героя: светящиеся пятна и формулы, которые плывут с разной скоростью при прокрутке */
.hero__deco {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.45;
}
.orb--green {
  width: 420px;
  height: 420px;
  right: -80px;
  top: -120px;
  background: var(--green-500);
  opacity: 0.18;
  animation: drift 16s ease-in-out infinite;
}
.orb--teal {
  width: 520px;
  height: 520px;
  left: -160px;
  bottom: -260px;
  background: #00a38a;
  opacity: 0.25;
  animation: drift 20s ease-in-out infinite reverse;
}
.glyph-wrap {
  position: absolute;
}
.glyph {
  display: block;
  font: 500 40px / 1 var(--font-sans);
  color: var(--text-on-dark);
  opacity: 0.07;
  animation: bob 9s ease-in-out infinite;
  user-select: none;
}

/* Появление текста героя при загрузке, по очереди */
.hero-in {
  animation: hero-in 0.9s var(--ease-out-expo) both;
  animation-delay: calc(var(--d) * 0.12s + 0.1s);
}

/* Бегущая строка предметов */
.ticker {
  overflow: hidden;
  background: var(--green-500);
  color: var(--teal-900);
  border-block: 1px solid rgba(0, 30, 43, 0.12);
  mask-image: linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent);
}
.ticker__track {
  display: flex;
  width: max-content;
  animation: ticker 48s linear infinite;
}
.ticker:hover .ticker__track {
  animation-play-state: paused;
}
.ticker__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-lg);
  padding: 14px var(--space-lg) 14px 0;
  font: 600 var(--fs-body-md) / 1 var(--font-sans);
  white-space: nowrap;
}
.ticker__item i {
  font-style: normal;
  opacity: 0.45;
}

/* Карточки приподнимаются при наведении */
.lift {
  transition: transform 0.35s var(--ease-out-expo), box-shadow 0.35s var(--ease-out-expo), opacity var(--dur-reveal) var(--ease-out-expo);
}
.lift.is-visible:hover,
.lift:not(.reveal):hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-4);
}
.hero__inner {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: var(--space-section-sm);
  align-items: center;
}
.hero__copy {
  display: grid;
  gap: var(--space-lg);
}
.hero .eyebrow {
  color: var(--green-500);
}
.hero__title {
  margin: 0;
  font: 500 var(--fs-display-lg) / 1.06 var(--font-sans);
  letter-spacing: -1px;
  color: var(--text-on-dark);
  max-width: 14ch;
}
.hero__text {
  margin: 0;
  max-width: 560px;
  font-size: var(--fs-subtitle);
  line-height: 1.55;
  color: var(--text-on-dark-muted);
}
.hero__roles {
  display: grid;
  gap: var(--space-sm);
  margin-top: var(--space-xs);
}
.hero__roles-title {
  font: 600 var(--fs-body-sm) / 1.2 var(--font-sans);
}
.roles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-sm);
}
.role {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border-dark);
  color: var(--text-on-dark);
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s;
}
.role:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--green-500);
  text-decoration: none;
  transform: translateY(-3px);
}
.role {
  transition: background 0.2s, border-color 0.2s, transform 0.3s var(--ease-out-expo);
}
.role:hover .role__arrow {
  transform: translateX(4px);
  color: var(--green-500);
}
.role__arrow {
  transition: transform 0.3s var(--ease-out-expo), color 0.2s;
}
.role:hover .role__icon {
  transform: rotate(-8deg) scale(1.08);
}
.role__icon {
  transition: transform 0.3s var(--ease-out-expo);
}
.role__icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--green-500);
  color: var(--teal-900);
}
.role__text {
  display: grid;
  min-width: 0;
}
.role__text strong {
  font: 600 var(--fs-body-sm) / 1.25 var(--font-sans);
}
.role__text small {
  font-size: var(--fs-micro);
  color: var(--text-on-dark-muted);
}
.role__arrow {
  margin-left: auto;
  flex-shrink: 0;
  color: var(--text-on-dark-muted);
}
.hero__note {
  margin: 0;
  font-size: var(--fs-body-sm);
  color: var(--text-on-dark-muted);
}
.hero__note a {
  color: var(--green-500);
}

/* ---------- Секции ---------- */
.landing {
  display: grid;
  gap: var(--space-section);
  padding-top: var(--space-xxl);
}
.section {
  display: grid;
  gap: var(--space-xl);
  align-content: start;
  scroll-margin-top: calc(var(--nav-height) + var(--space-md));
}
.section__head {
  display: grid;
  gap: var(--space-xs);
}
.section__head h2,
.section__head p {
  margin: 0;
}
.section__head--row {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: var(--space-md);
  flex-wrap: wrap;
}

/* Цифры + таймер */
.proof {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-md);
  align-items: stretch;
}
.proof__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}
.proof__stat {
  padding: var(--space-lg) var(--space-xl);
}
.proof__stat + .proof__stat {
  border-left: 1px solid var(--border-default);
}
.proof__stat dd {
  margin: 4px 0 0;
}

/* Возможности */
.features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-xxl) var(--space-xl);
}
.feature {
  display: grid;
  gap: var(--space-xs);
  align-content: start;
}
.feature h3,
.feature p {
  margin: 0;
}
.feature h3 {
  font-size: var(--fs-h5);
}
.feature {
  padding: var(--space-lg);
  margin: calc(-1 * var(--space-lg));
  border-radius: var(--radius-lg);
  transition: background 0.3s, transform 0.4s var(--ease-out-expo), opacity var(--dur-reveal) var(--ease-out-expo);
}
.feature.is-visible:hover {
  background: var(--surface-subtle);
  transform: translateY(-4px);
}
.feature:hover .feature__icon {
  background: var(--green-500);
  color: var(--teal-900);
  transform: rotate(-6deg) scale(1.06);
}
.feature__icon {
  transition: background 0.3s, color 0.3s, transform 0.4s var(--ease-out-expo);
  width: 44px;
  height: 44px;
  margin-bottom: var(--space-xs);
  border-radius: var(--radius-md);
  display: grid;
  place-items: center;
  background: var(--surface-feature);
  color: var(--green-dark);
}

/* Как проходит обучение */
.how {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: var(--space-xl);
  padding: var(--space-xxxl);
}
.how__glow {
  position: absolute;
  width: 360px;
  height: 360px;
  right: -120px;
  top: -140px;
  border-radius: 50%;
  background: var(--green-500);
  filter: blur(90px);
  opacity: 0.16;
  animation: drift 14s ease-in-out infinite;
  pointer-events: none;
}
.how__steps {
  position: relative;
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-xl);
}
/* Линия между шагами «прорисовывается» по мере прокрутки (--line: 0…1) */
.how__steps::before,
.how__steps::after {
  content: '';
  position: absolute;
  top: 19px;
  left: 20px;
  right: 20px;
  height: 2px;
  border-radius: 2px;
}
.how__steps::before {
  background: rgba(255, 255, 255, 0.12);
}
.how__steps::after {
  background: var(--green-500);
  transform: scaleX(var(--line, 0));
  transform-origin: 0 50%;
  transition: transform 0.15s linear;
}
.how__step > div {
  position: relative;
  z-index: 1;
}
.how__step {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  align-items: flex-start;
}
.how__step h3 {
  margin: 0 0 4px;
}
.how__step p {
  margin: 0;
}
.how__step .how__num {
  position: relative;
  z-index: 1;
  background: var(--teal-700);
  color: var(--text-on-dark);
  box-shadow: 0 0 0 6px var(--teal-900);
  transition: background 0.4s, color 0.4s, transform 0.5s var(--ease-out-expo);
}
.how__step.lit .how__num {
  background: var(--green-500);
  color: var(--teal-900);
  transform: scale(1.12);
}
.how__num {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--green-500);
  color: var(--teal-900);
  font: 600 var(--fs-body-md) / 1 var(--font-sans);
}

/* Аудитории */
.audience {
  padding: var(--space-xxl);
  margin-top: calc(-1 * var(--space-xl));
  overflow: hidden;
}
.audience__inner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--space-xxl);
  align-items: center;
}
.audience__list li {
  animation: item-in 0.5s var(--ease-out-expo) backwards;
  animation-delay: calc(var(--i) * 0.06s + 0.1s);
}
.swap-enter-active,
.swap-leave-active {
  transition: opacity 0.25s, transform 0.35s var(--ease-out-expo);
}
.swap-enter-from {
  opacity: 0;
  transform: translateX(24px);
}
.swap-leave-to {
  opacity: 0;
  transform: translateX(-24px);
}
.audience__copy {
  display: grid;
  gap: var(--space-md);
  justify-items: start;
}
.audience__copy h3,
.audience__copy p {
  margin: 0;
}
.audience__copy h3 {
  font-size: var(--fs-h3);
  line-height: 1.2;
}
.audience__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-sm);
}
.audience__list li {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  background: var(--surface-subtle);
  font-weight: 500;
}
.audience__list :deep(svg) {
  color: var(--green-dark);
  flex-shrink: 0;
}

.news-grid {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}
.courses-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-md);
}

/* FAQ + заявка */
.split-2 {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: var(--space-section-sm);
  align-items: start;
}
.contact {
  padding: var(--space-xxl);
}

/* Финальный CTA */
.cta {
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-xl);
  flex-wrap: wrap;
  padding: var(--space-xxxl);
}
.cta::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 30%, rgba(0, 237, 100, 0.12) 50%, transparent 70%);
  transform: translateX(-100%);
  animation: sweep 6s ease-in-out 1s infinite;
  pointer-events: none;
}
.cta > * {
  position: relative;
  z-index: 1;
}
.cta h2 {
  margin: 0 0 var(--space-xs);
}
.cta p {
  margin: 0;
  max-width: 520px;
}
.cta__actions {
  flex-wrap: wrap;
}

@keyframes drift {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(-40px, 30px) scale(1.12);
  }
}
@keyframes bob {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-14px) rotate(6deg);
  }
}
@keyframes hero-in {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
}
@keyframes ticker {
  to {
    transform: translateX(-50%);
  }
}
@keyframes item-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
}
@keyframes sweep {
  0% {
    transform: translateX(-100%);
  }
  60%,
  100% {
    transform: translateX(100%);
  }
}

@media (max-width: 1100px) {
  .hero__inner {
    grid-template-columns: 1fr;
  }
  .hero__mock {
    max-width: 520px;
  }
  .proof {
    grid-template-columns: 1fr;
  }
  .features {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .split-2 {
    grid-template-columns: 1fr;
  }
  .courses-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .roles {
    grid-template-columns: 1fr;
  }
  .proof__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .proof__stat:nth-child(3) {
    border-left: 0;
  }
  .proof__stat:nth-child(n + 3) {
    border-top: 1px solid var(--border-default);
  }
  .how__steps,
  .audience__inner {
    grid-template-columns: 1fr;
  }
  .how__steps::before,
  .how__steps::after {
    display: none;
  }
  .glyph {
    opacity: 0.05;
  }
}
@media (max-width: 640px) {
  .hero {
    padding: var(--space-section-sm) 0;
  }
  .hero__title {
    font-size: var(--fs-h2);
  }
  .hero__text {
    font-size: var(--fs-body-md);
  }
  .hero__mock {
    display: none;
  }
  .landing {
    gap: var(--space-section-sm);
  }
  .features,
  .courses-grid {
    grid-template-columns: 1fr;
  }
  .how,
  .audience,
  .contact,
  .cta {
    padding: var(--space-xl);
  }
}
</style>
