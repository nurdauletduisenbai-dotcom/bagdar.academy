<script setup lang="ts">
import { computed } from 'vue'

import { submissionsApi } from '@/api/assignments'
import { orgsApi } from '@/api/orgs'
import { progressApi } from '@/api/progress'
import AppIcon from '@/components/ui/AppIcon.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types/api'
import { courseStatusLabels, fmtMoney, roleLabel } from '@/utils/format'

const auth = useAuthStore()
const summary = useAsync(() => progressApi.orgSummary())
const invites = useAsync(() => orgsApi.invites())
const toReview = useAsync(() => submissionsApi.list({ status: 'submitted' }))

const expiringInvites = computed(() =>
  (invites.data.value?.results ?? []).filter((i) => i.is_valid && new Date(i.expires_at).getTime() - Date.now() < 3 * 86400_000).length,
)
const roles = computed(() => Object.entries(summary.data.value?.members_by_role ?? {}) as [Role, number][])
const maxRole = computed(() => Math.max(1, ...roles.value.map(([, n]) => n)))
</script>

<template>
  <StateBlock :loading="summary.loading.value" :error="summary.error.value" @retry="summary.run">
    <template v-if="summary.data.value">
      <section class="band page-band stats">
        <div class="eyebrow">{{ $t('home.orgToday', { org: auth.currentOrg?.name ?? '' }) }}</div>
        <div class="stats__grid">
          <div><div class="stat">{{ summary.data.value.members_by_role.student ?? 0 }}</div><span class="muted small">{{ $t('home.kStudents') }}</span></div>
          <div><div class="stat">{{ summary.data.value.active_enrollments }}</div><span class="muted small">{{ $t('home.kEnrollments') }}</span></div>
          <div><div class="stat stat--accent">{{ summary.data.value.orders_pending }}</div><span class="muted small">{{ $t('home.kOrdersPending') }}</span></div>
          <div><div class="stat">{{ fmtMoney(summary.data.value.revenue_30d) }}</div><span class="muted small">{{ $t('home.k30d') }}</span></div>
        </div>
      </section>

      <div class="grid--2" style="align-items: start">
        <section class="card">
          <h2>{{ $t('admin.dashboard.actions') }}</h2>
          <ul class="list-lines">
            <li><RouterLink to="/admin/orders" class="action"><span>{{ $t('admin.dashboard.ordersToConfirm', { n: summary.data.value.orders_pending }) }}</span><AppIcon name="arrow-right" :size="16" /></RouterLink></li>
            <li><RouterLink to="/admin/invites" class="action"><span>{{ $t('admin.dashboard.invitesExpiring', { n: expiringInvites }) }}</span><AppIcon name="arrow-right" :size="16" /></RouterLink></li>
            <li><RouterLink to="/teach/submissions" class="action"><span>{{ $t('admin.dashboard.unreviewed', { n: toReview.data.value?.total ?? 0 }) }}</span><AppIcon name="arrow-right" :size="16" /></RouterLink></li>
          </ul>
        </section>

        <section class="card">
          <h2>{{ $t('admin.dashboard.byRole') }}</h2>
          <div class="bars">
            <div v-for="([role, n], i) in roles" :key="role" class="bar">
              <span class="small">{{ n }}</span>
              <div class="bar__fill" :class="{ dark: i === roles.length - 1 }" :style="{ height: `${(n / maxRole) * 100}%` }" />
              <span class="small muted">{{ roleLabel(role) }}</span>
            </div>
          </div>
        </section>

        <section class="card">
          <h2>{{ $t('nav.courses') }}</h2>
          <ul class="list-lines">
            <li v-for="(n, status) in summary.data.value.courses_by_status" :key="status" class="row row--between">
              <span>{{ courseStatusLabels[status] ?? status }}</span><strong>{{ n }}</strong>
            </li>
          </ul>
          <RouterLink to="/teach/courses" class="small">{{ $t('admin.dashboard.allCourses') }}</RouterLink>
        </section>

        <section class="card">
          <h2>{{ $t('admin.dashboard.learning') }}</h2>
          <div class="row" style="gap: var(--space-xxl)">
            <div><div class="stat">{{ summary.data.value.average_progress_pct }}%</div><span class="muted small">{{ $t('home.avgProgress') }}</span></div>
            <div><div class="stat">{{ fmtMoney(summary.data.value.revenue_total) }}</div><span class="muted small">{{ $t('admin.dashboard.revenueTotal') }}</span></div>
          </div>
        </section>
      </div>
    </template>
  </StateBlock>
</template>

<style scoped>
.stats {
  display: grid;
  gap: var(--space-lg);
}
.stats__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-lg);
}
.action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-strong);
}
.bars {
  display: flex;
  gap: var(--space-md);
  align-items: flex-end;
  height: 160px;
}
.bar {
  flex: 1;
  height: 100%;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 4px;
  text-align: center;
}
.bar__fill {
  align-self: end;
  background: var(--hairline);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  min-height: 4px;
}
.bar__fill.dark {
  background: var(--teal-900);
}
</style>
