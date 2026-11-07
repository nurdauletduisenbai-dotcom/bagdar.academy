<script setup lang="ts">
import { reactive } from 'vue'

import type { CoursePayload } from '@/api/courses'
import type { Course } from '@/types/api'
import { courseStatusLabels, courseTypeLabels } from '@/utils/format'

const props = defineProps<{ course?: Course & { description?: string }; busy?: boolean }>()
const emit = defineEmits<{ save: [payload: CoursePayload] }>()

const form = reactive<CoursePayload>({
  title: props.course?.title ?? '',
  description: props.course?.description ?? '',
  type: props.course?.type ?? 'school_subject',
  subject: props.course?.subject ?? '',
  grade_level: props.course?.grade_level ?? null,
  price: props.course?.price ?? '0',
  access_days: props.course?.access_days ?? 365,
  status: props.course?.status ?? 'draft',
  is_free_preview_enabled: props.course?.is_free_preview_enabled ?? true,
})
</script>

<template>
  <form class="form" @submit.prevent="emit('save', { ...form, grade_level: form.grade_level || null })">
    <label>{{ $t('ui.title') }} <input v-model="form.title" required /></label>
    <label>{{ $t('ui.description') }} <textarea v-model="form.description" /></label>
    <div class="form-row">
      <label>
        {{ $t('teach.courseForm.type') }}
        <select v-model="form.type">
          <option v-for="(label, key) in courseTypeLabels" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <label>{{ $t('teach.courseForm.subject') }} <input v-model="form.subject" /></label>
      <label>{{ $t('teach.courseForm.grade') }} <input v-model.number="form.grade_level" type="number" min="1" max="12" /></label>
    </div>
    <div class="form-row">
      <label>{{ $t('teach.courseForm.price') }} <input v-model="form.price" type="number" min="0" step="1" /></label>
      <label>{{ $t('teach.courseForm.accessDays') }} <input v-model.number="form.access_days" type="number" min="1" /></label>
      <label>
        {{ $t('teach.courseForm.status') }}
        <select v-model="form.status">
          <option v-for="(label, key) in courseStatusLabels" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
    </div>
    <label class="inline"><input v-model="form.is_free_preview_enabled" type="checkbox" /> {{ $t('teach.courseForm.freePreview') }}</label>
    <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('common.save') }}</button>
  </form>
</template>
