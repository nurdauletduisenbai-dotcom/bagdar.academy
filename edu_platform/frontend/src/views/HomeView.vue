<script setup lang="ts">
import { computed } from 'vue'

import { parentsApi } from '@/api/auth'
import { assignmentsApi, submissionsApi } from '@/api/assignments'
import { coursesApi } from '@/api/courses'
import { announcementsApi } from '@/api/notifications'
import { progressApi } from '@/api/progress'
import { sessionsApi } from '@/api/schedule'
import AppIcon from '@/components/ui/AppIcon.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { fmtDateTime, fmtMoney, fmtTime, fmtWeekday } from '@/utils/format'

const auth = useAuthStore()
const now = new Date()
const endOfDay = new Date(now)
endOfDay.setHours(23, 59, 59, 999)
const inWeek = new Date(now.getTime() + 7 * 86400_000)
const firstName = computed(() => auth.user?.full_name?.split(' ')[0] ?? '')

const sessions = useAsync(() => sessionsApi.list({ date_from: now.toISOString(), date_to: inWeek.toISOString() }))
const announcements = useAsync(() => announcementsApi.list())
const today = computed(() =>
  (sessions.data.value?.results ?? []).filter((s) => !s.is_canceled && new Date(s.start_time) <= endOfDay),
)

// ---------- Ученик ----------
const progress = useAsync(() => (auth.isStudent ? progressApi.my() : Promise.resolve([])))
const assignments = useAsync(() => (auth.isStudent ? assignmentsApi.list() : Promise.resolve(null)))
const activeCourses = computed(() => (progress.data.value ?? []).filter((c) => c.enrollment_status === 'active'))
const pending = computed(() =>
  (assignments.data.value?.results ?? []).filter((a) => !a.my_submission && !a.is_overdue),
)
const avgProgress = computed(() => {
  const list = activeCourses.value
  return list.length ? Math.round(list.reduce((s, c) => s + c.percent_completed, 0) / list.length) : 0
})
/** «Продолжить»: первый непройденный урок курса, где прогресс меньше 100% */
const continueCourse = computed(() => activeCourses.value.find((c) => c.percent_completed < 100) ?? activeCourses.value[0])
const report = useAsync(async () => {
  await progress.run()
  const c = continueCourse.value
  return c ? progressApi.course(c.course_id) : null
})
const nextLesson = computed(() => report.data.value?.lessons.find((l) => !l.is_completed) ?? null)

// ---------- Учитель / админ / родитель ----------
const toReview = useAsync(() => (auth.isTeacher ? submissionsApi.list({ status: 'submitted' }) : Promise.resolve(null)))
const teachCourses = useAsync(() => (auth.isStaff ? coursesApi.list() : Promise.resolve(null)))
const summary = useAsync(() => (auth.isAdmin ? progressApi.orgSummary() : Promise.resolve(null)))
const children = useAsync(() => (auth.isParent ? parentsApi.children() : Promise.resolve([])))
</script>

