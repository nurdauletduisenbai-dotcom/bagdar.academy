<script setup lang="ts">
import { useRoute } from 'vue-router'

import { progressApi } from '@/api/progress'
import AppIcon from '@/components/ui/AppIcon.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAsync } from '@/composables/useAsync'
import { attendanceLabels, fmtDateTime, submissionStatusLabels } from '@/utils/format'

const props = defineProps<{ courseId: string }>()
const route = useRoute()
const student = route.query.student ? Number(route.query.student) : undefined
const report = useAsync(() => progressApi.course(Number(props.courseId), student))
const kind = (s: string) => (s === 'graded' ? 'badge--success' : s === 'overdue' ? 'badge--danger' : s === 'submitted' ? 'badge--warning' : '')
</script>

<template>
  <StateBlock :loading="report.loading.value" :error="report.error.value" @retry="report.run">
    <template v-if="report.data.value">
      <section class="band page-band head">
        <ProgressRing :value="report.data.value.percent_completed" :size="104" dark />
        <div class="head__body">
          <RouterLink :to="`/courses/${courseId}`" class="back small"><AppIcon name="arrow-left" :size="14" /> {{ $t('ui.toCourse') }}</RouterLink>
          <div class="eyebrow">{{ $t('report.eyebrow') }}</div>
          <h1>{{ report.data.value.course_title }}</h1>
          <p class="muted">
            {{ $t('report.lessons', { done: report.data.value.lessons_completed_count, total: report.data.value.total_lessons_count }) }} ·
            {{ $t('report.avg', { avg: report.data.value.average_test_score }) }}
          </p>
        </div>
      </section>

      <div class="grid--2" style="align-items: start">
        <section class="card">
          <h2>{{ $t('report.lessonsH') }}</h2>
          <ul class="list-lines">
            <li v-for="l in report.data.value.lessons" :key="l.id" class="row row--between">
              <span class="row"><AppIcon :name="l.is_completed ? 'check' : 'circle'" :size="14" :class="{ ok: l.is_completed }" /> {{ l.title }}</span>
              <span class="muted small">{{ l.section }}</span>
            </li>
          </ul>
        </section>
        <div class="stack">
          <section class="card">
            <h2>{{ $t('report.testsH') }}</h2>
            <p v-if="!report.data.value.tests.length" class="muted small">{{ $t('lessonView.noTests') }}</p>
            <ul class="list-lines">
              <li v-for="t in report.data.value.tests" :key="t.id" class="row row--between">
                <span>{{ t.title }} <span class="muted small">· {{ $t('courseView.attempts', { n: t.attempts }) }}</span></span>
                <span class="badge" :class="t.passed ? 'badge--success' : t.best_score_pct === null ? '' : 'badge--danger'">
                  {{ t.best_score_pct === null ? $t('report.notPassed') : `${t.best_score_pct}%` }}
                </span>
              </li>
            </ul>
          </section>
          <section class="card">
            <h2>{{ $t('report.assignmentsH') }}</h2>
            <p v-if="!report.data.value.assignments.length" class="muted small">{{ $t('report.noAssignments') }}</p>
            <ul class="list-lines">
              <li v-for="a in report.data.value.assignments" :key="a.id" class="row row--between">
                <span>{{ a.title }} <span class="muted small">· {{ $t('ui.until', { date: fmtDateTime(a.deadline) }) }}</span></span>
                <span class="row">
                  <strong v-if="a.score !== null" class="small">{{ a.score }}/{{ a.max_score }}</strong>
                  <span class="badge" :class="kind(a.status)">{{ submissionStatusLabels[a.status] }}</span>
                </span>
              </li>
            </ul>
          </section>
          <section class="card">
            <h2>{{ $t('report.attendanceH') }}</h2>
            <div class="pills">
              <span v-for="(n, status) in report.data.value.attendance" :key="status" class="pill">{{ attendanceLabels[status] }}: {{ n }}</span>
            </div>
            <p v-if="!Object.keys(report.data.value.attendance).length" class="muted small">{{ $t('report.noMarks') }}</p>
          </section>
        </div>
      </div>
    </template>
  </StateBlock>
</template>

<style scoped>
.head {
  display: flex;
  gap: var(--space-xl);
  align-items: center;
  flex-wrap: wrap;
}
.head__body {
  display: grid;
  gap: 4px;
}
.head__body p {
  margin: 0;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-on-dark-muted);
}
.ok {
  color: var(--green-600);
}
.pill {
  cursor: default;
}
</style>
