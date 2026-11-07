<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { groupsApi } from '@/api/courses'
import { sessionsApi } from '@/api/schedule'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppModal from '@/components/ui/AppModal.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { AttendanceStatus, ClassSession, GroupStudent } from '@/types/api'
import { attendanceLabels, fmtDayMonth, fmtTime, fmtWeekday } from '@/utils/format'

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()

const weekStart = ref(startOfWeek(new Date()))
function startOfWeek(d: Date) {
  const r = new Date(d)
  r.setHours(0, 0, 0, 0)
  r.setDate(r.getDate() - ((r.getDay() + 6) % 7))
  return r
}
const weekEnd = computed(() => new Date(weekStart.value.getTime() + 7 * 86400_000))
const sessions = useAsync(() => sessionsApi.list({
  date_from: weekStart.value.toISOString(), date_to: weekEnd.value.toISOString(),
}))
const todayStr = new Date().toDateString()

const days = computed(() => Array.from({ length: 7 }, (_, i) => {
  const date = new Date(weekStart.value.getTime() + i * 86400_000)
  const label = `${fmtWeekday(date)}, ${fmtDayMonth(date)}`
  return {
    date,
    label: date.toDateString() === todayStr ? `${t('ui.today')} · ${label}` : label,
    isToday: date.toDateString() === todayStr,
    items: (sessions.data.value?.results ?? []).filter((s) => new Date(s.start_time).toDateString() === date.toDateString()),
  }
}).filter((d) => d.items.length || d.isToday))

const range = computed(() => {
  return `${fmtDayMonth(weekStart.value)} — ${fmtDayMonth(new Date(weekEnd.value.getTime() - 1))}`
})
const minutes = (s: ClassSession) => Math.round((new Date(s.end_time).getTime() - new Date(s.start_time).getTime()) / 60000)
const isNow = (s: ClassSession) => new Date(s.start_time) <= new Date() && new Date() <= new Date(s.end_time)

function shift(weeks: number) {
  weekStart.value = new Date(weekStart.value.getTime() + weeks * 7 * 86400_000)
  sessions.run()
}

async function toggleCancel(s: ClassSession) {
  if (!s.is_canceled && !confirm(t('schedule.confirmCancel'))) return
  if (await act(() => sessionsApi.update(s.id, { is_canceled: !s.is_canceled }), s.is_canceled ? t('schedule.restored') : t('schedule.canceled'))) {
    sessions.run()
  }
}

// ---------- Посещаемость (вид учителя) ----------
const marking = ref<{ session: ClassSession; students: GroupStudent[] } | null>(null)
const marks = reactive<Record<number, AttendanceStatus>>({})
const ORDER: AttendanceStatus[] = ['present', 'late', 'absent', 'excused']
const markClass: Record<AttendanceStatus, string> = { present: 'm-ok', late: 'm-late', absent: 'm-no', excused: 'm-exc' }

async function openAttendance(s: ClassSession) {
  const [students, existing] = await Promise.all([groupsApi.students(s.group), sessionsApi.attendance(s.id)])
  for (const st of students) marks[st.student_id] = existing.find((e) => e.student === st.student_id)?.status ?? 'present'
  marking.value = { session: s, students }
}

function cycle(studentId: number) {
  marks[studentId] = ORDER[(ORDER.indexOf(marks[studentId]) + 1) % ORDER.length]
}

async function saveAttendance() {
  if (!marking.value) return
  const records = marking.value.students.map((s) => ({ student_id: s.student_id, status: marks[s.student_id] }))
  if (await act(() => sessionsApi.markAttendance(marking.value!.session.id, records), t('schedule.attendanceSaved'))) marking.value = null
}
</script>

