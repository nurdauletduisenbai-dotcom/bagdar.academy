<script setup lang="ts">
import { reactive } from 'vue'
import { useI18n } from 'vue-i18n'

import { orgsApi } from '@/api/orgs'
import PageHeader from '@/components/ui/PageHeader.vue'
import StateBlock from '@/components/ui/StateBlock.vue'
import { useAction, useAsync } from '@/composables/useAsync'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()

const auth = useAuthStore()
const { act, busy } = useAction()
const form = reactive({ name: '', logo_url: '', timezone: '' })
const org = useAsync(async () => {
  const o = await orgsApi.current()
  Object.assign(form, { name: o.name, logo_url: o.logo_url ?? '', timezone: o.timezone })
  return o
})

async function save() {
  if (await act(() => orgsApi.updateCurrent({ ...form, logo_url: form.logo_url || null }), t('profile.prefsSaved'))) {
    await auth.loadProfile(auth.user?.org_id ?? null)
  }
}
</script>

<template>
  <PageHeader :title="$t('nav.settings')" />
  <StateBlock :loading="org.loading.value" :error="org.error.value" @retry="org.run">
    <section v-if="org.data.value" class="card">
      <form class="form" @submit.prevent="save">
        <label>{{ $t('ui.title') }} <input v-model="form.name" required /></label>
        <label>{{ $t('admin.settings.slug') }} <input :value="org.data.value.slug" disabled /></label>
        <label>{{ $t('admin.settings.logo') }} <input v-model="form.logo_url" type="url" /></label>
        <label>{{ $t('admin.settings.tz') }} <input v-model="form.timezone" placeholder="Asia/Almaty" /></label>
        <button class="btn" :disabled="busy" style="justify-self: start">{{ $t('common.save') }}</button>
      </form>
    </section>
  </StateBlock>
</template>
