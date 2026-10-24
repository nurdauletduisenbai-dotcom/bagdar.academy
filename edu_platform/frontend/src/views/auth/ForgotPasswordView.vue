<script setup lang="ts">
import { ref } from 'vue'

import { authApi } from '@/api/auth'
import { errorMessage } from '@/api/http'

import AuthCard from './AuthCard.vue'

const email = ref('')
const message = ref('')
const error = ref('')

async function onSubmit() {
  error.value = ''
  try {
    message.value = (await authApi.requestPasswordReset(email.value)).message
  } catch (e) {
    error.value = errorMessage(e)
  }
}
</script>

<template>
  <AuthCard :title="$t('titles.forgotPassword')">
    <div v-if="message" class="stack">
      <div class="alert alert--success">{{ message }}</div>
      <i18n-t keypath="forgot.mailhog" tag="p" scope="global" class="muted small"><template #link><a href="http://localhost:8025" target="_blank">localhost:8025</a></template></i18n-t>
    </div>
    <form v-else class="form" @submit.prevent="onSubmit">
      <label>Email <input v-model="email" type="email" required /></label>
      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <button class="btn btn--lg btn--block">{{ $t('forgot.send') }}</button>
      <RouterLink to="/login" class="small">{{ $t('forgot.toLogin') }}</RouterLink>
    </form>
  </AuthCard>
</template>
