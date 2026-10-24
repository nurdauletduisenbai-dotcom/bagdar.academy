<script setup lang="ts">
import QRCode from 'qrcode'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { authApi, parentsApi } from '@/api/auth'
import { notificationsApi } from '@/api/notifications'
import SchoolPicker from '@/components/schools/SchoolPicker.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { DirectorySchool, NewSchoolPayload, TwoFactorSetup } from '@/types/api'
import { fmtDateTime } from '@/utils/format'

const { t } = useI18n()

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { act, busy } = useAction()
const tab = ref<'profile' | 'security' | 'notifications' | 'parents'>('profile')

// ---------- Профиль ----------
const profile = useAsync(() => authApi.me())
const form = reactive({ first_name: '', last_name: '', phone: '', language: 'ru' as 'ru' | 'kk' | 'en', birth_date: '' })
onMounted(async () => {
  const p = await profile.run()
  if (p) Object.assign(form, { first_name: p.first_name, last_name: p.last_name, phone: p.phone ?? '', language: p.language, birth_date: p.birth_date ?? '' })
})

// ---------- Школа ----------
const pickedSchool = ref<DirectorySchool | null>(null)
const ownSchool = ref<NewSchoolPayload | null>(null)
async function saveSchool() {
  const p = await act(() => authApi.setSchool({ school_id: pickedSchool.value?.id ?? null, new_school: ownSchool.value }),
    t('schoolPicker.saved'))
  if (p) {
    profile.data.value = p
    pickedSchool.value = null
    ownSchool.value = null
  }
}

async function saveProfile() {
  await act(() => authApi.updateMe({ ...form, phone: form.phone || null, birth_date: form.birth_date || null }), t('profile.saved'))
  await auth.loadProfile(auth.user?.org_id ?? null)
}

// ---------- Безопасность ----------
const passwords = reactive({ old: '', next: '' })
async function changePassword() {
  const ok = await act(() => authApi.changePassword(passwords.old, passwords.next), t('profile.passwordChanged'))
  if (ok) {
    await auth.logout()
    router.push({ name: 'login' })
  }
}

const sessions = useAsync(() => authApi.sessions(), { immediate: false })
async function revoke(id: number) {
  await act(() => authApi.revokeSession(id), t('profile.sessionEnded'))
  sessions.run()
}
async function logoutAll() {
  await act(() => authApi.logoutAll(), t('profile.loggedOutAll'))
  await auth.logout()
  router.push({ name: 'login' })
}

const twoFa = ref<TwoFactorSetup | null>(null)
const qr = ref('')
const code = ref('')
const backupCodes = ref<string[]>([])
const disableForm = reactive({ password: '', code: '' })
async function startTwoFa() {
  const setup = await act(() => authApi.twoFactorSetup())
  if (setup) {
    twoFa.value = setup
    qr.value = await QRCode.toDataURL(setup.otpauth_uri, { width: 200 })
  }
}
async function enableTwoFa() {
  const result = await act(() => authApi.twoFactorEnable(code.value), t('profile.twoFaOn'))
  if (result) {
    backupCodes.value = result.backup_codes
    twoFa.value = null
  }
}
async function disableTwoFa() {
  await act(() => authApi.twoFactorDisable(disableForm.password, disableForm.code), t('profile.twoFaOff'))
}

// ---------- Уведомления ----------
const prefs = useAsync(() => notificationsApi.preferences(), { immediate: false })
async function savePrefs() {
  if (prefs.data.value) await act(() => notificationsApi.updatePreferences(prefs.data.value!), t('profile.prefsSaved'))
}

// ---------- Родители ----------
const requests = useAsync(() => parentsApi.requests(), { immediate: false })
async function confirmParent(id: number) {
  await act(() => parentsApi.confirm(id), t('profile.parentAllowed'))
  requests.run()
}
async function rejectParent(id: number) {
  await act(() => parentsApi.reject(id), t('profile.accessClosed'))
  requests.run()
}

function open(next: typeof tab.value) {
  tab.value = next
  if (next === 'security') sessions.run()
  if (next === 'notifications') prefs.run()
  if (next === 'parents') requests.run()
}

onMounted(() => {
  const wanted = route.query.tab
  if (wanted === 'security' || wanted === 'notifications' || wanted === 'parents') open(wanted)
})

async function resend() {
  await act(() => authApi.resendVerification(), t('profile.emailSent'))
}
</script>

