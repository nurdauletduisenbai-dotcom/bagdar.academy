<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { coursesApi, groupsApi } from '@/api/courses'
import { orgsApi } from '@/api/orgs'
import AppBadge from '@/components/ui/AppBadge.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { Group, Invite, Role } from '@/types/api'
import { fmtDateTime, roleLabel, roleOptions } from '@/utils/format'

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()
const invites = useAsync(() => (auth.isAdmin ? orgsApi.invites() : Promise.resolve(null)))
const courses = useAsync(() => coursesApi.list())
const groups = ref<Group[]>([])
const form = reactive({ role: 'student' as Role, course_id: null as number | null, group_id: null as number | null, max_uses: 1, expires_in_days: 7 })
const created = ref<Invite | null>(null)
const inviteLink = (token: string) => `${window.location.origin}/invite?token=${encodeURIComponent(token)}`

async function onCourse() {
  form.group_id = null
  groups.value = form.course_id ? await groupsApi.list(form.course_id) : []
}

async function create() {
  const invite = await act(() => orgsApi.createInvite(form), t('admin.invites.created'))
  if (invite) {
    created.value = invite
    invites.run()
  }
}

async function copy(text: string) {
  await act(() => navigator.clipboard.writeText(text), t('admin.invites.copied'))
}

async function revoke(id: number) {
  if (await act(() => orgsApi.revokeInvite(id), t('admin.invites.revoked'))) invites.run()
}
</script>

<template>
  <PageHeader :title="$t('titles.invites')" :subtitle="$t('admin.invites.subtitle')" />

  <div class="grid--2" style="align-items: start">
    <section class="card">
      <h2>{{ $t('admin.invites.new') }}</h2>
      <form class="form" @submit.prevent="create">
        <label>
          {{ $t('admin.invites.role') }}
          <select v-model="form.role">
            <option v-for="(label, key) in roleOptions" :key="key" :value="key" :disabled="!auth.isAdmin && key !== 'student'">{{ label }}</option>
          </select>
        </label>
        <label>
          {{ $t('admin.invites.enrollTo') }} {{ auth.isAdmin ? $t('admin.invites.optional') : '' }}
          <select v-model="form.course_id" :required="!auth.isAdmin" @change="onCourse">
            <option :value="null">{{ $t('admin.invites.noCourse') }}</option>
            <option v-for="c in courses.data.value?.results ?? []" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>
        </label>
        <label v-if="groups.length">
          {{ $t('teach.groupsTab.group') }}
          <select v-model="form.group_id">
            <option :value="null">{{ $t('admin.invites.noGroup') }}</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </label>
        <div class="form-row">
          <label>{{ $t('admin.invites.uses') }} <input v-model.number="form.max_uses" type="number" min="1" max="500" /></label>
          <label>{{ $t('admin.invites.days') }} <input v-model.number="form.expires_in_days" type="number" min="1" max="90" /></label>
        </div>
        <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('ui.create') }}</button>
      </form>

      <div v-if="created?.invite_token" class="alert alert--success" style="margin-top: 16px; display: grid">
        <strong>{{ $t('admin.invites.linkOnce') }}</strong>
        <pre class="code">{{ inviteLink(created.invite_token) }}</pre>
        <button class="btn btn--sm" style="justify-self: start" @click="copy(inviteLink(created.invite_token))">{{ $t('admin.invites.copy') }}</button>
      </div>
    </section>

    <section v-if="auth.isAdmin" class="card">
      <h2>{{ $t('admin.invites.all') }}</h2>
      <StateBlock :loading="invites.loading.value" :error="invites.error.value" :empty="!invites.data.value?.results.length" @retry="invites.run">
        <ul class="list-plain">
          <li v-for="i in invites.data.value?.results ?? []" :key="i.id" class="row row--between">
            <span>
              {{ roleLabel(i.role) }} <span class="muted small">{{ i.used_count }}/{{ i.max_uses }} · {{ $t('ui.until', { date: fmtDateTime(i.expires_at) }) }}</span>
            </span>
            <span class="row">
              <AppBadge :kind="i.is_valid ? 'success' : 'default'">{{ i.is_valid ? $t('admin.invites.valid') : $t('admin.invites.inactive') }}</AppBadge>
              <button v-if="i.is_valid" class="btn btn--ghost btn--sm" @click="revoke(i.id)">{{ $t('admin.invites.revoke') }}</button>
            </span>
          </li>
        </ul>
      </StateBlock>
    </section>
  </div>
</template>
