<script setup lang="ts">
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'

import { coursesApi, groupsApi } from '@/api/courses'
import { progressApi } from '@/api/progress'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { enrollmentStatusLabels } from '@/utils/format'

const props = defineProps<{ courseId: number }>()

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()
const table = useAsync(() => progressApi.courseStudents(props.courseId))
const groups = useAsync(() => groupsApi.list(props.courseId))
const form = reactive({ student_email: '', access_days: 365, group_id: null as number | null })

async function enroll() {
  if (await act(() => coursesApi.enrollStudent(props.courseId, form), t('teach.studentsTab.enrolled'))) {
    form.student_email = ''
    table.run()
  }
}
</script>

<template>
  <div class="stack">
    <section v-if="auth.isStaff" class="card">
      <h2>{{ $t('teach.studentsTab.enroll') }}</h2>
      <form class="row" @submit.prevent="enroll">
        <input v-model="form.student_email" type="email" :placeholder="$t('teach.studentsTab.email')" style="max-width: 260px" required />
        <select v-model="form.group_id" style="max-width: 200px">
          <option :value="null">{{ $t('teach.studentsTab.noGroup') }}</option>
          <option v-for="g in groups.data.value ?? []" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
        <input v-model.number="form.access_days" type="number" min="1" style="max-width: 110px" :title="$t('teach.studentsTab.accessDays')" />
        <button class="btn" :disabled="busy">{{ $t('teach.studentsTab.enrollBtn') }}</button>
      </form>
      <p class="muted small">{{ $t('teach.studentsTab.hint') }}</p>
    </section>

    <section class="card">
      <h2>{{ $t('teach.studentsTab.progress') }}</h2>
      <StateBlock :loading="table.loading.value" :error="table.error.value" :empty="!table.data.value?.length"
                  :empty-text="$t('teach.studentsTab.empty')" @retry="table.run">
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>{{ $t('roles.student') }}</th><th>{{ $t('teach.groupsTab.group') }}</th><th>{{ $t('teach.studentsTab.colEnrollment') }}</th><th style="width: 180px">{{ $t('teach.studentsTab.colDone') }}</th><th>{{ $t('teach.studentsTab.colAvg') }}</th><th></th></tr></thead>
            <tbody>
              <tr v-for="r in table.data.value ?? []" :key="r.student_id">
                <td>{{ r.student_name }}<div class="muted small">{{ r.student_email }}</div></td>
                <td>{{ r.group ?? '—' }}</td>
                <td>{{ enrollmentStatusLabels[r.enrollment_status] }}</td>
                <td><ProgressBar :value="r.percent_completed" /> <span class="small">{{ r.percent_completed }}%</span></td>
                <td>{{ r.average_test_score }}%</td>
                <td><RouterLink :to="{ path: `/progress/courses/${courseId}`, query: { student: r.student_id } }" class="btn btn--ghost btn--sm">{{ $t('teach.studentsTab.report') }}</RouterLink></td>
              </tr>
            </tbody>
          </table>
        </div>
      </StateBlock>
    </section>
  </div>
</template>
