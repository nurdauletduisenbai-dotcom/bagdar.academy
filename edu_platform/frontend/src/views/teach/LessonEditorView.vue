<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { lessonsApi, materialsApi, videosApi } from '@/api/content'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { fmtBytes, fmtDuration, fromLocalInput, toLocalInput } from '@/utils/format'

const props = defineProps<{ id: string }>()

const { t } = useI18n()

const lessonId = Number(props.id)
const router = useRouter()
const { act, busy } = useAction()

const form = reactive({ title: '', order: 1, is_free_preview: false, publish_at: '' })
const lesson = useAsync(async () => {
  const l = await lessonsApi.get(lessonId)
  Object.assign(form, { title: l.title, order: l.order, is_free_preview: l.is_free_preview, publish_at: toLocalInput(l.publish_at) })
  return l
})
const videos = useAsync(() => videosApi.list(lessonId))
const materials = useAsync(() => materialsApi.list(lessonId))

const video = reactive({ title: '', youtube_url: '', minutes: 10 })
const material = reactive({ title: '', file_url: '' })
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

async function saveLesson() {
  if (await act(() => lessonsApi.update(lessonId, { ...form, publish_at: fromLocalInput(form.publish_at) }), t('teach.programTab.saved'))) lesson.run()
}

async function removeLesson() {
  if (!confirm(t('teach.lessonEditor.confirmDelete'))) return
  const courseId = lesson.data.value?.course_id
  if (await act(() => lessonsApi.remove(lessonId), t('teach.lessonEditor.deleted'))) router.push(`/teach/courses/${courseId}`)
}

async function addVideo() {
  const ok = await act(() => videosApi.create({
    lesson: lessonId, title: video.title, youtube_url: video.youtube_url, duration_seconds: Math.round(video.minutes * 60),
  }), t('teach.lessonEditor.videoAdded'))
  if (ok) {
    Object.assign(video, { title: '', youtube_url: '' })
    videos.run()
  }
}

async function removeVideo(id: number) {
  if (await act(() => videosApi.remove(id), t('teach.lessonEditor.videoDeleted'))) videos.run()
}

async function addMaterial() {
  const ok = await act(() => materialsApi.create({ lesson: lessonId, title: material.title, file: file.value, file_url: material.file_url }),
    t('teach.lessonEditor.materialAdded'))
  if (ok) {
    Object.assign(material, { title: '', file_url: '' })
    file.value = null
    if (fileInput.value) fileInput.value.value = ''
    materials.run()
  }
}

async function removeMaterial(id: number) {
  if (await act(() => materialsApi.remove(id), t('teach.lessonEditor.materialDeleted'))) materials.run()
}
</script>

<template>
  <StateBlock :loading="lesson.loading.value && !lesson.data.value" :error="lesson.error.value" @retry="lesson.run">
    <template v-if="lesson.data.value">
      <PageHeader :title="$t('teach.lessonEditor.title', { title: lesson.data.value.title })">
        <template #before><RouterLink :to="`/teach/courses/${lesson.data.value.course_id}`" class="small">{{ $t('ui.toCourseEditor') }}</RouterLink></template>
        <RouterLink :to="`/lessons/${id}`" class="btn btn--ghost">{{ $t('ui.asStudent') }}</RouterLink>
      </PageHeader>

      <div class="grid--2" style="align-items: start">
        <section class="card">
          <h2>{{ $t('teach.lessonEditor.params') }}</h2>
          <form class="form" @submit.prevent="saveLesson">
            <label>{{ $t('ui.title') }} <input v-model="form.title" required /></label>
            <div class="form-row">
              <label>{{ $t('teach.lessonEditor.order') }} <input v-model.number="form.order" type="number" min="1" /></label>
              <label>{{ $t('teach.lessonEditor.publishAt') }} <input v-model="form.publish_at" type="datetime-local" /></label>
            </div>
            <label class="inline"><input v-model="form.is_free_preview" type="checkbox" /> {{ $t('teach.lessonEditor.freePreview') }}</label>
            <div class="row">
              <button class="btn" :disabled="busy">{{ $t('common.save') }}</button>
              <button type="button" class="btn btn--danger" :disabled="busy" @click="removeLesson">{{ $t('teach.lessonEditor.delete') }}</button>
            </div>
          </form>
        </section>

        <section class="card">
          <h2>{{ $t('teach.lessonEditor.video') }}</h2>
          <StateBlock :loading="videos.loading.value" :error="videos.error.value" :empty="!videos.data.value?.length" @retry="videos.run">
            <ul class="list-plain">
              <li v-for="v in videos.data.value ?? []" :key="v.id" class="row row--between">
                <span>{{ v.title }} <span class="muted small">{{ v.youtube_video_id }} · {{ fmtDuration(v.duration_seconds) }}</span></span>
                <button class="btn btn--ghost btn--sm" @click="removeVideo(v.id)">{{ $t('ui.delete') }}</button>
              </li>
            </ul>
          </StateBlock>
          <form class="form" style="margin-top: 12px" @submit.prevent="addVideo">
            <label>{{ $t('ui.title') }} <input v-model="video.title" required /></label>
            <label>{{ $t('teach.lessonEditor.youtube') }} <input v-model="video.youtube_url" placeholder="https://youtu.be/…" required /></label>
            <label>{{ $t('teach.lessonEditor.duration') }} <input v-model.number="video.minutes" type="number" min="0" step="0.5" /></label>
            <button class="btn btn--ghost" :disabled="busy" style="justify-self: start">{{ $t('teach.lessonEditor.addVideo') }}</button>
          </form>
        </section>

        <section class="card" style="grid-column: 1 / -1">
          <h2>{{ $t('teach.lessonEditor.materials') }}</h2>
          <StateBlock :loading="materials.loading.value" :error="materials.error.value" :empty="!materials.data.value?.length" @retry="materials.run">
            <ul class="list-plain">
              <li v-for="m in materials.data.value ?? []" :key="m.id" class="row row--between">
                <span>{{ m.title }} <span class="muted small">{{ m.has_file ? `${m.file_type} ${fmtBytes(m.file_size_bytes)}` : m.file_url }}</span></span>
                <button class="btn btn--ghost btn--sm" @click="removeMaterial(m.id)">{{ $t('ui.delete') }}</button>
              </li>
            </ul>
          </StateBlock>
          <form class="form-row" style="margin-top: 12px; align-items: end" @submit.prevent="addMaterial">
            <label>{{ $t('ui.title') }} <input v-model="material.title" required /></label>
            <label>{{ $t('teach.lessonEditor.file') }}
              <input ref="fileInput" type="file" @change="file = ($event.target as HTMLInputElement).files?.[0] ?? null" />
            </label>
            <label>{{ $t('teach.lessonEditor.orLink') }} <input v-model="material.file_url" type="url" /></label>
            <button class="btn btn--ghost" :disabled="busy">{{ $t('teach.lessonEditor.addMaterial') }}</button>
          </form>
        </section>
      </div>
    </template>
  </StateBlock>
</template>
