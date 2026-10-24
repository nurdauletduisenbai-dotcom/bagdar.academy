<script setup lang="ts">
import { reactive } from 'vue'

import type { Question, QuestionOption, QuestionType, Topic } from '@/types/api'
import { questionTypeLabels } from '@/utils/format'

const props = defineProps<{ question?: Question; topics: Topic[]; busy?: boolean }>()
const emit = defineEmits<{ save: [payload: Partial<Question>] }>()

const form = reactive({
  topic: props.question?.topic ?? props.topics[0]?.id ?? 0,
  type: (props.question?.type ?? 'single') as QuestionType,
  text: props.question?.text ?? '',
  explanation: props.question?.explanation ?? '',
  difficulty: props.question?.difficulty ?? 3,
  tolerance: props.question?.tolerance ?? 0,
  options: (props.question?.options ?? [
    { text: '', is_correct: true, match_target: '' },
    { text: '', is_correct: false, match_target: '' },
  ]).map((o) => ({ ...o })) as QuestionOption[],
})

const needsOptions = () => form.type !== 'open'

function setSingle(index: number) {
  form.options.forEach((o, i) => (o.is_correct = i === index))
}

function addOption() {
  form.options.push({ text: '', is_correct: ['short', 'number'].includes(form.type), match_target: '' })
}

function submit() {
  const options = needsOptions()
    ? form.options.filter((o) => o.text.trim()).map((o, i) => ({
        ...o, order: i + 1, is_correct: form.type === 'match' ? false : ['short', 'number'].includes(form.type) ? true : o.is_correct,
      }))
    : []
  emit('save', { ...form, options })
}
</script>

<template>
  <form class="form" @submit.prevent="submit">
    <div class="form-row">
      <label>
        {{ $t('teach.questionEditor.topic') }}
        <select v-model.number="form.topic" required>
          <option v-for="t in topics" :key="t.id" :value="t.id">{{ t.subject }} — {{ t.name }}</option>
        </select>
      </label>
      <label>
        {{ $t('teach.questionEditor.type') }}
        <select v-model="form.type">
          <option v-for="(label, key) in questionTypeLabels" :key="key" :value="key">{{ label }}</option>
        </select>
      </label>
      <label>{{ $t('teach.questionEditor.difficulty') }} <input v-model.number="form.difficulty" type="number" min="1" max="5" /></label>
    </div>
    <label>{{ $t('teach.questionEditor.text') }} <textarea v-model="form.text" required /></label>

    <div v-if="needsOptions()" class="stack" style="gap: 8px">
      <span class="small muted">{{ $t(`teach.questionEditor.hint.${form.type}`) }}</span>
      <div v-for="(o, i) in form.options" :key="i" class="row">
        <input v-if="form.type === 'single'" type="radio" name="correct" :checked="o.is_correct" :title="$t('teach.questionEditor.correct')" @change="setSingle(i)" />
        <input v-else-if="form.type === 'multi'" v-model="o.is_correct" type="checkbox" :title="$t('teach.questionEditor.correct')" />
        <input v-model="o.text" :placeholder="form.type === 'match' ? $t('teach.questionEditor.left') : $t('teach.questionEditor.option')" style="flex: 1; min-width: 160px" />
        <input v-if="form.type === 'match'" v-model="o.match_target" :placeholder="$t('teach.questionEditor.right')" style="flex: 1; min-width: 160px" />
        <button type="button" class="btn btn--ghost btn--sm" @click="form.options.splice(i, 1)">✕</button>
      </div>
      <button type="button" class="btn btn--ghost btn--sm" style="justify-self: start" @click="addOption">{{ $t('teach.questionEditor.addOption') }}</button>
    </div>

    <label v-if="form.type === 'number'">{{ $t('teach.questionEditor.tolerance') }} <input v-model.number="form.tolerance" type="number" min="0" step="any" /></label>
    <label>{{ $t('teach.questionEditor.explanation') }} <textarea v-model="form.explanation" /></label>
    <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('teach.questionEditor.save') }}</button>
  </form>
</template>
