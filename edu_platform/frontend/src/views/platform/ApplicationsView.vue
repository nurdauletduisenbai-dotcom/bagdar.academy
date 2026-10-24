<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import { applicationsApi } from '@/api/schools'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppPager from '@/components/ui/AppPager.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAsync } from '@/composables/useAsync'
import type { ApplicationStatus } from '@/types/api'
import { fmtDateTime } from '@/utils/format'

/** Заявки школ (только суперпользователь): новые и требующие уточнения — сверху */
const router = useRouter()
const filters = reactive({ status: 'new' as ApplicationStatus | '', search: '', page: 1 })
const list = useAsync(() => applicationsApi.list({
  status: filters.status || undefined, search: filters.search || undefined, page: filters.page,
}))
const summary = useAsync(() => applicationsApi.summary())
const statuses: ApplicationStatus[] = ['new', 'needs_info', 'approved', 'rejected']
const badge: Record<ApplicationStatus, string> = {
  new: 'badge--info', needs_info: 'badge--warning', approved: 'badge--success', rejected: 'badge--danger',
}

function setStatus(s: ApplicationStatus | '') {
  filters.status = s
  filters.page = 1
  list.run()
}

function search() {
  filters.page = 1
  list.run()
}
</script>

<template>
  <PageHeader :title="$t('platformApps.title')" :subtitle="$t('platformApps.subtitle')" />

  <div class="row row--between toolbar">
    <div class="pills">
      <button v-for="s in statuses" :key="s" class="pill" :class="{ active: filters.status === s }" @click="setStatus(s)">
        {{ $t(`platformApps.status.${s}`) }}
        <span v-if="summary.data.value" class="count">{{ summary.data.value[s] }}</span>
      </button>
      <button class="pill" :class="{ active: !filters.status }" @click="setStatus('')">{{ $t('platformApps.all') }}</button>
    </div>
    <form class="search" @submit.prevent="search">
      <AppIcon name="search" />
      <input v-model="filters.search" type="search" :placeholder="$t('platformApps.search')" :aria-label="$t('platformApps.search')" />
    </form>
  </div>

  <StateBlock :loading="list.loading.value" :error="list.error.value" :empty="!list.data.value?.results.length"
              :empty-text="$t('platformApps.empty')" @retry="list.run">
    <div class="card card--flush table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>{{ $t('platformApps.colSchool') }}</th>
            <th>{{ $t('platformApps.colApplicant') }}</th>
            <th>{{ $t('platformApps.colStatus') }}</th>
            <th>{{ $t('platformApps.colDate') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in list.data.value?.results ?? []" :key="a.id" class="row-link"
              @click="router.push({ name: 'platform-application', params: { id: a.id } })">
            <td>
              <RouterLink :to="{ name: 'platform-application', params: { id: a.id } }" @click.stop>
                <strong>{{ a.school.name }}</strong>
              </RouterLink>
              <div class="muted small">
                {{ $t(`schoolApply.types.${a.org_type}`) }} · {{ a.school.locality || a.school.region_name_ru }}
              </div>
              <div class="row tags">
                <span v-if="a.is_claim || a.school.admins.length" class="badge badge--warning">{{ $t('platformApps.claim') }}</span>
                <span v-if="!a.school.is_approved" class="badge">{{ $t('platformApps.notListed') }}</span>
              </div>
            </td>
            <td>
              {{ a.contact_name }}<span v-if="a.position" class="muted small"> · {{ a.position }}</span>
              <div class="muted small">{{ a.email }} · {{ a.phone }}</div>
            </td>
            <td><span class="badge" :class="badge[a.status]">{{ $t(`platformApps.status.${a.status}`) }}</span></td>
            <td class="small">{{ fmtDateTime(a.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <AppPager :page="filters.page" :total-pages="list.data.value?.total_pages ?? 1"
              @change="(p) => { filters.page = p; list.run() }" />
  </StateBlock>
</template>

<style scoped>
.toolbar {
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
  gap: var(--space-sm);
}
.toolbar .search {
  width: 300px;
  max-width: 100%;
}
.row-link {
  cursor: pointer;
}
.row-link:hover td {
  background: var(--surface-subtle);
}
.tags {
  gap: 4px;
  margin-top: 4px;
}
</style>
