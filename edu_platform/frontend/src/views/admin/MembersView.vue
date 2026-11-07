<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { orgsApi } from '@/api/orgs'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppPager from '@/components/ui/AppPager.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { Member, MemberLookup, Role } from '@/types/api'
import { fmtDate, roleLabel, roleOptions } from '@/utils/format'

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()
const filters = reactive({ role: '' as Role | '', search: '', page: 1 })
const members = useAsync(() => orgsApi.members({ role: filters.role || undefined, search: filters.search || undefined, page: filters.page }))
const add = reactive({ role: 'student' as Role })
const addOpen = ref(false)

// ---------- Поиск пользователя для добавления: видно сразу, есть ли он и кто это ----------
const query = ref('')
const found = ref<MemberLookup[]>([])
const picked = ref<MemberLookup | null>(null)
const searching = ref(false)
const looksLikeEmail = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(query.value.trim()))
const hasRole = computed(() => !!picked.value?.roles.includes(add.role))
let lookupTimer: number | undefined
let lookupSeq = 0

watch(query, (q) => {
  if (picked.value && q === picked.value.email) return
  picked.value = null
  window.clearTimeout(lookupTimer)
  if (q.trim().length < 2) {
    found.value = []
    return
  }
  lookupTimer = window.setTimeout(async () => {
    const seq = ++lookupSeq
    searching.value = true
    try {
      const res = await orgsApi.lookupUser(q.trim())
      if (seq !== lookupSeq) return
      found.value = res
      // Точное совпадение email — выбираем сразу
      const exact = res.find((u) => u.email.toLowerCase() === q.trim().toLowerCase())
      if (exact) pick(exact)
    } catch {
      found.value = []
    } finally {
      if (seq === lookupSeq) searching.value = false
    }
  }, 300)
})

function pick(u: MemberLookup) {
  picked.value = u
  query.value = u.email
  found.value = []
}

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
  if (!picked.value || hasRole.value) return
  const email = picked.value.email
  if (await act(() => orgsApi.addMember(email, add.role), t('admin.members.added'))) {
    query.value = ''
    picked.value = null
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

  <form v-if="addOpen" class="card add-member" @submit.prevent="addMember">
    <div class="add-member__row">
      <div class="add-member__field">
        <input v-model="query" type="search" autocomplete="off" :placeholder="$t('admin.members.lookupPh')"
               :aria-label="$t('admin.members.lookupPh')" />
        <ul v-if="found.length && !picked" class="add-member__results">
          <li v-for="u in found" :key="u.id">
            <button type="button" @click="pick(u)">
              <strong>{{ u.full_name }}</strong>
              <span class="muted small">{{ u.email }}<template v-if="u.school"> · {{ u.school }}</template></span>
              <span v-if="u.roles.length" class="badge badge--info">{{ $t('admin.members.lookupAlready') }}: {{ u.roles.map(roleLabel).join(', ') }}</span>
            </button>
          </li>
        </ul>
      </div>
      <select v-model="add.role" :aria-label="$t('admin.invites.role')">
        <option v-for="(label, key) in roleOptions" :key="key" :value="key">{{ label }}</option>
      </select>
      <button class="btn" :disabled="busy || !picked || hasRole">{{ $t('ui.add') }}</button>
    </div>

    <p v-if="picked" class="add-member__status add-member__status--ok">
      <AppIcon name="check" :size="16" />
      <span>
        {{ $t('admin.members.lookupPicked') }}: <strong>{{ picked.full_name }}</strong> · {{ picked.email }}
        <template v-if="picked.school"> · {{ picked.school }}</template>
        —
        <template v-if="picked.roles.length">{{ $t('admin.members.lookupAlready') }}: {{ picked.roles.map(roleLabel).join(', ') }}</template>
        <template v-else>{{ $t('admin.members.lookupNotMember') }}</template>
        <template v-if="hasRole">. {{ $t('admin.members.lookupHasRole') }}</template>
      </span>
    </p>
    <p v-else-if="searching" class="add-member__status muted">{{ $t('admin.members.lookupSearching') }}</p>
    <p v-else-if="looksLikeEmail && !found.length" class="add-member__status add-member__status--no">
      <AppIcon name="x" :size="16" />
      <span>{{ $t('admin.members.lookupNotFound') }} <RouterLink to="/admin/invites">{{ $t('admin.members.lookupInvite') }} →</RouterLink></span>
    </p>
    <p v-else class="add-member__status muted">{{ $t('admin.members.lookupHint') }}</p>
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

<style scoped>
.add-member {
  display: grid;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}
.add-member__row {
  display: flex;
  gap: var(--space-sm);
  align-items: flex-start;
  flex-wrap: wrap;
}
.add-member__row > select {
  max-width: 180px;
}
.add-member__field {
  position: relative;
  flex: 1;
  min-width: 240px;
  max-width: 420px;
}
.add-member__results {
  position: absolute;
  z-index: 5;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-3);
  max-height: 320px;
  overflow-y: auto;
}
.add-member__results button {
  display: grid;
  gap: 2px;
  justify-items: start;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--radius-sm);
  background: none;
  font: inherit;
  text-align: left;
  color: var(--text-strong);
  cursor: pointer;
}
.add-member__results button:hover,
.add-member__results button:focus-visible {
  background: var(--surface-subtle);
  outline: none;
}
.add-member__status {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0;
  font-size: var(--fs-body-sm);
}
.add-member__status--ok :deep(svg) {
  color: var(--green-dark);
  flex-shrink: 0;
  margin-top: 2px;
}
.add-member__status--no {
  color: var(--error-text);
}
.add-member__status--no :deep(svg) {
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
