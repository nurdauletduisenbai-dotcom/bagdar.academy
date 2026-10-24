<script setup lang="ts">
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'

import { assignmentsApi } from '@/api/assignments'
import { lessonsApi } from '@/api/content'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { fmtDateTime, fromLocalInput } from '@/utils/format'

const props = defineProps<{ courseId: number }>()

const { t } = useI18n()

const { act, busy } = useAction()
const assignments = useAsync(() => assignmentsApi.list({ course: props.courseId }))
const lessons = useAsync(() => lessonsApi.list({ course: props.courseId }))
const form = reactive({ lesson: 0, title: '', description: '', deadline: '', max_score: 10, accept_late: true })

async function create() {
  const ok = await act(() => assignmentsApi.create({ ...form, deadline: fromLocalInput(form.deadline)! }),
    t('teach.assignmentsTab.created'))
  if (ok) {
    Object.assign(form, { title: '', description: '', deadline: '' })
    assignments.run()
  }
}

async function remove(id: number) {
  if (!confirm(t('teach.assignmentsTab.confirmDelete'))) return
  if (await act(() => assignmentsApi.remove(id), t('ui.deleted'))) assignments.run()
}
</script>

<template>
  <div class="grid--2" style="align-items: start">
    <section class="card">
      <h2>{{ $t('teach.assignmentsTab.title') }}</h2>
      <StateBlock :loading="assignments.loading.value" :error="assignments.error.value"
                  :empty="!assignments.data.value?.results.length" @retry="assignments.run">
        <ul class="list-plain">
          <li v-for="a in assignments.data.value?.results ?? []" :key="a.id" class="row row--between">
            <span>
              <RouterLink :to="`/assignments/${a.id}`">{{ a.title }}</RouterLink>
              <div class="muted small">{{ $t('teach.assignmentsTab.dueSubs', { date: fmtDateTime(a.deadline), n: a.submissions_count ?? 0 }) }}</div>
            </span>
            <span class="row">
              <RouterLink :to="{ path: '/teach/submissions', query: { assignment: a.id } }" class="btn btn--ghost btn--sm">{{ $t('teach.assignmentsTab.check') }}</RouterLink>
              <button class="btn btn--ghost btn--sm" @click="remove(a.id)">{{ $t('ui.delete') }}</button>
            </span>
          </li>
        </ul>
      </StateBlock>
    </section>
    <section class="card">
      <h2>{{ $t('teach.assignmentsTab.new') }}</h2>
      <form class="form" @submit.prevent="create">
        <label>
          {{ $t('teach.assignmentsTab.lesson') }}
          <select v-model.number="form.lesson" required>
            <option :value="0" disabled>{{ $t('teach.assignmentsTab.chooseLesson') }}</option>
            <option v-for="l in lessons.data.value ?? []" :key="l.id" :value="l.id">{{ l.title }}</option>
          </select>
        </label>
        <label>{{ $t('ui.title') }} <input v-model="form.title" required /></label>
        <label>{{ $t('ui.description') }} <textarea v-model="form.description" required /></label>
        <div class="form-row">
          <label>{{ $t('teach.assignmentsTab.deadline') }} <input v-model="form.deadline" type="datetime-local" required /></label>
          <label>{{ $t('teach.assignmentsTab.maxScore') }} <input v-model.number="form.max_score" type="number" min="1" /></label>
        </div>
        <label class="inline"><input v-model="form.accept_late" type="checkbox" /> {{ $t('teach.assignmentsTab.acceptLate') }}</label>
        <button class="btn" :disabled="busy || !form.lesson" style="justify-self: start">{{ $t('ui.create') }}</button>
      </form>
    </section>
  </div>
</template>
