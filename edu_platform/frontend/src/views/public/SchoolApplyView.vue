<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { errorMessage } from '@/api/http'
import { schoolsApi } from '@/api/schools'
import SchoolPicker from '@/components/schools/SchoolPicker.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { vReveal } from '@/composables/useMotion'
import { useLocaleStore } from '@/stores/locale'
import type { DirectorySchool, NewSchoolPayload, SchoolApplicationPayload } from '@/types/api'

/** «Подключить школу»: заявка → проверка суперпользователем → заявитель становится администратором */
const { t } = useI18n()
const locale = useLocaleStore()

const school = ref<DirectorySchool | null>(null)
const newSchool = ref<NewSchoolPayload | null>(null)
const form = reactive({
  org_type: 'school' as SchoolApplicationPayload['org_type'],
  contact_name: '',
  position: '',
  email: '',
  phone: '',
  students_count: null as number | null,
  bin: '',
  message: '',
  consent: false,
})
const schoolMissing = ref(false)
const sending = ref(false)
const error = ref('')
const sentTo = ref('')

async function submit() {
  error.value = ''
  schoolMissing.value = !school.value && !newSchool.value
  if (schoolMissing.value) {
    error.value = t('register.schoolRequired')
    return
  }
  sending.value = true
  try {
    await schoolsApi.apply({
      ...form,
      school_id: school.value?.id ?? null,
      new_school: newSchool.value,
      language: locale.current,
    })
    sentTo.value = form.email
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="motion-scope container apply">
    <section class="apply__intro">
      <div v-reveal class="eyebrow">bagdar.academy</div>
      <h1 v-reveal="80">{{ $t('schoolApply.title') }}</h1>
      <p v-reveal="160" class="apply__lead">{{ $t('schoolApply.lead') }}</p>
      <ol class="apply__steps">
        <li v-for="n in 3" :key="n" v-reveal="200 + n * 100">
          <span class="apply__num">{{ n }}</span>
          <div>
            <strong>{{ $t(`schoolApply.step${n}`) }}</strong>
            <p class="muted small">{{ $t(`schoolApply.step${n}Text`) }}</p>
          </div>
        </li>
      </ol>
    </section>

    <section v-reveal:right class="card apply__card">
      <div v-if="sentTo" class="apply__done">
        <span class="apply__done-icon"><AppIcon name="check" :size="28" /></span>
        <h2>{{ $t('schoolApply.doneTitle') }}</h2>
        <p class="muted">{{ $t('schoolApply.doneText', { email: sentTo }) }}</p>
        <RouterLink to="/" class="btn btn--ghost">{{ $t('schoolApply.toHome') }}</RouterLink>
      </div>

      <form v-else class="form" @submit.prevent="submit">
        <SchoolPicker v-model:school="school" v-model:new-school="newSchool" required :invalid="schoolMissing" />
        <label>{{ $t('schoolApply.orgType') }}
          <select v-model="form.org_type">
            <option v-for="k in (['school', 'center', 'club'] as const)" :key="k" :value="k">{{ $t(`schoolApply.types.${k}`) }}</option>
          </select>
        </label>

        <h3 class="apply__subtitle">{{ $t('schoolApply.contactTitle') }}</h3>
        <div class="form-row">
          <label>{{ $t('schoolApply.name') }} <input v-model="form.contact_name" autocomplete="name" required maxlength="150" /></label>
          <label>{{ $t('schoolApply.position') }} <input v-model="form.position" :placeholder="$t('schoolApply.positionPh')" maxlength="100" /></label>
        </div>
        <div class="form-row">
          <label>Email
            <input v-model="form.email" type="email" autocomplete="email" required />
          </label>
          <label>{{ $t('schoolApply.phone') }}
            <input v-model="form.phone" type="tel" inputmode="tel" autocomplete="tel" placeholder="+7 700 000 00 00" required maxlength="32" />
          </label>
        </div>
        <p class="muted small apply__hint">{{ $t('schoolApply.emailHint') }}</p>
        <div class="form-row">
          <label>{{ $t('schoolApply.students') }} <input v-model.number="form.students_count" type="number" min="1" max="100000" /></label>
          <label>{{ $t('schoolApply.bin') }} <input v-model="form.bin" inputmode="numeric" maxlength="14" placeholder="000000000000" /></label>
        </div>
        <label>{{ $t('schoolApply.message') }} <textarea v-model="form.message" rows="3" maxlength="2000" /></label>
        <label class="inline consent">
          <input v-model="form.consent" type="checkbox" required />
          <i18n-t keypath="landing.contactConsent" tag="span" scope="global">
            <template #link><RouterLink to="/privacy" target="_blank">{{ $t('landing.contactConsentLink') }}</RouterLink></template>
          </i18n-t>
        </label>
        <p v-if="error" class="alert alert--error">{{ error }}</p>
        <button class="btn btn--lg" :disabled="sending">{{ sending ? $t('landing.contactSending') : $t('schoolApply.submit') }}</button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.apply {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: var(--space-section-sm);
  align-items: start;
  padding-top: var(--space-section-sm);
}
.apply__intro {
  display: grid;
  gap: var(--space-md);
  position: sticky;
  top: calc(var(--nav-height) + var(--space-xl));
}
.apply__intro h1 {
  margin: 0;
  font-size: var(--fs-h1);
  line-height: 1.1;
  letter-spacing: -0.5px;
}
.apply__lead {
  margin: 0;
  font-size: var(--fs-subtitle);
  line-height: 1.55;
  color: var(--text-secondary);
}
.apply__steps {
  list-style: none;
  margin: var(--space-md) 0 0;
  padding: 0;
  display: grid;
  gap: var(--space-lg);
}
.apply__steps li {
  display: flex;
  gap: var(--space-md);
}
.apply__steps p {
  margin: 4px 0 0;
}
.apply__num {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--teal-900);
  color: var(--green-500);
  font: 600 var(--fs-body-sm) / 1 var(--font-sans);
}
.apply__card {
  padding: var(--space-xxl);
}
.apply__subtitle {
  margin: var(--space-sm) 0 0;
  font-size: var(--fs-h5);
}
.apply__hint {
  margin: -8px 0 0;
}
.consent {
  font-size: var(--fs-body-sm);
  color: var(--text-secondary);
}
.consent a {
  text-decoration: underline;
}
.apply__done {
  display: grid;
  gap: var(--space-md);
  justify-items: start;
}
.apply__done h2,
.apply__done p {
  margin: 0;
}
.apply__done-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--green-500);
  color: var(--teal-900);
  animation: pop 0.5s var(--ease-out-expo) both;
}
@keyframes pop {
  from {
    transform: scale(0.4);
    opacity: 0;
  }
}
@media (max-width: 900px) {
  .apply {
    grid-template-columns: 1fr;
  }
  .apply__intro {
    position: static;
  }
  .apply__intro h1 {
    font-size: var(--fs-h2);
  }
}
@media (max-width: 640px) {
  .apply__card {
    padding: var(--space-xl);
  }
}
</style>