<template>
  <h1 class="greeting">{{ $t('home.hello', { name: firstName }) }}</h1>

  <!-- ================= Ученик (вайрфрейм 1a) ================= -->
  <template v-if="auth.isStudent">
    <section class="band hero">
      <div class="hero__media">
        <AppIcon name="play" :size="28" />
      </div>
      <div class="hero__body">
        <template v-if="continueCourse">
          <div class="eyebrow">{{ $t('home.continue', { course: continueCourse.course_title }) }}</div>
          <h2 class="hero__title">{{ nextLesson?.title ?? `${$t('courseView.allDone')} 🎉` }}</h2>
          <ProgressBar :value="continueCourse.percent_completed" dark />
          <div class="row">
            <RouterLink v-if="nextLesson" :to="`/lessons/${nextLesson.id}`" class="btn">{{ $t('home.watchNext') }}</RouterLink>
            <RouterLink :to="`/courses/${continueCourse.course_id}`" class="btn btn--ghost">{{ $t('lessonView.toCourse') }}</RouterLink>
            <span class="muted small">{{ $t('home.donePct', { pct: continueCourse.percent_completed }) }}</span>
          </div>
        </template>
        <template v-else>
          <div class="eyebrow">{{ $t('home.startLearning') }}</div>
          <h2 class="hero__title">{{ $t('home.noCourses') }}</h2>
          <div><RouterLink to="/catalog" class="btn">{{ $t('home.openCatalog') }}</RouterLink></div>
        </template>
      </div>
    </section>

    <div class="tiles">
      <RouterLink to="/assignments" class="card card--link tile">
        <span class="muted small">{{ $t('home.toSubmit') }}</span>
        <span class="stat">{{ pending.length }}</span>
        <span class="small muted">{{ pending[0] ? $t('home.nearest', { title: pending[0].title }) : $t('home.allSubmitted') }}</span>
      </RouterLink>
      <RouterLink to="/schedule" class="card card--link tile">
        <span class="muted small">{{ $t('ui.today') }}</span>
        <span class="stat">{{ today[0] ? fmtTime(today[0].start_time) : '—' }}</span>
        <span class="small muted">{{ today[0] ? today[0].title : $t('home.noSessions') }}</span>
      </RouterLink>
      <RouterLink to="/my-courses" class="card card--link tile">
        <span class="muted small">{{ $t('nav.myCourses') }}</span>
        <span class="stat">{{ activeCourses.length }} <span class="tile__unit">· {{ avgProgress }}%</span></span>
        <span class="small muted">{{ $t('home.avgProgress') }}</span>
      </RouterLink>
    </div>
  </template>

  <!-- ================= Админ (вайрфрейм 2r) ================= -->
  <section v-if="auth.isAdmin" class="band band-stats">
    <div class="eyebrow">{{ $t('home.orgToday', { org: auth.currentOrg?.name ?? '' }) }}</div>
    <StateBlock :loading="summary.loading.value" :error="summary.error.value" @retry="summary.run">
      <div v-if="summary.data.value" class="band-stats__grid">
        <div><div class="stat">{{ summary.data.value.members_by_role.student ?? 0 }}</div><span class="muted small">{{ $t('home.kStudents') }}</span></div>
        <div><div class="stat">{{ summary.data.value.active_enrollments }}</div><span class="muted small">{{ $t('home.kEnrollments') }}</span></div>
        <div><div class="stat stat--accent">{{ summary.data.value.orders_pending }}</div><span class="muted small">{{ $t('home.kOrdersPending') }}</span></div>
        <div><div class="stat">{{ fmtMoney(summary.data.value.revenue_30d) }}</div><span class="muted small">{{ $t('home.k30d') }}</span></div>
      </div>
    </StateBlock>
    <div class="row"><RouterLink to="/admin" class="btn btn--sm">{{ $t('home.schoolSummary') }}</RouterLink>
      <RouterLink v-if="summary.data.value?.orders_pending" to="/admin/orders" class="btn btn--sm btn--ghost">{{ $t('home.confirmPayments') }}</RouterLink></div>
  </section>

  <!-- ================= Учитель ================= -->
  <section v-if="auth.isTeacher && !auth.isAdmin" class="band band-stats">
    <div class="eyebrow">{{ $t('ui.today') }}</div>
    <div class="band-stats__grid">
      <div><div class="stat stat--accent">{{ toReview.data.value?.total ?? 0 }}</div><span class="muted small">{{ $t('home.kToReview') }}</span></div>
      <div><div class="stat">{{ today.length }}</div><span class="muted small">{{ $t('home.kSessionsToday') }}</span></div>
      <div><div class="stat">{{ teachCourses.data.value?.total ?? 0 }}</div><span class="muted small">{{ $t('home.kSchoolCourses') }}</span></div>
    </div>
    <div class="row">
      <RouterLink to="/teach/submissions" class="btn btn--sm">{{ $t('home.reviewWork') }}</RouterLink>
      <RouterLink to="/teach/courses" class="btn btn--sm btn--ghost">{{ $t('nav.myCourses') }}</RouterLink>
    </div>
  </section>

  <div class="grid--2 home-grid">
    <!-- Проверка работ -->
    <section v-if="auth.isTeacher" class="card">
      <div class="row row--between"><h2>{{ $t('home.awaitReview') }}</h2><RouterLink to="/teach/submissions" class="small">{{ $t('ui.allArrow') }}</RouterLink></div>
      <StateBlock :loading="toReview.loading.value" :error="toReview.error.value"
                  :empty="!toReview.data.value?.results.length" :empty-text="$t('home.allReviewed')" @retry="toReview.run">
        <ul class="list-lines">
          <li v-for="s in toReview.data.value?.results.slice(0, 5) ?? []" :key="s.id" class="row row--between">
            <span>{{ s.student_name }} · <span class="muted">{{ s.assignment_title }}</span></span>
            <span class="muted small">{{ fmtDateTime(s.submitted_at) }}</span>
          </li>
        </ul>
      </StateBlock>
    </section>

    <!-- Родитель -->
    <section v-if="auth.isParent" class="card">
      <div class="row row--between"><h2>{{ $t('nav.children') }}</h2><RouterLink to="/children" class="small">{{ $t('home.grades') }}</RouterLink></div>
      <StateBlock :loading="children.loading.value" :error="children.error.value" :empty="!children.data.value?.length"
                  :empty-text="$t('home.linkChild')" @retry="children.run">
        <ul class="list-lines">
          <li v-for="r in children.data.value ?? []" :key="r.id" class="row row--between">
            <strong>{{ r.student.full_name }}</strong>
            <span v-if="r.is_confirmed" class="badge badge--success">{{ $t('home.accessOpen') }}</span>
            <span v-else class="badge badge--warning">{{ $t('home.awaitConfirm') }}</span>
          </li>
        </ul>
      </StateBlock>
    </section>

    <!-- Курсы ученика -->
    <section v-if="auth.isStudent && activeCourses.length" class="card">
      <div class="row row--between"><h2>{{ $t('nav.myCourses') }}</h2><RouterLink to="/catalog" class="small">{{ $t('home.plusCatalog') }}</RouterLink></div>
      <ul class="list-lines">
        <li v-for="c in activeCourses" :key="c.course_id" class="course-line">
          <RouterLink :to="`/courses/${c.course_id}`">{{ c.course_title }}</RouterLink>
          <ProgressBar :value="c.percent_completed" />
          <span class="small muted">{{ c.percent_completed }}%</span>
        </li>
      </ul>
    </section>

    <section class="card">
      <div class="row row--between"><h2>{{ $t('home.upcoming') }}</h2><RouterLink to="/schedule" class="small">{{ $t('home.scheduleLink') }}</RouterLink></div>
      <StateBlock :loading="sessions.loading.value" :error="sessions.error.value" :empty="!sessions.data.value?.results.length"
                  :empty-text="$t('home.noWeekSessions')" @retry="sessions.run">
        <ul class="list-lines">
          <li v-for="s in sessions.data.value?.results.slice(0, 5) ?? []" :key="s.id" class="session-line">
            <strong class="session-line__time">{{ fmtTime(s.start_time) }}</strong>
            <span>{{ s.title }} <span class="muted small">· {{ s.group_name }}</span></span>
            <span class="muted small">{{ fmtWeekday(s.start_time) }}, {{ new Date(s.start_time).getDate() }}</span>
          </li>
        </ul>
      </StateBlock>
    </section>

    <section class="card">
      <div class="row row--between"><h2>{{ $t('home.announcements') }}</h2><RouterLink to="/announcements" class="small">{{ $t('ui.allArrow') }}</RouterLink></div>
      <StateBlock :loading="announcements.loading.value" :error="announcements.error.value"
                  :empty="!announcements.data.value?.results.length" :empty-text="$t('home.noAnnouncements')" @retry="announcements.run">
        <ul class="list-lines">
          <li v-for="a in announcements.data.value?.results.slice(0, 3) ?? []" :key="a.id">
            <strong>{{ a.title }}</strong>
            <div class="muted small">{{ a.author }} · {{ fmtDateTime(a.created_at) }}</div>
          </li>
        </ul>
      </StateBlock>
    </section>
  </div>
