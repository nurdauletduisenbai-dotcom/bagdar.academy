<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { coursesApi } from '@/api/courses'
import { announcementsApi } from '@/api/notifications'
import AppModal from '@/components/ui/AppModal.vue'
import AppPager from '@/components/ui/AppPager.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import { fmtDateTime } from '@/utils/format'

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()
const page = ref(1)
const list = useAsync(() => announcementsApi.list({ page: page.value }))
const courses = useAsync(() => (auth.isTeacher ? coursesApi.list() : Promise.resolve(null)))
const creating = ref(false)
const form = reactive({ title: '', content: '', course: null as number | null, notify: true })

async function create() {
  if (await act(() => announcementsApi.create(form), t('announcements.published'))) {
    creating.value = false
    Object.assign(form, { title: '', content: '' })
    list.run()
  }
}

async function remove(id: number) {
  if (confirm(t('announcements.confirmDelete')) && (await act(() => announcementsApi.remove(id), t('ui.deleted')))) list.run()
}
</script>

<template>
  <PageHeader :title="$t('titles.announcements')">
    <button v-if="auth.isTeacher" class="btn" @click="creating = true">{{ $t('announcements.add') }}</button>
  </PageHeader>
  <StateBlock :loading="list.loading.value" :error="list.error.value" :empty="!list.data.value?.results.length"
              :empty-text="$t('announcements.empty')" @retry="list.run">
    <div class="stack">
      <article v-for="a in list.data.value?.results ?? []" :key="a.id" class="card announcement">
        <div class="row row--between">
          <span class="badge" :class="a.course ? '' : 'badge--info'">{{ a.course ? $t('titles.course') : $t('announcements.wholeSchool') }}</span>
          <button v-if="auth.isTeacher" class="btn btn--text btn--sm" @click="remove(a.id)">{{ $t('ui.delete') }}</button>
        </div>
        <h2>{{ a.title }}</h2>
        <p style="white-space: pre-line">{{ a.content }}</p>
        <span class="muted small">{{ a.author }} · {{ fmtDateTime(a.created_at) }}</span>
      </article>
    </div>
    <AppPager :page="page" :total-pages="list.data.value?.total_pages ?? 1" @change="(p) => { page = p; list.run() }" />
  </StateBlock>

  <AppModal v-if="creating" :title="$t('announcements.new')" @close="creating = false">
    <form class="form" @submit.prevent="create">
      <label>
        {{ $t('announcements.audience') }}
        <select v-model="form.course">
          <option v-if="auth.isAdmin" :value="null">{{ $t('announcements.wholeSchool') }}</option>
          <option v-for="c in courses.data.value?.results ?? []" :key="c.id" :value="c.id">{{ $t('announcements.courseOpt', { title: c.title }) }}</option>
        </select>
      </label>
      <label>{{ $t('announcements.heading') }} <input v-model="form.title" required /></label>
      <label>{{ $t('announcements.text') }} <textarea v-model="form.content" required /></label>
      <label class="inline"><input v-model="form.notify" type="checkbox" /> {{ $t('announcements.notify') }}</label>
      <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('ui.publish') }}</button>
    </form>
  </AppModal>
</template>
