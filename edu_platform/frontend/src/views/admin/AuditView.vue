<script setup lang="ts">
import { reactive } from 'vue'

import { orgsApi } from '@/api/orgs'
import AppPager from '@/components/ui/AppPager.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAsync } from '@/composables/useAsync'
import { auditActionLabels, fmtDateTime } from '@/utils/format'

const actions = auditActionLabels
const filters = reactive({ action: '', page: 1 })
const logs = useAsync(() => orgsApi.auditLogs({ action: filters.action || undefined, page: filters.page }))
</script>

<template>
  <PageHeader :title="$t('admin.audit.title')" :subtitle="$t('admin.audit.subtitle')" />
  <select v-model="filters.action" style="max-width: 260px; margin-bottom: var(--space-lg)" @change="filters.page = 1; logs.run()">
    <option value="">{{ $t('admin.audit.allActions') }}</option>
    <option v-for="(label, key) in actions" :key="key" :value="key">{{ label }}</option>
  </select>
  <StateBlock :loading="logs.loading.value" :error="logs.error.value" :empty="!logs.data.value?.results.length" @retry="logs.run">
    <div class="card card--flush table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('admin.audit.colTime') }}</th><th>{{ $t('admin.audit.colAction') }}</th><th>{{ $t('admin.audit.colWho') }}</th><th>IP</th><th>{{ $t('admin.audit.colObject') }}</th><th>{{ $t('admin.audit.colDetails') }}</th></tr></thead>
        <tbody>
          <tr v-for="l in logs.data.value?.results ?? []" :key="l.id">
            <td class="small nowrap">{{ fmtDateTime(l.created_at) }}</td>
            <td><span class="badge">{{ actions[l.action] ?? l.action }}</span></td>
            <td>{{ l.user_email ?? '—' }}</td>
            <td class="small">{{ l.ip_address ?? '—' }}</td>
            <td class="small">{{ l.entity_type }} {{ l.entity_id ?? '' }}</td>
            <td><pre v-if="Object.keys(l.changes).length" class="code">{{ JSON.stringify(l.changes) }}</pre></td>
          </tr>
        </tbody>
      </table>
    </div>
    <AppPager :page="filters.page" :total-pages="logs.data.value?.total_pages ?? 1" @change="(p) => { filters.page = p; logs.run() }" />
  </StateBlock>
</template>

<style scoped>
.nowrap {
  white-space: nowrap;
}
</style>
