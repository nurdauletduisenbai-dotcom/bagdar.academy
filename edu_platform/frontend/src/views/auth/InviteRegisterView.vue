<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { authApi } from '@/api/auth'
import { errorMessage } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { InvitePreview } from '@/types/api'
import { roleLabel } from '@/utils/format'

import AuthCard from './AuthCard.vue'

/**
 * Регистрация по приглашению. По ссылке из письма данные уже известны: email (логин) зафиксирован,
 * ФИО подставлено — остаётся только пароль. После создания аккаунта ссылка и код больше не действуют.
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const fromLink = typeof route.query.token === 'string' && route.query.token !== ''
const form = reactive({
  invite_token: fromLink ? String(route.query.token) : '',
  email: '', first_name: '', last_name: '', password: '', password2: '',
})
const preview = ref<InvitePreview | null>(null)
const checking = ref(false)
const sending = ref(false)
const signingIn = ref(false)
const error = ref('')

const locked = computed(() => !!preview.value?.email_locked)
const valid = computed(() => preview.value?.status === 'valid')

async function check() {
  if (!form.invite_token.trim()) return
  checking.value = true
  error.value = ''
  try {
    preview.value = await authApi.previewInvite(form.invite_token.trim())
    if (preview.value.status === 'valid') {
      form.email = preview.value.email ?? ''
      form.first_name = preview.value.first_name ?? ''
      form.last_name = preview.value.last_name ?? ''
    }
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    checking.value = false
  }
}

async function onSubmit() {
  error.value = ''
  if (form.password !== form.password2) {
    error.value = t('invite.mismatch')
    return
  }
  sending.value = true
  try {
    await authApi.registerByInvite({
      invite_token: form.invite_token.trim(), email: form.email, password: form.password,
      first_name: form.first_name, last_name: form.last_name,
    })
    // Ссылка израсходована: убираем токен из адреса и сразу входим
    signingIn.value = true
    await router.replace({ query: {} })
    await auth.login({ email: form.email, password: form.password })
    router.push('/home')
  } catch (e) {
    error.value = errorMessage(e)
    signingIn.value = false
    // Например, ссылку только что использовали в другой вкладке — покажем актуальное состояние
    if (!auth.isAuthenticated) await check()
  } finally {
    sending.value = false
  }
}

onMounted(() => fromLink && check())
</script>

<template>
  <AuthCard :title="$t('invite.title')">
    <p v-if="checking" class="muted">{{ $t('invite.checking') }}</p>
    <div v-else-if="signingIn" class="alert alert--success">{{ $t('invite.signingIn') }}</div>

    <!-- Ссылка больше не действует -->
    <div v-else-if="preview && !valid" class="stack">
      <p class="alert" :class="preview.status === 'used' ? 'alert--success' : 'alert--warning'">
        {{ preview.status === 'used' ? $t('invite.used') : preview.status === 'expired' ? $t('invite.expired') : $t('invite.notFound') }}
      </p>
      <RouterLink to="/login" class="btn">{{ $t('auth.submit') }}</RouterLink>
    </div>

    <!-- Кода нет в адресе — вводят вручную -->
    <form v-else-if="!preview" class="form" @submit.prevent="check">
      <label>{{ $t('invite.code') }} <input v-model="form.invite_token" required autocomplete="off" /></label>
      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <button class="btn btn--lg btn--block">{{ $t('invite.check') }}</button>
    </form>

    <!-- Приглашение действует -->
    <form v-else class="form" @submit.prevent="onSubmit">
      <p class="invite__joining">
        {{ $t('invite.joining', { org: preview.org_name, role: preview.role ? roleLabel(preview.role) : '' }) }}
      </p>
      <label>{{ $t('invite.login') }}
        <input v-model="form.email" type="email" autocomplete="username" :readonly="locked" :class="{ locked }" required />
      </label>
      <p v-if="locked" class="muted small invite__hint">{{ $t('invite.emailLocked') }}</p>
      <div class="form-row">
        <label>{{ $t('ui.firstName') }} <input v-model="form.first_name" autocomplete="given-name" required /></label>
        <label>{{ $t('ui.lastName') }} <input v-model="form.last_name" autocomplete="family-name" required /></label>
      </div>
      <p v-if="preview.first_name" class="muted small invite__hint">{{ $t('invite.nameHint') }}</p>
      <label>{{ $t('ui.passwordMin') }}
        <input v-model="form.password" type="password" autocomplete="new-password" minlength="10" required autofocus />
      </label>
      <label>{{ $t('invite.passwordRepeat') }}
        <input v-model="form.password2" type="password" autocomplete="new-password" minlength="10" required />
      </label>
      <p v-if="error" class="alert alert--error">{{ error }}</p>
      <button class="btn btn--lg btn--block" :disabled="sending">{{ $t('invite.createAccount') }}</button>
    </form>
  </AuthCard>
</template>

<style scoped>
.invite__joining {
  margin: 0;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  background: var(--surface-feature);
  color: var(--text-strong);
  font-size: var(--fs-body-sm);
}
.invite__hint {
  margin: -8px 0 0;
}
input.locked {
  background: var(--surface-subtle);
  color: var(--text-secondary);
  cursor: not-allowed;
}
</style>
