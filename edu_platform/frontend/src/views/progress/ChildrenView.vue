<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { parentsApi } from '@/api/auth'
import { progressApi } from '@/api/progress'
import ProgressSummary from '@/components/progress/ProgressSummary.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import type { CourseReport, ParentRelation } from '@/types/api'
import { fmtDateTime } from '@/utils/format'

const { t } = useI18n()

const { act, busy } = useAction()
const children = useAsync(() => parentsApi.children())
const selectedId = ref<number | null>(null)
const linking = ref(false)
const email = ref('')

const selected = computed<ParentRelation | null>(() =>
  (children.data.value ?? []).find((r) => r.id === selectedId.value) ?? (children.data.value ?? [])[0] ?? null,
)

const reports = useAsync<CourseReport[]>(async () => {
  const rel = selected.value
  if (!rel?.is_confirmed) return []
  const data = await progressApi.student(rel.student.id)
  return Promise.all(data.courses.map((c) => progressApi.course(c.course_id, rel.student.id)))
}, { immediate: false })
watch(selected, () => reports.run())

/** «За неделю»: несданные ДЗ с близким/прошедшим дедлайном */
const warnings = computed(() =>
  (reports.data.value ?? []).flatMap((r) =>
    r.assignments
      .filter((a) => a.status === 'pending' && new Date(a.deadline).getTime() - Date.now() < 2 * 86400_000)
      .map((a) => ({ ...a, course: r.course_title })),
  ),
)
const overdue = computed(() => (reports.data.value ?? []).flatMap((r) => r.assignments.filter((a) => a.status === 'overdue')).length)
const missed = computed(() => (reports.data.value ?? []).reduce((n, r) => n + (r.attendance.absent ?? 0), 0))

async function link() {
  if (await act(() => parentsApi.requestLink(email.value), t('children.requested'))) {
    email.value = ''
    linking.value = false
    children.run()
  }
}

async function unlink(id: number) {
  if (confirm(t('children.confirmUnlink')) && (await act(() => parentsApi.unlink(id), t('children.unlinked')))) children.run()
}
</script>

<template>
  <PageHeader :title="$t('nav.children')">
    <button class="btn btn--ghost" @click="linking = !linking">{{ $t('children.link') }}</button>
  </PageHeader>

  <form v-if="linking" class="card row" style="margin-bottom: var(--space-lg)" @submit.prevent="link">
    <input v-model="email" type="email" :placeholder="$t('children.emailPh')" style="max-width: 320px" required />
    <button class="btn" :disabled="busy">{{ $t('children.sendRequest') }}</button>
    <span class="muted small">{{ $t('children.confirmHint') }}</span>
  </form>

  <StateBlock :loading="children.loading.value" :error="children.error.value" :empty="!children.data.value?.length"
              :empty-text="$t('children.empty')" @retry="children.run">
    <div class="pills" style="margin-bottom: var(--space-lg)">
      <button v-for="r in children.data.value ?? []" :key="r.id" class="pill" :class="{ active: selected?.id === r.id }" @click="selectedId = r.id">
        {{ r.student.full_name }}<template v-if="!r.is_confirmed">{{ $t('children.awaitConfirm') }}</template>
      </button>
    </div>

    <template v-if="selected">
      <div v-if="!selected.is_confirmed" class="alert alert--warning">
        {{ $t('children.notConfirmed', { name: selected.student.full_name }) }}
        <button class="btn btn--ghost btn--sm" @click="unlink(selected.id)">{{ $t('children.revoke') }}</button>
      </div>
      <StateBlock v-else :loading="reports.loading.value" :error="reports.error.value" @retry="reports.run">
        <section class="card week">
          <div class="eyebrow">{{ $t('children.now') }}</div>
          <p class="week__line">
            {{ $t('children.lessonsDone', { n: (reports.data.value ?? []).reduce((n, r) => n + r.lessons_completed_count, 0) }) }} ·
            {{ $t('children.testsDone', { n: (reports.data.value ?? []).reduce((n, r) => n + r.tests.filter((t) => t.best_score_pct !== null).length, 0) }) }} ·
            {{ $t('children.missed', { n: missed }) }}<template v-if="overdue"> · {{ $t('children.overdue', { n: overdue }) }}</template>
          </p>
          <div v-for="w in warnings" :key="w.id" class="alert alert--warning">
            {{ $t('children.hwMissing', { title: w.title, course: w.course, date: fmtDateTime(w.deadline) }) }}
          </div>
        </section>
        <ProgressSummary :reports="reports.data.value ?? []" :student-id="selected.student.id" />
        <button class="btn btn--text btn--sm" style="margin-top: var(--space-md)" @click="unlink(selected.id)">{{ $t('children.unlink') }}</button>
      </StateBlock>
    </template>
  </StateBlock>
</template>

<style scoped>
.week {
  display: grid;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}
.week__line {
  margin: 0;
  font-weight: 500;
}
</style>