<template>
  <PageHeader :title="$t('profile.title')" :subtitle="auth.user?.email" />

  <div class="split split--nav">
    <nav class="side-nav card">
      <button :class="{ active: tab === 'profile' }" @click="open('profile')">{{ $t('profile.tabProfile') }}</button>
      <button :class="{ active: tab === 'security' }" @click="open('security')">{{ $t('profile.tabSecurity') }}</button>
      <button :class="{ active: tab === 'notifications' }" @click="open('notifications')">{{ $t('profile.tabNotifications') }}</button>
      <button v-if="auth.isStudent" :class="{ active: tab === 'parents' }" @click="open('parents')">{{ $t('profile.tabParents') }}</button>
      <RouterLink v-if="auth.hasRole('student', 'parent')" to="/orders">{{ $t('titles.myOrders') }}</RouterLink>
    </nav>

    <div class="stack">
      <section v-if="tab === 'profile'" class="card">
        <StateBlock :loading="profile.loading.value" :error="profile.error.value" @retry="profile.run">
          <form class="form" @submit.prevent="saveProfile">
            <div class="form-row">
              <label>{{ $t('ui.firstName') }} <input v-model="form.first_name" required /></label>
              <label>{{ $t('ui.lastName') }} <input v-model="form.last_name" required /></label>
            </div>
            <div class="form-row">
              <label>{{ $t('profile.phone') }} <input v-model="form.phone" placeholder="+7 …" /></label>
              <label>{{ $t('profile.birthDate') }} <input v-model="form.birth_date" type="date" /></label>
              <label>
                {{ $t('profile.language') }}
                <select v-model="form.language">
                  <option value="ru">{{ $t("lang.ru") }}</option>
                  <option value="kk">{{ $t("lang.kk") }}</option>
                  <option value="en">English</option>
                </select>
              </label>
            </div>
            <div class="row">
              <button class="btn" :disabled="busy">{{ $t('common.save') }}</button>
              <button v-if="profile.data.value && !profile.data.value.is_verified" type="button" class="btn btn--ghost" @click="resend">
                {{ $t('profile.verifyEmail') }}
              </button>
            </div>
          </form>
        </StateBlock>
      </section>

      <section v-if="tab === 'profile' && profile.data.value" class="card stack">
        <h2>{{ $t('schoolPicker.label') }}</h2>
        <p v-if="profile.data.value.school" class="row">
          <strong>{{ profile.data.value.school.name }}</strong>
          <span v-if="profile.data.value.school.locality" class="muted small">{{ profile.data.value.school.locality }}</span>
          <span v-if="!profile.data.value.school.is_approved" class="badge badge--warning">{{ $t('schoolPicker.pending') }}</span>
        </p>
        <p v-else class="muted small">{{ $t('schoolPicker.none') }}</p>
        <SchoolPicker v-model:school="pickedSchool" v-model:new-school="ownSchool" />
        <div class="row">
          <button class="btn" :disabled="busy || (!pickedSchool && !ownSchool)" @click="saveSchool">{{ $t('common.save') }}</button>
        </div>
      </section>

      <template v-if="tab === 'security'">
        <section class="card setting">
          <div class="setting__head">
            <div>
              <h2>{{ $t('profile.twoFaTitle') }}</h2>
              <p class="muted small">{{ $t('profile.twoFaHint') }}</p>
            </div>
            <button v-if="!twoFa && !backupCodes.length" class="btn btn--sm" :disabled="busy" @click="startTwoFa">{{ $t('profile.setup') }}</button>
          </div>
          <div v-if="backupCodes.length" class="stack">
            <div class="alert alert--success">{{ $t('profile.backupCodes') }}</div>
            <pre class="code">{{ backupCodes.join('\n') }}</pre>
          </div>
          <div v-else-if="twoFa" class="twofa">
            <img :src="qr" :alt="$t('profile.qrAlt')" width="180" height="180" />
            <div class="stack">
              <p class="small">{{ $t('profile.scan') }}</p>
              <p class="muted small">{{ $t('profile.manualKey') }} <code>{{ twoFa.secret }}</code></p>
              <form class="row" @submit.prevent="enableTwoFa">
                <input v-model="code" inputmode="numeric" placeholder="123456" style="max-width: 160px" required />
                <button class="btn" :disabled="busy">{{ $t('profile.enable') }}</button>
              </form>
            </div>
          </div>
          <details v-else>
            <summary class="small">{{ $t('profile.alreadyOn') }}</summary>
            <form class="form" style="margin-top: var(--space-sm)" @submit.prevent="disableTwoFa">
              <div class="form-row">
                <label>{{ $t('auth.password') }} <input v-model="disableForm.password" type="password" required /></label>
                <label>{{ $t('profile.code2fa') }} <input v-model="disableForm.code" required /></label>
              </div>
              <button class="btn btn--danger btn--sm" :disabled="busy" style="justify-self: start">{{ $t('profile.disable') }}</button>
            </form>
          </details>
        </section>

        <section class="card setting">
          <div class="setting__head">
            <h2>{{ $t('profile.sessions') }}</h2>
            <button class="btn btn--danger btn--sm" @click="logoutAll">{{ $t('profile.logoutAll') }}</button>
          </div>
          <StateBlock :loading="sessions.loading.value" :error="sessions.error.value" :empty="!sessions.data.value?.length" @retry="sessions.run">
            <ul class="list-lines">
              <li v-for="s in sessions.data.value ?? []" :key="s.id" class="row row--between">
                <span class="session-info">
                  <span class="small">{{ s.device_info || $t('profile.unknownDevice') }}</span>
                  <span class="muted small">{{ s.ip }} · {{ fmtDateTime(s.created_at) }}</span>
                </span>
                <span v-if="s.is_current" class="badge badge--success">{{ $t('profile.thisIsYou') }}</span>
                <button v-else class="btn btn--text btn--sm" @click="revoke(s.id)">{{ $t('profile.endSession') }}</button>
              </li>
            </ul>
          </StateBlock>
        </section>

        <section class="card setting">
          <h2>{{ $t('auth.password') }}</h2>
          <form class="form" @submit.prevent="changePassword">
            <div class="form-row">
              <label>{{ $t('profile.currentPassword') }} <input v-model="passwords.old" type="password" required /></label>
              <label>{{ $t('profile.newPassword') }} <input v-model="passwords.next" type="password" minlength="10" required /></label>
            </div>
            <button class="btn btn--ghost" :disabled="busy" style="justify-self: start">{{ $t('profile.change') }}</button>
          </form>
        </section>
      </template>

      <section v-if="tab === 'notifications'" class="card">
        <StateBlock :loading="prefs.loading.value" :error="prefs.error.value" @retry="prefs.run">
          <form v-if="prefs.data.value" class="form" @submit.prevent="savePrefs">
            <label class="inline"><input v-model="prefs.data.value.in_app_enabled" type="checkbox" /> {{ $t('profile.inApp') }}</label>
            <label class="inline"><input v-model="prefs.data.value.email_enabled" type="checkbox" /> {{ $t('profile.emailNotif') }}</label>
            <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('common.save') }}</button>
          </form>
        </StateBlock>
      </section>

      <section v-if="tab === 'parents'" class="card">
        <h2>{{ $t('profile.whoSees') }}</h2>
        <StateBlock :loading="requests.loading.value" :error="requests.error.value" :empty="!requests.data.value?.length"
                    :empty-text="$t('profile.noRequests')" @retry="requests.run">
          <ul class="list-lines">
            <li v-for="r in requests.data.value ?? []" :key="r.id" class="row row--between">
              <span>{{ r.parent.full_name }} <span class="muted small">{{ r.parent.email }}</span></span>
              <span class="row">
                <span v-if="r.is_confirmed" class="badge badge--success">{{ $t('profile.confirmed') }}</span>
                <button v-else class="btn btn--sm" @click="confirmParent(r.id)">{{ $t('ui.confirm') }}</button>
                <button class="btn btn--text btn--sm" @click="rejectParent(r.id)">{{ r.is_confirmed ? $t('profile.closeAccess') : $t('profile.reject') }}</button>
              </span>
            </li>
          </ul>
        </StateBlock>
      </section>
    </div>
  </div>
</template>

<style scoped>
.side-nav.card {
  padding: var(--space-xs);
  position: sticky;
  top: calc(var(--nav-height) + var(--space-md));
}
.setting {
  display: grid;
  gap: var(--space-md);
}
.setting__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-md);
}
.setting__head h2,
.setting__head p {
  margin: 0;
}
.twofa {
  display: flex;
  gap: var(--space-xl);
  align-items: flex-start;
  flex-wrap: wrap;
}
.twofa p {
  margin: 0;
}
.session-info {
  display: grid;
}
</style>
