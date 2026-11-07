<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { authApi } from '@/api/auth'
import { errorMessage } from '@/api/http'
import SchoolPicker from '@/components/schools/SchoolPicker.vue'
import type { DirectorySchool, NewSchoolPayload } from '@/types/api'

import AuthCard from './AuthCard.vue'

const { t } = useI18n()
// ?role=parent — с выбора роли на главной странице
const presetRole = useRoute().query.role === 'parent' ? 'parent' : 'student'
const form = reactive({
  email: '', password: '', first_name: '', last_name: '',
  role: presetRole as 'student' | 'parent', is_minor: false, parent_consent: false,
})
// Школа: из справочника или своя (кружок, учебный центр); ученику обязательна, родителю — нет
const school = ref<DirectorySchool | null>(null)
const newSchool = ref<NewSchoolPayload | null>(null)
const schoolMissing = ref(false)
const error = ref('')
const done = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  schoolMissing.value = form.role === 'student' && !school.value && !newSchool.value
  if (schoolMissing.value) {
    error.value = t('register.schoolRequired')
    return
  }
  loading.value = true
  try {
    done.value = (await authApi.register({ ...form, school_id: school.value?.id ?? null, new_school: newSchool.value })).message
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthCard :title="$t('titles.register')">
    <div v-if="done" class="stack">
      <div class="alert alert--success">{{ done }}</div>
      <i18n-t keypath="register.mailhog" tag="p" scope="global" class="muted small"><template #link><a href="http://localhost:8025" target="_blank">localhost:8025</a></template></i18n-t>
      <RouterLink to="/login" class="btn">{{ $t('auth.submit') }}</RouterLink>
    </div>
    <form v-else class="form" @submit.prevent="onSubmit">
      <div class="form-row">
        <label>{{ $t('ui.firstName') }} <input v-model="form.first_name" required /></label>
        <label>{{ $t('ui.lastName') }} <input v-model="form.last_name" required /></label>
      </div>
      <label>Email <input v-model="form.email" type="email" required /></label>
      <label>{{ $t('ui.passwordMin') }} <input v-model="form.password" type="password" minlength="10" required /></label>
      <label>
        {{ $t('register.as') }}
        <select v-model="form.role">
          <option value="student">{{ $t("roles.student") }}</option>
          <option value="parent">{{ $t("roles.parent") }}</option>
        </select>
      </label>
      <SchoolPicker v-model:school="school" v-model:new-school="newSchool" :required="form.role === 'student'"
                    :invalid="schoolMissing" />
      <label class="inline"><input v-model="form.is_minor" type="checkbox" /> {{ $t('register.minor') }}</label>
      <label v-if="form.is_minor" class="inline"><input v-model="form.parent_consent" type="checkbox" /> {{ $t('register.consent') }}</label>
      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <button class="btn btn--lg btn--block" :disabled="loading">{{ $t('register.submit') }}</button>
      <i18n-t keypath="auth.registerPrivacy" tag="p" class="small muted" scope="global">
        <template #link><RouterLink to="/privacy" target="_blank">{{ $t('auth.registerPrivacyLink') }}</RouterLink></template>
      </i18n-t>
      <p class="small muted">{{ $t('register.staffNote') }} <RouterLink to="/login">{{ $t('register.haveAccount') }}</RouterLink></p>
      <p class="small muted">{{ $t('register.schoolRep') }} <RouterLink to="/schools/apply">{{ $t('schoolApply.cta') }} →</RouterLink></p>
    </form>
  </AuthCard>
</template>
