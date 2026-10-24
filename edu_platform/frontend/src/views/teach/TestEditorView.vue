<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { questionsApi, testsApi } from '@/api/tests'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppModal from '@/components/ui/AppModal.vue'
import MathText from '@/components/ui/MathText.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import type { TestInfo } from '@/types/api'
import { attemptStatusLabels, fmtDateTime, fromLocalInput, questionTypeLabels, testModeLabels, toLocalInput } from '@/utils/format'

const props = defineProps<{ id: string }>()

const { t } = useI18n()

const testId = Number(props.id)
const router = useRouter()
const { act, busy } = useAction()
const tab = ref<'questions' | 'settings' | 'stats' | 'attempts'>('questions')

const form = reactive<Partial<TestInfo>>({})
const test = useAsync(async () => {
  const data = await testsApi.get(testId)
  Object.assign(form, { ...data, available_from: toLocalInput(data.available_from), available_to: toLocalInput(data.available_to) })
  return data
})
const items = useAsync(() => testsApi.questions(testId))
const stats = useAsync(() => testsApi.stats(testId), { immediate: false })
const attempts = useAsync(() => testsApi.attempts(testId), { immediate: false })

const picking = ref(false)
const bankSearch = ref('')
const bank = useAsync(() => questionsApi.list({ search: bankSearch.value || undefined, is_archived: false }), { immediate: false })

function open(next: typeof tab.value) {
  tab.value = next
  if (next === 'stats') stats.run()
  if (next === 'attempts') attempts.run()
}

async function saveSettings() {
  const payload = { ...form, available_from: fromLocalInput(form.available_from ?? ''), available_to: fromLocalInput(form.available_to ?? '') }
  if (await act(() => testsApi.update(testId, payload), t('teach.testEditor.saved'))) test.run()
}

async function removeTest() {
  if (!confirm(t('teach.testEditor.confirmDelete'))) return
  const courseId = test.data.value?.course
  if (await act(() => testsApi.remove(testId), t('teach.testEditor.deleted'))) router.push(`/teach/courses/${courseId}`)
}

function openBank() {
  picking.value = true
  bank.run()
}

async function add(questionId: number) {
  if (await act(() => testsApi.addQuestion(testId, questionId, 1), t('teach.testEditor.added'))) {
    items.run()
    test.run()
  }
}

async function setPoints(questionId: number, points: number) {
  await act(() => testsApi.updateQuestion(testId, questionId, { points }))
  items.run()
}

async function removeQuestion(questionId: number) {
  if (await act(() => testsApi.removeQuestion(testId, questionId), t('teach.testEditor.removed'))) items.run()
}

const inTest = (questionId: number) => items.data.value?.some((i) => i.question.id === questionId)
</script>