</template>

<style scoped>
.greeting {
  margin-bottom: var(--space-xl);
}
.hero {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: var(--space-xl);
  align-items: center;
}
.hero__media {
  aspect-ratio: 16 / 10;
  border-radius: var(--radius-md);
  border: 1px dashed rgba(255, 255, 255, 0.25);
  display: grid;
  place-items: center;
  color: var(--green-500);
  background: rgba(255, 255, 255, 0.04);
}
.hero__body {
  display: grid;
  gap: var(--space-sm);
}
.hero__title {
  font: 500 var(--fs-h3) / var(--lh-h3) var(--font-sans);
  margin: 0;
}
.tiles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-md);
  margin: var(--space-md) 0 var(--space-xl);
}
.tile {
  display: grid;
  gap: 4px;
}
.tile__unit {
  font-size: var(--fs-h5);
  color: var(--text-tertiary);
}
.band-stats {
  display: grid;
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}
.band-stats__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-lg);
}
.home-grid {
  align-items: start;
}
.course-line {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) 44px;
  gap: var(--space-sm);
  align-items: center;
}
.session-line {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: var(--space-sm);
  align-items: center;
}
.session-line__time {
  font-weight: 600;
}
@media (max-width: 760px) {
  .hero {
    grid-template-columns: 1fr;
  }
  .hero__media {
    display: none;
  }
  .tiles {
    grid-template-columns: 1fr;
  }
}
</style>
