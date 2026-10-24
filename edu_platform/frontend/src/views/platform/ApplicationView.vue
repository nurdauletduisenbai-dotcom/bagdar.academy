<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { SCHOOL_KINDS, applicationsApi, schoolsApi } from '@/api/schools'
import SchoolPicker from '@/components/schools/SchoolPicker.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useToast } from '@/stores/toast'
import type { ApplicationStatus, DirectorySchool, ManagedApplication, NewSchoolPayload } from '@/types/api'
import { fmtDateTime } from '@/utils/format'

/** Карточка заявки школы: правка данных школы и заявителя, замена школы, решение */
const props = defineProps<{ id: string }>()
const { t, locale } = useI18n()
const toast = useToast()
const { act, busy } = useAction()

const app = useAsync(() => applicationsApi.get(Number(props.id)))
const regions = useAsync(() => schoolsApi.regions())

const school = reactive({ name: '', name_kk: '', name_ru: '', kind: 'school' as ManagedApplication['school']['kind'], region: 0, locality: '' })
const applicant = reactive({
  org_type: 'school' as ManagedApplication['org_type'], contact_name: '', position: '', email: '', phone: '',
  students_count: null as number | null, bin: '', message: '',
})
const note = ref('')
const replacement = ref<DirectorySchool | null>(null)
const ignoredNew = ref<NewSchoolPayload | null>(null)

function fill(a: ManagedApplication) {
  Object.assign(school, {
    name: a.school.name, name_kk: a.school.name_kk, name_ru: a.school.name_ru, kind: a.school.kind,
    region: a.school.region, locality: a.school.locality,
  })
  Object.assign(applicant, {
    org_type: a.org_type, contact_name: a.contact_name, position: a.position, email: a.email, phone: a.phone,
    students_count: a.students_count, bin: a.bin, message: a.message,
  })
  note.value = a.review_note
}
watch(() => app.data.value, (a) => a && fill(a), { immediate: true })

const a = computed(() => app.data.value)
const locked = computed(() => a.value?.status === 'approved')
const hasAdmins = computed(() => !!a.value?.school.admins.length)
const badge: Record<ApplicationStatus, string> = {
  new: 'badge--info', needs_info: 'badge--warning', approved: 'badge--success', rejected: 'badge--danger',
}
const regionName = (r: { name_kk: string; name_ru: string }) => (locale.value === 'kk' ? r.name_kk : r.name_ru)

async function saveSchool() {
  const res = await act(() => applicationsApi.update(Number(props.id), { school_edit: { ...school } }), t('platformApps.saved'))
  if (res) app.data.value = res
}

async function saveApplicant() {
  const res = await act(() => applicationsApi.update(Number(props.id), { ...applicant }), t('platformApps.saved'))
  if (res) app.data.value = res
}

async function replaceSchool() {
  if (!replacement.value) return
  const res = await act(() => applicationsApi.update(Number(props.id), { school_id: replacement.value!.id }), t('platformApps.saved'))
  if (res) {
    app.data.value = res
    replacement.value = null
  }
}

const changed = () => window.dispatchEvent(new Event('applications-changed'))

async function approve() {
  if (!a.value || !confirm(t('platformApps.approveConfirm', { school: a.value.school.name }))) return
  const res = await act(() => applicationsApi.approve(Number(props.id)))
  if (res) {
    app.data.value = res
    changed()
    const r = res.result
    toast.success(r?.invited
      ? t('platformApps.approvedInvited', { email: res.email })
      : t('platformApps.approvedMember', { email: res.email, org: r?.org_name ?? '' }))
  }
}

async function reject() {
  if (!confirm(t('platformApps.rejectConfirm'))) return
  const res = await act(() => applicationsApi.reject(Number(props.id), note.value), t('platformApps.rejected'))
  if (res) {
    app.data.value = res
    changed()
  }
}

async function requestInfo() {
  if (!note.value.trim()) {
    toast.error(t('platformApps.noteRequired'))
    return
  }
  const res = await act(() => applicationsApi.requestInfo(Number(props.id), note.value), t('platformApps.infoSent'))
  if (res) {
    app.data.value = res
    changed()
  }
}
</script>

