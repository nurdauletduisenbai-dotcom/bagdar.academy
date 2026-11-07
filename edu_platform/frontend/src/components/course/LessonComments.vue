<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { commentsApi } from '@/api/content'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'
import type { Comment } from '@/types/api'
import { fmtDateTime } from '@/utils/format'

const props = defineProps<{ lessonId: number; canModerate: boolean }>()

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()

const comments = useAsync(() => commentsApi.list(props.lessonId))
const text = ref('')
const replyTo = ref<Comment | null>(null)

const roots = computed(() => (comments.data.value?.results ?? []).filter((c) => !c.parent))
const repliesOf = (id: number) => (comments.data.value?.results ?? []).filter((c) => c.parent === id)

async function send() {
  if (!text.value.trim()) return
  const ok = await act(() => commentsApi.create({ lesson: props.lessonId, content: text.value, parent: replyTo.value?.id }))
  if (ok) {
    text.value = ''
    replyTo.value = null
    comments.run()
  }
}

async function remove(c: Comment) {
  await act(() => commentsApi.remove(c.id), t('comments.deleted'))
  comments.run()
}

async function toggle(c: Comment) {
  await act(() => commentsApi.toggleHidden(c.id))
  comments.run()
}
</script>

<template>
  <section class="card">
    <h2>{{ $t('comments.title') }}</h2>
    <StateBlock :loading="comments.loading.value" :error="comments.error.value" :empty="!roots.length"
                :empty-text="$t('comments.empty')" @retry="comments.run">
      <ul class="list-lines">
        <li v-for="c in roots" :key="c.id" class="stack" style="gap: 6px">
          <div class="row row--between">
            <strong>{{ c.author.name }}</strong>
            <span class="muted small">{{ fmtDateTime(c.created_at) }}</span>
          </div>
          <p style="margin: 0; white-space: pre-line" :class="{ muted: c.is_hidden }">
            {{ c.content }} <span v-if="c.is_hidden" class="badge">{{ $t('comments.hidden') }}</span>
          </p>
          <div class="row small">
            <button class="btn btn--text btn--sm" @click="replyTo = c">{{ $t('comments.reply') }}</button>
            <button v-if="c.author.id === auth.user?.id || canModerate" class="btn btn--text btn--sm" @click="remove(c)">{{ $t('ui.delete') }}</button>
            <button v-if="canModerate" class="btn btn--text btn--sm" @click="toggle(c)">{{ c.is_hidden ? $t('comments.show') : $t('comments.hide') }}</button>
          </div>
          <ul v-if="repliesOf(c.id).length" class="replies">
            <li v-for="r in repliesOf(c.id)" :key="r.id">
              <div class="row row--between">
                <strong>{{ r.author.name }}</strong>
                <span class="muted small">{{ fmtDateTime(r.created_at) }}</span>
              </div>
              <p style="margin: 4px 0 0; white-space: pre-line">{{ r.content }}</p>
              <button v-if="r.author.id === auth.user?.id || canModerate" class="btn btn--text btn--sm" @click="remove(r)">{{ $t('ui.delete') }}</button>
            </li>
          </ul>
        </li>
      </ul>
    </StateBlock>

    <form class="form" style="margin-top: 16px" @submit.prevent="send">
      <p v-if="replyTo" class="small">
        <i18n-t keypath="comments.replyFor" scope="global"><template #name><strong>{{ replyTo.author.name }}</strong></template></i18n-t>
        <button type="button" class="btn btn--ghost btn--sm" @click="replyTo = null">{{ $t('comments.cancel') }}</button>
      </p>
      <textarea v-model="text" :placeholder="$t('comments.placeholder')" required />
      <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('comments.send') }}</button>
    </form>
  </section>
</template>

<style scoped>
.replies {
  list-style: none;
  margin: var(--space-xs) 0 0 var(--space-xl);
  padding: 0 0 0 var(--space-md);
  border-left: 2px solid var(--green-soft);
  display: grid;
  gap: var(--space-sm);
}
</style>