<template>
  <StateBlock :loading="test.loading.value && !test.data.value" :error="test.error.value" @retry="test.run">
    <template v-if="test.data.value">
      <PageHeader :title="test.data.value.title" :subtitle="`${testModeLabels[test.data.value.mode]} · ${$t('teach.testsTab.questionsN', { n: test.data.value.questions_count })}`">
        <template #before><RouterLink :to="`/teach/courses/${test.data.value.course}`" class="small">{{ $t('ui.toCourseEditor') }}</RouterLink></template>
        <RouterLink :to="`/tests/${id}/take`" class="btn btn--ghost">{{ $t('teach.testEditor.testPage') }}</RouterLink>
      </PageHeader>

      <div class="tabs">
        <button :class="{ active: tab === 'questions' }" @click="open('questions')">{{ $t('teach.testEditor.tabQuestions') }}</button>
        <button :class="{ active: tab === 'settings' }" @click="open('settings')">{{ $t('ui.settings') }}</button>
        <button :class="{ active: tab === 'stats' }" @click="open('stats')">{{ $t('teach.testEditor.tabStats') }}</button>
        <button :class="{ active: tab === 'attempts' }" @click="open('attempts')">{{ $t('teach.testEditor.tabAttempts') }}</button>
      </div>

      <div v-if="tab === 'questions'" class="split">
        <section class="card">
          <div class="row row--between">
            <h2>{{ $t('teach.testEditor.tabQuestions') }} · {{ items.data.value?.length ?? 0 }}</h2>
            <button class="btn btn--sm" @click="openBank">{{ $t('teach.testEditor.fromBank') }}</button>
          </div>
          <StateBlock :loading="items.loading.value" :error="items.error.value" :empty="!items.data.value?.length"
                      :empty-text="$t('teach.testEditor.empty')" @retry="items.run">
            <ul class="list-plain">
              <li v-for="(item, i) in items.data.value ?? []" :key="item.id" class="tq">
                <span class="tq__handle muted">⠿</span>
                <span class="tq__text">{{ i + 1 }}. <MathText :text="item.question.text" /> <span class="badge">{{ questionTypeLabels[item.question.type] }}</span></span>
                <input type="number" min="0" step="0.5" :value="item.points" class="tq__points" :title="$t('teach.testEditor.pointsTitle')"
                       @change="setPoints(item.question.id, Number(($event.target as HTMLInputElement).value))" />
                <span class="small muted">{{ $t('teach.testEditor.pointsShort') }}</span>
                <button class="btn btn--text btn--sm" :title="$t('teach.testEditor.remove')" @click="removeQuestion(item.question.id)"><AppIcon name="x" :size="14" /></button>
              </li>
            </ul>
          </StateBlock>
          <button class="dropzone add-q" @click="openBank">{{ $t('teach.testEditor.fromBank') }} · <RouterLink to="/teach/questions" @click.stop>{{ $t('teach.testEditor.newQ') }}</RouterLink></button>
          <p class="muted small">{{ $t('teach.testEditor.locked') }}</p>
        </section>
        <aside class="card card--subtle summary">
          <div>{{ $t('teach.testEditor.mode') }}: <strong>{{ testModeLabels[test.data.value.mode] }}</strong></div>
          <div>{{ $t('teach.testEditor.time') }}: <strong>{{ test.data.value.time_limit_minutes ? $t('ui.minutes', { n: test.data.value.time_limit_minutes }) : $t('ui.noTimer') }}</strong></div>
          <div>{{ $t('teach.testEditor.pass') }}: <strong>{{ test.data.value.passing_score_pct }}%</strong></div>
          <div>{{ $t('teach.testEditor.attemptsN') }}: <strong>{{ test.data.value.max_attempts || '∞' }}</strong></div>
          <label class="inline"><input type="checkbox" :checked="test.data.value.shuffle_questions" disabled /> {{ $t('teach.testEditor.shuffle') }}</label>
          <label class="inline"><input type="checkbox" :checked="test.data.value.show_answers_after_submit" disabled /> {{ $t('teach.testEditor.showReview') }}</label>
          <button class="btn btn--ghost btn--sm" @click="open('settings')">{{ $t('ui.change') }}</button>
        </aside>
      </div>

      <section v-else-if="tab === 'settings'" class="card">
        <form class="form" @submit.prevent="saveSettings">
          <label>{{ $t('ui.title') }} <input v-model="form.title" required /></label>
          <label>{{ $t('ui.description') }} <textarea v-model="form.description" /></label>
          <div class="form-row">
            <label>
              {{ $t('teach.testEditor.mode') }}
              <select v-model="form.mode">
                <option v-for="(label, key) in testModeLabels" :key="key" :value="key">{{ label }}</option>
              </select>
            </label>
            <label>{{ $t('teach.testsTab.minutes') }} <input v-model.number="form.time_limit_minutes" type="number" min="0" /></label>
            <label>{{ $t('teach.testsTab.attempts') }} <input v-model.number="form.max_attempts" type="number" min="0" /></label>
            <label>{{ $t('teach.testsTab.passing') }} <input v-model.number="form.passing_score_pct" type="number" min="0" max="100" /></label>
          </div>
          <div class="form-row">
            <label>{{ $t('teach.testEditor.from') }} <input v-model="form.available_from" type="datetime-local" /></label>
            <label>{{ $t('teach.testEditor.to') }} <input v-model="form.available_to" type="datetime-local" /></label>
          </div>
          <label class="inline"><input v-model="form.shuffle_questions" type="checkbox" /> {{ $t('teach.testEditor.shuffleQ') }}</label>
          <label class="inline"><input v-model="form.shuffle_options" type="checkbox" /> {{ $t('teach.testEditor.shuffleO') }}</label>
          <label class="inline"><input v-model="form.show_answers_after_submit" type="checkbox" /> {{ $t('teach.testEditor.showAfter') }}</label>
          <div class="row">
            <button class="btn" :disabled="busy">{{ $t('common.save') }}</button>
            <button type="button" class="btn btn--danger" :disabled="busy" @click="removeTest">{{ $t('teach.testEditor.delete') }}</button>
          </div>
        </form>
      </section>

      <section v-else-if="tab === 'stats'" class="stack">
        <StateBlock :loading="stats.loading.value" :error="stats.error.value" @retry="stats.run">
          <template v-if="stats.data.value">
            <div class="grid">
              <div class="card"><div class="stat">{{ stats.data.value.attempts }}</div><span class="muted">{{ $t('teach.testEditor.sAttempts') }}</span></div>
              <div class="card"><div class="stat">{{ stats.data.value.students }}</div><span class="muted">{{ $t('teach.testEditor.sStudents') }}</span></div>
              <div class="card"><div class="stat">{{ stats.data.value.average_score_pct }}%</div><span class="muted">{{ $t('teach.testEditor.sAvg') }}</span></div>
              <div class="card"><div class="stat">{{ stats.data.value.pass_rate_pct }}%</div><span class="muted">{{ $t('teach.testEditor.sPassed') }}</span></div>
              <div class="card"><div class="stat">{{ stats.data.value.anti_cheat_events }}</div><span class="muted">{{ $t('teach.testEditor.sCheat') }}</span></div>
            </div>
            <div class="card table-wrap">
              <table class="table">
                <thead><tr><th>{{ $t('teach.bank.colQuestion') }}</th><th>{{ $t('teach.questionEditor.type') }}</th><th>{{ $t('teach.testEditor.colAnswered') }}</th><th>{{ $t('teach.testEditor.colCorrect') }}</th></tr></thead>
                <tbody>
                  <tr v-for="q in stats.data.value.questions" :key="q.question_id">
                    <td><MathText :text="q.text" /></td>
                    <td>{{ questionTypeLabels[q.type] }}</td>
                    <td>{{ q.answered }}</td>
                    <td :class="{ error: (q.correct_pct ?? 100) < 50 }">{{ q.correct_pct === null ? '—' : `${q.correct_pct}%` }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </StateBlock>
      </section>

      <section v-else class="card">
        <StateBlock :loading="attempts.loading.value" :error="attempts.error.value" :empty="!attempts.data.value?.length" @retry="attempts.run">
          <div class="table-wrap">
            <table class="table">
              <thead><tr><th>{{ $t('roles.student') }}</th><th>{{ $t('teach.testEditor.colStarted') }}</th><th>{{ $t('teach.courseForm.status') }}</th><th>{{ $t('teach.review.score') }}</th><th></th></tr></thead>
              <tbody>
                <tr v-for="a in attempts.data.value ?? []" :key="a.id">
                  <td>{{ a.student_email }}</td>
                  <td>{{ fmtDateTime(a.started_at) }}</td>
                  <td><AppBadge :kind="a.status === 'submitted' ? 'warning' : a.is_passed ? 'success' : 'default'">{{ attemptStatusLabels[a.status] }}</AppBadge></td>
                  <td>{{ a.score }} / {{ a.max_score }} ({{ a.score_pct }}%)</td>
                  <td><RouterLink :to="`/attempts/${a.id}`" class="btn btn--ghost btn--sm">{{ a.status === 'submitted' ? $t('teach.assignmentsTab.check') : $t('teach.testEditor.review') }}</RouterLink></td>
                </tr>
              </tbody>
            </table>
          </div>
        </StateBlock>
      </section>
    </template>
  </StateBlock>

  <AppModal v-if="picking" :title="$t('teach.testEditor.pickTitle')" wide @close="picking = false">
    <form class="row" style="margin-bottom: 12px" @submit.prevent="bank.run">
      <input v-model="bankSearch" type="search" :placeholder="$t('ui.search')" style="max-width: 280px" />
      <button class="btn btn--ghost">{{ $t('teach.testEditor.find') }}</button>
      <RouterLink to="/teach/questions" class="small">{{ $t('teach.testEditor.createInBank') }}</RouterLink>
    </form>
    <StateBlock :loading="bank.loading.value" :error="bank.error.value" :empty="!bank.data.value?.results.length" @retry="bank.run">
      <ul class="list-plain">
        <li v-for="q in bank.data.value?.results ?? []" :key="q.id" class="row row--between">
          <span style="flex: 1"><AppBadge>{{ questionTypeLabels[q.type] }}</AppBadge> <MathText :text="q.text" /></span>
          <button class="btn btn--sm" :disabled="busy || inTest(q.id)" @click="add(q.id)">{{ inTest(q.id) ? $t('teach.testEditor.inTest') : $t('ui.add') }}</button>
        </li>
      </ul>
    </StateBlock>
  </AppModal>
</template>

<style scoped>
.tq {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) 72px auto auto;
  gap: var(--space-sm);
  align-items: center;
}
.tq__points {
  height: 36px;
  text-align: center;
  padding: 0 6px;
}
.add-q {
  display: block;
  width: 100%;
  margin-top: var(--space-sm);
  cursor: pointer;
  font: inherit;
}
.summary {
  display: grid;
  gap: var(--space-sm);
  font-size: var(--fs-body-sm);
}
</style>