<template>
  <PageHeader :title="$t('nav.schedule')" :subtitle="range">
    <button class="icon-btn" :aria-label="$t('schedule.prevWeek')" @click="shift(-1)"><AppIcon name="chevron-left" /></button>
    <button class="btn btn--ghost btn--sm" @click="weekStart = startOfWeek(new Date()); sessions.run()">{{ $t('ui.today') }}</button>
    <button class="icon-btn" :aria-label="$t('schedule.nextWeek')" @click="shift(1)"><AppIcon name="chevron-right" /></button>
  </PageHeader>

  <p v-if="auth.isTeacher" class="muted small">{{ $t('schedule.teacherHint') }}</p>

  <StateBlock :loading="sessions.loading.value" :error="sessions.error.value" @retry="sessions.run">
    <div class="days">
      <section v-for="day in days" :key="day.label" class="day">
        <div class="eyebrow" :class="{ today: day.isToday }">{{ day.label }}</div>
        <p v-if="!day.items.length" class="muted small">{{ $t('schedule.noSessions') }}</p>
        <article v-for="s in day.items" :key="s.id" class="card session" :class="{ now: isNow(s), canceled: s.is_canceled }">
          <span class="session__time">{{ fmtTime(s.start_time) }}</span>
          <div class="session__body">
            <strong>{{ s.title }} · {{ s.group_name }}</strong>
            <span class="muted small">
              {{ s.location || (s.online_meeting_url ? $t('schedule.online') : '') }}<template v-if="s.location || s.online_meeting_url"> · </template>{{ $t('ui.minutes', { n: minutes(s) }) }}
              <template v-if="!s.is_canceled && new Date(s.start_time) > new Date()">{{ $t('schedule.remind') }}</template>
            </span>
          </div>
          <div class="row">
            <span v-if="s.is_canceled" class="badge badge--danger">{{ $t('schedule.canceledBadge') }}</span>
            <span v-else-if="isNow(s)" class="badge badge--green">{{ $t('schedule.now') }}</span>
            <a v-if="s.online_meeting_url && !s.is_canceled" :href="s.online_meeting_url" target="_blank" rel="noopener" class="btn btn--sm">{{ $t('schedule.join') }}</a>
            <template v-if="auth.isTeacher">
              <button class="btn btn--ghost btn--sm" @click="openAttendance(s)">{{ $t('schedule.attendance') }}</button>
              <button class="btn btn--text btn--sm" @click="toggleCancel(s)">{{ s.is_canceled ? $t('schedule.restore') : $t('schedule.cancel') }}</button>
            </template>
          </div>
        </article>
      </section>
      <p v-if="!sessions.data.value?.results.length" class="muted">{{ $t('schedule.noWeek') }}</p>
    </div>
  </StateBlock>

  <AppModal v-if="marking" :title="`${$t('schedule.attendance')} · ${marking.session.title}`" @close="marking = null">
    <p v-if="!marking.students.length" class="muted">{{ $t('schedule.noStudents') }}</p>
    <form v-else class="stack" @submit.prevent="saveAttendance">
      <p class="muted small">{{ $t('schedule.markHint') }}</p>
      <div class="pills">
        <button v-for="st in marking.students" :key="st.student_id" type="button" class="pill mark" :class="markClass[marks[st.student_id]]"
                @click="cycle(st.student_id)">
          {{ st.full_name }} · {{ attendanceLabels[marks[st.student_id]] }}
        </button>
      </div>
      <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('common.save') }}</button>
    </form>
  </AppModal>
</template>

<style scoped>
.days {
  display: grid;
  gap: var(--space-xl);
}
.day {
  display: grid;
  gap: var(--space-sm);
}
.day p {
  margin: 0;
}
.eyebrow.today {
  color: var(--green-dark);
}
.session {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) auto;
  gap: var(--space-lg);
  align-items: center;
  padding: var(--space-md) var(--space-xl);
}
.session.now {
  border: 2px solid var(--green-500);
  background: var(--surface-feature);
}
.session.canceled {
  opacity: 0.6;
}
.session__time {
  font: 500 var(--fs-h4) / 1 var(--font-sans);
  font-variant-numeric: tabular-nums;
}
.session__body {
  display: grid;
  gap: 2px;
}
.mark {
  color: var(--text-strong);
}
.m-ok { background: var(--green-soft); border-color: var(--green-soft); color: var(--green-dark); }
.m-late { background: var(--warning-bg); border-color: #f2d49b; color: var(--warning-text); }
.m-no { background: var(--error-bg); border-color: #f0b8b3; color: var(--error-text); }
.m-exc { background: var(--surface-soft); }
@media (max-width: 640px) {
  .session {
    grid-template-columns: 56px minmax(0, 1fr);
  }
  .session > .row {
    grid-column: 1 / -1;
  }
}
</style>
