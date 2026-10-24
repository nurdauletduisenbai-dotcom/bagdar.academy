<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { authApi } from '@/api/auth'
import { errorMessage } from '@/api/http'

import AuthCard from './AuthCard.vue'

// ?role=parent — с выбора роли на главной странице
const presetRole = useRoute().query.role === 'parent' ? 'parent' : 'student'
const form = reactive({
  email: '', password: '', first_name: '', last_name: '',
  role: presetRole as 'student' | 'parent', org_slug: 'fizmat-school', is_minor: false, parent_consent: false,
})
const error = ref('')
const done = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    done.value = (await authApi.register(form)).message
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
      <label>{{ $t('register.orgSlug') }} <input v-model="form.org_slug" required /></label>
      <label class="inline"><input v-model="form.is_minor" type="checkbox" /> {{ $t('register.minor') }}</label>
      <label v-if="form.is_minor" class="inline"><input v-model="form.parent_consent" type="checkbox" /> {{ $t('register.consent') }}</label>
      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <button class="btn btn--lg btn--block" :disabled="loading">{{ $t('register.submit') }}</button>
      <p class="small muted">{{ $t('register.staffNote') }} <RouterLink to="/login">{{ $t('register.haveAccount') }}</RouterLink></p>
    </form>
  </AuthCard>
</template>
