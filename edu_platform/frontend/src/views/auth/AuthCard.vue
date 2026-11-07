<script setup lang="ts">
import BrandLogo from '@/components/ui/BrandLogo.vue'
import LangSwitcher from '@/components/ui/LangSwitcher.vue'

/** Вход/регистрация: слева teal-панель с брендом, справа форма (вайрфрейм 2a) */
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="auth">
    <aside class="auth__brand">
      <RouterLink to="/" class="auth__logo" aria-label="bagdar.academy"><BrandLogo dark :height="52" /></RouterLink>
      <div class="auth__pitch">
        <div class="eyebrow">bagdar.academy</div>
        <p class="auth__slogan">{{ $t('auth.brandSlogan') }}</p>
        <p class="auth__note">{{ $t('auth.brandNote') }}</p>
      </div>
      <LangSwitcher dark />
    </aside>
    <section class="auth__form">
      <div class="auth__inner">
        <h1>{{ title }}</h1>
        <p v-if="subtitle" class="muted">{{ subtitle }}</p>
        <slot />
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(320px, 5fr) 7fr;
}
.auth__brand {
  /* Фон «кольца компаса» из дизайн-системы — для титульных экранов */
  background: #0b1a18 url('@/assets/brand/bg-compass-dark.svg') right -266px bottom -173px / 1400px auto no-repeat;
  color: var(--text-on-dark);
  padding: var(--space-xxxl);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-xxl);
}
.auth__logo {
  display: inline-flex;
  align-self: flex-start;
  margin-left: -10px;
}
.auth__pitch .eyebrow {
  color: var(--green-500);
}
.auth__pitch {
  display: grid;
  gap: var(--space-md);
  max-width: 460px;
}
.auth__slogan {
  font: 800 var(--fs-h1) / var(--lh-h1) var(--font-display);
  letter-spacing: -0.6px;
  margin: 0;
}
.auth__note {
  color: var(--text-on-dark-muted);
  margin: 0;
}
.auth__form {
  display: grid;
  place-items: center;
  padding: var(--space-xxxl) var(--space-xl);
  background: var(--canvas);
}
.auth__inner {
  width: min(420px, 100%);
  display: grid;
  gap: var(--space-md);
}
.auth__inner > p {
  margin: -8px 0 0;
}
/* Планшет: сплит сохраняем, панель уже */
@media (max-width: 1024px) {
  .auth {
    grid-template-columns: minmax(260px, 4fr) 6fr;
  }
  .auth__brand {
    padding: var(--space-xxl) var(--space-xl);
  }
  .auth__slogan {
    font-size: var(--fs-h3);
  }
}
/* Телефон: панель сверху */
@media (max-width: 640px) {
  .auth {
    grid-template-columns: 1fr;
  }
  .auth__brand {
    padding: var(--space-xl);
    gap: var(--space-md);
  }
  .auth__slogan {
    font-size: var(--fs-h4);
  }
  .auth__note {
    display: none;
  }
}
</style>
