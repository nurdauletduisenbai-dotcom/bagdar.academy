<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { groupsApi } from '@/api/courses'
import { sessionsApi } from '@/api/schedule'
import AppModal from '@/components/ui/AppModal.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import type { Group, GroupStudent } from '@/types/api'
import { fromLocalInput } from '@/utils/format'

const props = defineProps<{ courseId: number }>()

const { t } = useI18n()

const { act, busy } = useAction()
const groups = useAsync(() => groupsApi.list(props.courseId))
const newGroup = reactive({ name: '', max_students: 30 })
const viewing = ref<{ group: Group; students: GroupStudent[] } | null>(null)
const session = reactive({ group: 0, title: '', start_time: '', end_time: '', location: '', online_meeting_url: '' })

async function addGroup() {
  if (await act(() => groupsApi.create({ course: props.courseId, ...newGroup }), t('teach.groupsTab.groupCreated'))) {
    newGroup.name = ''
    groups.run()
  }
}

async function showStudents(group: Group) {
  const students = await act(() => groupsApi.students(group.id))
  if (students) viewing.value = { group, students }
}

async function addSession() {
  const ok = await act(() => sessionsApi.create({
    ...session,
    start_time: fromLocalInput(session.start_time)!,
    end_time: fromLocalInput(session.end_time)!,
    online_meeting_url: session.online_meeting_url || null,
  }), t('teach.groupsTab.sessionAdded'))
  if (ok) Object.assign(session, { title: '', start_time: '', end_time: '' })
}
</script>

<template>
  <div class="grid--2" style="align-items: start">
    <section class="card">
      <h2>{{ $t('teach.groupsTab.groups') }}</h2>
      <StateBlock :loading="groups.loading.value" :error="groups.error.value" :empty="!groups.data.value?.length" @retry="groups.run">
        <ul class="list-plain">
          <li v-for="g in groups.data.value ?? []" :key="g.id" class="row row--between">
            <span>{{ g.name }} <span class="muted small">{{ g.students_count }}/{{ g.max_students }}</span></span>
            <button class="btn btn--ghost btn--sm" @click="showStudents(g)">{{ $t('teach.groupsTab.students') }}</button>
          </li>
        </ul>
      </StateBlock>
      <form class="row" style="margin-top: 12px" @submit.prevent="addGroup">
        <input v-model="newGroup.name" :placeholder="$t('teach.groupsTab.groupName')" style="max-width: 220px" required />
        <input v-model.number="newGroup.max_students" type="number" min="1" style="max-width: 90px" :title="$t('teach.groupsTab.seats')" />
        <button class="btn btn--ghost" :disabled="busy">{{ $t('teach.groupsTab.addGroup') }}</button>
      </form>
      <p class="muted small">{{ $t('teach.groupsTab.studentsHint') }}</p>
    </section>

    <section class="card">
      <h2>{{ $t('teach.groupsTab.addSession') }}</h2>
      <form class="form" @submit.prevent="addSession">
        <label>
          {{ $t('teach.groupsTab.group') }}
          <select v-model.number="session.group" required>
            <option :value="0" disabled>{{ $t('ui.choose') }}</option>
            <option v-for="g in groups.data.value ?? []" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
        </label>
        <label>{{ $t('teach.groupsTab.topic') }} <input v-model="session.title" required /></label>
        <div class="form-row">
          <label>{{ $t('teach.groupsTab.start') }} <input v-model="session.start_time" type="datetime-local" required /></label>
          <label>{{ $t('teach.groupsTab.end') }} <input v-model="session.end_time" type="datetime-local" required /></label>
        </div>
        <div class="form-row">
          <label>{{ $t('teach.groupsTab.room') }} <input v-model="session.location" /></label>
          <label>{{ $t('teach.groupsTab.link') }} <input v-model="session.online_meeting_url" type="url" /></label>
        </div>
        <button class="btn" :disabled="busy || !session.group" style="justify-self: start">{{ $t('ui.add') }}</button>
      </form>
    </section>
  </div>

  <AppModal v-if="viewing" :title="$t('teach.groupsTab.groupTitle', { name: viewing.group.name })" @close="viewing = null">
    <ul v-if="viewing.students.length" class="list-plain">
      <li v-for="s in viewing.students" :key="s.student_id">{{ s.full_name }} <span class="muted small">{{ s.email }}</span></li>
    </ul>
    <p v-else class="muted">{{ $t('teach.groupsTab.noStudents') }}</p>
  </AppModal>
</template>
