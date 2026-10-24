<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { authApi } from '@/api/auth'
import { errorMessage } from '@/api/http'

import AuthCard from './AuthCard.vue'

const route = useRoute()
const form = reactive({
  invite_token: typeof route.query.token === 'string' ? route.query.token : '',
  email: '', password: '', first_name: '', last_name: '',
})
const error = ref('')
const done = ref(false)

async function onSubmit() {
  error.value = ''
  try {
    await authApi.registerByInvite(form)
    done.value = true
  } catch (e) {
    error.value = errorMessage(e)
  }
}
</script>

<template>
  <AuthCard :title="$t('invite.title')">
    <div v-if="done" class="stack">
      <div class="alert alert--success">{{ $t('invite.created') }}</div>
      <RouterLink to="/login" class="btn">{{ $t('auth.submit') }}</RouterLink>
    </div>
    <form v-else class="form" @submit.prevent="onSubmit">
      <label>{{ $t('invite.code') }} <input v-model="form.invite_token" required /></label>
      <div class="form-row">
        <label>{{ $t('ui.firstName') }} <input v-model="form.first_name" required /></label>
        <label>{{ $t('ui.lastName') }} <input v-model="form.last_name" required /></label>
      </div>
      <label>Email <input v-model="form.email" type="email" required /></label>
      <label>{{ $t('ui.passwordMin') }} <input v-model="form.password" type="password" minlength="10" required /></label>
      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <button class="btn btn--lg btn--block">{{ $t('invite.createAccount') }}</button>
    </form>
  </AuthCard>
</template>