<template>
  <RouterLink :to="{ name: 'platform-applications' }" class="back small"><AppIcon name="arrow-left" :size="14" /> {{ $t('platformApps.back') }}</RouterLink>

  <StateBlock :loading="app.loading.value" :error="app.error.value" @retry="app.run">
    <template v-if="a">
      <header class="head">
        <div>
          <div class="eyebrow">{{ $t(`schoolApply.types.${a.org_type}`) }} · #{{ a.id }}</div>
          <h1>{{ a.school.name }}</h1>
          <p class="muted small">{{ $t('platformApps.colDate') }}: {{ fmtDateTime(a.created_at) }} · {{ $t('platformApps.siteLang') }}: {{ a.language || '—' }}</p>
        </div>
        <span class="badge" :class="badge[a.status]">{{ $t(`platformApps.status.${a.status}`) }}</span>
      </header>

      <p v-if="a.is_claim || hasAdmins" class="alert alert--warning">{{ $t('platformApps.claimWarn') }}</p>
      <p v-if="locked" class="alert alert--success">{{ $t('platformApps.locked') }}</p>

      <div class="layout">
        <div class="stack">
          <!-- Школа -->
          <section class="card stack">
            <h2>{{ $t('platformApps.schoolCard') }}</h2>
            <ul class="facts small">
              <li>{{ a.school.organization ? $t('platformApps.orgExists') : $t('platformApps.orgNone') }}</li>
              <li>{{ $t('platformApps.admins') }}: {{ a.school.admins.join(', ') || $t('platformApps.noAdmins') }}</li>
              <li v-if="!a.school.is_approved">{{ $t('platformApps.pendingSchool') }}</li>
            </ul>
            <form class="form" @submit.prevent="saveSchool">
              <label>{{ $t('platformApps.schoolName') }} <input v-model="school.name" :disabled="locked" required minlength="3" /></label>
              <div class="form-row">
                <label>{{ $t('platformApps.nameKk') }} <input v-model="school.name_kk" :disabled="locked" /></label>
                <label>{{ $t('platformApps.nameRu') }} <input v-model="school.name_ru" :disabled="locked" /></label>
              </div>
              <div class="form-row">
                <label>{{ $t('platformApps.kind') }}
                  <select v-model="school.kind" :disabled="locked">
                    <option v-for="k in SCHOOL_KINDS" :key="k" :value="k">{{ $t(`schoolPicker.kinds.${k}`) }}</option>
                  </select>
                </label>
                <label>{{ $t('platformApps.region') }}
                  <select v-model="school.region" :disabled="locked">
                    <option v-for="r in regions.data.value ?? []" :key="r.id" :value="r.id">{{ regionName(r) }}</option>
                  </select>
                </label>
                <label>{{ $t('platformApps.locality') }} <input v-model="school.locality" :disabled="locked" /></label>
              </div>
              <button v-if="!locked" class="btn btn--ghost" :disabled="busy">{{ $t('common.save') }}</button>
            </form>

            <div v-if="!locked" class="replace">
              <h3>{{ $t('platformApps.replaceSchool') }}</h3>
              <p class="muted small">{{ $t('platformApps.replaceHint') }}</p>
              <div class="row replace__row">
                <SchoolPicker v-model:school="replacement" v-model:new-school="ignoredNew" class="replace__picker" />
                <button class="btn btn--ghost" :disabled="busy || !replacement" @click="replaceSchool">{{ $t('platformApps.replace') }}</button>
              </div>
            </div>
          </section>

          <!-- Заявитель -->
          <section class="card stack">
            <h2>{{ $t('platformApps.applicantCard') }}</h2>
            <form class="form" @submit.prevent="saveApplicant">
              <label>{{ $t('schoolApply.orgType') }}
                <select v-model="applicant.org_type" :disabled="locked">
                  <option v-for="k in (['school', 'center', 'club'] as const)" :key="k" :value="k">{{ $t(`schoolApply.types.${k}`) }}</option>
                </select>
              </label>
              <div class="form-row">
                <label>{{ $t('schoolApply.name') }} <input v-model="applicant.contact_name" :disabled="locked" required /></label>
                <label>{{ $t('schoolApply.position') }} <input v-model="applicant.position" :disabled="locked" /></label>
              </div>
              <div class="form-row">
                <label>Email <input v-model="applicant.email" type="email" :disabled="locked" required /></label>
                <label>{{ $t('schoolApply.phone') }} <input v-model="applicant.phone" type="tel" :disabled="locked" required /></label>
              </div>
              <div class="form-row">
                <label>{{ $t('schoolApply.students') }} <input v-model.number="applicant.students_count" type="number" min="1" :disabled="locked" /></label>
                <label>{{ $t('schoolApply.bin') }} <input v-model="applicant.bin" inputmode="numeric" :disabled="locked" /></label>
              </div>
              <label>{{ $t('schoolApply.message') }} <textarea v-model="applicant.message" rows="3" :disabled="locked" /></label>
              <button v-if="!locked" class="btn btn--ghost" :disabled="busy">{{ $t('common.save') }}</button>
            </form>
          </section>
        </div>

        <!-- Решение -->
        <aside class="card stack decision">
          <h2>{{ $t('platformApps.decision') }}</h2>
          <template v-if="!locked">
            <button class="btn btn--block" :disabled="busy" @click="approve">{{ $t('platformApps.approve') }}</button>
            <p class="muted small">{{ $t('platformApps.approveHint') }}</p>
            <label>{{ $t('platformApps.note') }}
              <textarea v-model="note" rows="4" />
            </label>
            <p class="muted small">{{ $t('platformApps.noteHint') }}</p>
            <div class="row decision__row">
              <button class="btn btn--ghost btn--sm" :disabled="busy" @click="requestInfo">{{ $t('platformApps.requestInfo') }}</button>
              <button class="btn btn--danger btn--sm" :disabled="busy || a.status === 'rejected'" @click="reject">{{ $t('platformApps.reject') }}</button>
            </div>
          </template>
          <p v-if="a.reviewed_by_email" class="muted small">
            {{ $t('platformApps.reviewed', { email: a.reviewed_by_email, date: fmtDateTime(a.reviewed_at) }) }}
          </p>
        </aside>
      </div>
    </template>
  </StateBlock>
</template>

<style scoped>
.back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-bottom: var(--space-md);
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}
.head h1 {
  margin: 4px 0;
}
.head p {
  margin: 0;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: var(--space-lg);
  align-items: start;
}
.card h2 {
  margin: 0;
  font-size: var(--fs-h4);
}
.facts {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  display: grid;
  gap: 2px;
}
.replace {
  border-top: 1px solid var(--border-default);
  padding-top: var(--space-md);
}
.replace h3 {
  margin: 0;
  font-size: var(--fs-h5);
}
.replace p {
  margin: 4px 0 var(--space-sm);
}
.replace__row {
  align-items: flex-end;
  flex-wrap: wrap;
}
.replace__picker {
  flex: 1;
  min-width: 240px;
}
.decision {
  position: sticky;
  top: calc(var(--nav-height) + var(--space-lg));
}
.decision p {
  margin: 0;
}
.decision__row {
  flex-wrap: wrap;
}
@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .decision {
    position: static;
  }
}
</style>
