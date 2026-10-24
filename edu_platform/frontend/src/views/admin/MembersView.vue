<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { orgsApi } from '@/api/orgs'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppPager from '@/components/ui/AppPager.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { Member, Role } from '@/types/api'
import { fmtDate, roleLabel, roleOptions } from '@/utils/format'

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()
const filters = reactive({ role: '' as Role | '', search: '', page: 1 })
const members = useAsync(() => orgsApi.members({ role: filters.role || undefined, search: filters.search || undefined, page: filters.page }))
const add = reactive({ email: '', role: 'student' as Role })
const addOpen = ref(false)

function apply() {
  filters.page = 1
  members.run()
}

async function changeRole(m: Member, role: Role) {
  if (await act(() => orgsApi.updateMember(m.id, { role }), t('admin.members.roleChanged'))) members.run()
}

async function toggleActive(m: Member) {
  const fn = (): Promise<unknown> =>
    m.is_active ? orgsApi.deactivateMember(m.id) : orgsApi.updateMember(m.id, { is_active: true })
  if (await act(fn, m.is_active ? t('admin.members.deactivated') : t('admin.members.activated'))) members.run()
}

async function addMember() {
  if (await act(() => orgsApi.addMember(add.email, add.role), t('admin.members.added'))) {
    add.email = ''
    addOpen.value = false
    members.run()
  }
}
</script>

<template>
  <PageHeader :title="$t('nav.members')">
    <button v-if="auth.isAdmin" class="btn btn--ghost" @click="addOpen = !addOpen">{{ $t('admin.members.addExisting') }}</button>
    <RouterLink to="/admin/invites" class="btn">{{ $t('admin.members.invite') }}</RouterLink>
  </PageHeader>

  <form v-if="addOpen" class="card row" style="margin-bottom: var(--space-lg)" @submit.prevent="addMember">
    <input v-model="add.email" type="email" :placeholder="$t('admin.members.emailPh')" style="max-width: 300px" required />
    <select v-model="add.role" style="max-width: 180px">
      <option v-for="(label, key) in roleOptions" :key="key" :value="key">{{ label }}</option>
    </select>
    <button class="btn" :disabled="busy">{{ $t('ui.add') }}</button>
  </form>

  <div class="row row--between" style="margin-bottom: var(--space-lg)">
    <div class="pills">
      <button class="pill" :class="{ active: !filters.role }" @click="filters.role = ''; apply()">{{ $t('ui.all') }} <span class="count">{{ filters.role ? '' : members.data.value?.total ?? '' }}</span></button>
      <button class="pill" :class="{ active: filters.role === 'student' }" @click="filters.role = 'student'; apply()">{{ $t('admin.members.f.student') }}</button>
      <button class="pill" :class="{ active: filters.role === 'teacher' }" @click="filters.role = 'teacher'; apply()">{{ $t('admin.members.f.teacher') }}</button>
      <button class="pill" :class="{ active: filters.role === 'parent' }" @click="filters.role = 'parent'; apply()">{{ $t('admin.members.f.parent') }}</button>
      <button class="pill" :class="{ active: filters.role === 'curator' }" @click="filters.role = 'curator'; apply()">{{ $t('admin.members.f.curator') }}</button>
      <button class="pill" :class="{ active: filters.role === 'admin' }" @click="filters.role = 'admin'; apply()">{{ $t('admin.members.f.admin') }}</button>
      <RouterLink v-if="auth.isTeacher" to="/admin/invites" class="pill">{{ $t('titles.invites') }}</RouterLink>
    </div>
    <form class="search" style="width: 260px" @submit.prevent="apply">
      <AppIcon name="search" /><input v-model="filters.search" type="search" :placeholder="$t('admin.members.searchPh')" :aria-label="$t('admin.members.searchLabel')" />
    </form>
  </div>

  <StateBlock :loading="members.loading.value" :error="members.error.value" :empty="!members.data.value?.results.length" @retry="members.run">
    <div class="card card--flush table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('admin.members.colUser') }}</th><th>{{ $t('admin.invites.role') }}</th><th>{{ $t('admin.members.colSince') }}</th><th>{{ $t('teach.courseForm.status') }}</th><th></th></tr></thead>
        <tbody>
          <tr v-for="m in members.data.value?.results ?? []" :key="m.id">
            <td><strong>{{ m.full_name }}</strong><div class="muted small">{{ m.email }}</div></td>
            <td>
              <select v-if="auth.isAdmin" :value="m.role" style="max-width: 170px; height: 36px" @change="changeRole(m, ($event.target as HTMLSelectElement).value as Role)">
                <option v-for="(label, key) in roleOptions" :key="key" :value="key">{{ label }}</option>
              </select>
              <span v-else>{{ roleLabel(m.role) }}</span>
            </td>
            <td class="small">{{ fmtDate(m.created_at) }}</td>
            <td><AppBadge :kind="m.is_active ? 'success' : 'default'">{{ m.is_active ? $t('admin.members.active') : $t('admin.members.inactive') }}</AppBadge></td>
            <td>
              <button v-if="auth.isAdmin && m.user !== auth.user?.id" class="btn btn--text btn--sm" :disabled="busy" @click="toggleActive(m)">
                {{ m.is_active ? $t('admin.members.deactivate') : $t('admin.members.activate') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <AppPager :page="filters.page" :total-pages="members.data.value?.total_pages ?? 1" @change="(p) => { filters.page = p; members.run() }" />
  </StateBlock>
</template>
