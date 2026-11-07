<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { errorMessage } from '@/api/http'
import { SCHOOL_KINDS, schoolsApi } from '@/api/schools'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppModal from '@/components/ui/AppModal.vue'
import type { DirectorySchool, KzRegion, NewSchoolPayload } from '@/types/api'

/**
 * Выбор школы при регистрации: поле открывает окно с поиском по справочнику школ Казахстана
 * и фильтром по региону. «Моей школы нет в списке» — ученик вводит свою школу/кружок (уйдёт на проверку).
 * Ровно одно из двух значений заполнено: v-model:school или v-model:new-school.
 */
defineProps<{ required?: boolean; invalid?: boolean }>()
const school = defineModel<DirectorySchool | null>('school', { default: null })
const newSchool = defineModel<NewSchoolPayload | null>('newSchool', { default: null })

const { t, locale } = useI18n()
const open = ref(false)
const mode = ref<'list' | 'own'>('list')
const searchInput = ref<HTMLInputElement | null>(null)

const regions = ref<KzRegion[]>([])
const query = ref('')
const region = ref<number | undefined>()
const results = ref<DirectorySchool[]>([])
const page = ref(1)
const totalPages = ref(1)
const loading = ref(false)
const error = ref('')

const own = reactive<NewSchoolPayload>({ name: '', kind: 'school', region: 0, locality: '' })
const ownError = ref('')

const kk = computed(() => locale.value === 'kk')
const schoolName = (s: Pick<DirectorySchool, 'name' | 'name_kk' | 'name_ru'>) =>
  (kk.value ? s.name_kk : s.name_ru) || s.name
const regionName = (r: KzRegion) => (kk.value ? r.name_kk : r.name_ru)
// «Астана, Астана» → «Астана»: пункт и регион без повторов
const joinPlace = (...parts: (string | undefined)[]) => parts.filter((v, i, a) => v && a.indexOf(v) === i).join(', ')
const placeLine = (s: DirectorySchool) => joinPlace(s.locality, kk.value ? s.region_name_kk : s.region_name_ru)

const summary = computed(() => {
  if (school.value) return { title: schoolName(school.value), sub: placeLine(school.value), pending: false }
  if (newSchool.value) {
    const r = regions.value.find((x) => x.id === newSchool.value!.region)
    return {
      title: newSchool.value.name,
      sub: joinPlace(newSchool.value.locality, r && regionName(r)),
      pending: true,
    }
  }
  return null
})

async function search(append = false) {
  loading.value = true
  error.value = ''
  try {
    const res = await schoolsApi.search({ search: query.value.trim() || undefined, region: region.value, page: page.value })
    results.value = append ? [...results.value, ...res.results] : res.results
    totalPages.value = res.total_pages
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

let timer: number | undefined
watch([query, region], () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    page.value = 1
    search()
  }, 300)
})

async function openPicker() {
  open.value = true
  mode.value = 'list'
  if (!regions.value.length) {
    try {
      regions.value = await schoolsApi.regions()
    } catch (e) {
      error.value = errorMessage(e)
    }
  }
  if (!results.value.length) search()
  await nextTick()
  searchInput.value?.focus()
}

function more() {
  page.value += 1
  search(true)
}

function pick(s: DirectorySchool) {
  school.value = s
  newSchool.value = null
  open.value = false
}

function startOwn() {
  mode.value = 'own'
  ownError.value = ''
  own.name = own.name || query.value.trim()
  own.region = own.region || region.value || 0
}

function saveOwn() {
  if (own.name.trim().length < 3) {
    ownError.value = t('schoolPicker.ownName')
    return
  }
  if (!own.region) {
    ownError.value = t('schoolPicker.ownRegionPick')
    return
  }
  newSchool.value = { ...own, name: own.name.trim(), locality: own.locality.trim() }
  school.value = null
  open.value = false
}
</script>

<template>
  <div class="picker">
    <span class="picker__label">{{ required ? $t('schoolPicker.label') : $t('schoolPicker.labelOptional') }}</span>
    <button type="button" class="picker__field" :class="{ 'picker__field--invalid': invalid }" aria-haspopup="dialog"
            :aria-label="`${$t('schoolPicker.label')}: ${summary?.title ?? $t('schoolPicker.placeholder')}`" @click="openPicker">
      <AppIcon name="search" :size="16" class="picker__icon" />
      <span v-if="summary" class="picker__value">
        <strong>{{ summary.title }}</strong>
        <small>
          {{ summary.sub }}
          <span v-if="summary.pending" class="badge badge--warning">{{ $t('schoolPicker.pending') }}</span>
        </small>
      </span>
      <span v-else class="picker__placeholder">{{ $t('schoolPicker.placeholder') }}</span>
      <span class="picker__change">{{ summary ? $t('schoolPicker.change') : '' }}</span>
    </button>

    <AppModal v-if="open" :title="mode === 'list' ? $t('schoolPicker.title') : $t('schoolPicker.ownTitle')" wide
              @close="open = false">
      <!-- Поиск по справочнику -->
      <div v-if="mode === 'list'" class="picker__body">
        <div class="picker__filters">
          <input ref="searchInput" v-model="query" type="search" :placeholder="$t('schoolPicker.search')"
                 :aria-label="$t('schoolPicker.search')" />
          <select v-model="region" :aria-label="$t('schoolPicker.ownRegion')">
            <option :value="undefined">{{ $t('schoolPicker.allRegions') }}</option>
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ regionName(r) }}</option>
          </select>
        </div>

        <p v-if="error" class="alert alert--error">{{ error }}</p>
        <ul class="picker__list">
          <li v-for="s in results" :key="s.id">
            <button type="button" class="picker__item" :class="{ selected: school?.id === s.id }" @click="pick(s)">
              <span class="picker__item-text">
                <strong>{{ schoolName(s) }}</strong>
                <small>{{ $t(`schoolPicker.kinds.${s.kind}`) }} · {{ placeLine(s) }}</small>
              </span>
              <span v-if="s.on_platform" class="badge badge--green">{{ $t('schoolPicker.onPlatform') }}</span>
              <AppIcon v-if="school?.id === s.id" name="check" :size="16" class="picker__check" />
            </button>
          </li>
        </ul>
        <p v-if="loading" class="muted small">{{ $t('schoolPicker.loading') }}</p>
        <p v-else-if="!results.length && !error" class="muted small">{{ $t('schoolPicker.nothing') }}</p>
        <button v-if="!loading && page < totalPages" type="button" class="btn btn--ghost btn--sm picker__more" @click="more">
          {{ $t('schoolPicker.more') }}
        </button>

        <button type="button" class="dropzone picker__own" @click="startOwn">
          <AppIcon name="plus" :size="18" />
          <span>
            <strong>{{ $t('schoolPicker.notListed') }}</strong>
            <small>{{ $t('schoolPicker.notListedHint') }}</small>
          </span>
        </button>
        <p class="muted picker__attr">
          {{ $t('schoolPicker.attribution') }}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a>
        </p>
      </div>

      <!-- Своя школа / кружок -->
      <form v-else class="form picker__body" @submit.prevent="saveOwn">
        <label>{{ $t('schoolPicker.ownName') }}
          <input v-model="own.name" required minlength="3" maxlength="255" :placeholder="$t('schoolPicker.ownNamePlaceholder')" />
        </label>
        <label>{{ $t('schoolPicker.ownKind') }}
          <select v-model="own.kind">
            <option v-for="k in SCHOOL_KINDS" :key="k" :value="k">{{ $t(`schoolPicker.kinds.${k}`) }}</option>
          </select>
        </label>
        <div class="form-row">
          <label>{{ $t('schoolPicker.ownRegion') }}
            <select v-model="own.region" required>
              <option :value="0" disabled>{{ $t('schoolPicker.ownRegionPick') }}</option>
              <option v-for="r in regions" :key="r.id" :value="r.id">{{ regionName(r) }}</option>
            </select>
          </label>
          <label>{{ $t('schoolPicker.ownLocality') }} <input v-model="own.locality" maxlength="120" /></label>
        </div>
        <p class="muted small">{{ $t('schoolPicker.ownNote') }}</p>
        <p v-if="ownError" class="alert alert--error">{{ ownError }}</p>
        <div class="row row--between">
          <button type="button" class="btn btn--text" @click="mode = 'list'">
            <AppIcon name="arrow-left" :size="14" /> {{ $t('schoolPicker.back') }}
          </button>
          <button class="btn">{{ $t('schoolPicker.ownSave') }}</button>
        </div>
      </form>
    </AppModal>
  </div>
</template>

<style scoped>
.picker {
  display: grid;
  gap: 6px;
}
.picker__label {
  font: 500 var(--fs-body-sm) / 1.3 var(--font-sans);
  color: var(--text-strong);
}
.picker__field {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  min-height: var(--control-height, 44px);
  padding: 8px 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--surface-card);
  color: var(--text-strong);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.picker__field:hover {
  border-color: var(--green-dark);
}
.picker__field:focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 1px;
}
.picker__field--invalid {
  border-color: var(--error-text);
}
.picker__icon {
  flex-shrink: 0;
  color: var(--text-tertiary);
}
.picker__value {
  display: grid;
  min-width: 0;
}
.picker__value strong {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker__value small {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: var(--fs-micro);
}
.picker__placeholder {
  color: var(--text-tertiary);
}
.picker__change {
  margin-left: auto;
  flex-shrink: 0;
  color: var(--text-link);
  font-size: var(--fs-caption);
}

.picker__body {
  display: grid;
  gap: var(--space-md);
}
.picker__filters {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: var(--space-sm);
}
.picker__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
  max-height: min(48vh, 420px);
  overflow-y: auto;
}
.picker__item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: none;
  font: inherit;
  text-align: left;
  color: var(--text-strong);
  cursor: pointer;
}
.picker__item:hover,
.picker__item:focus-visible {
  background: var(--surface-subtle);
  border-color: var(--border-default);
  outline: none;
}
.picker__item.selected {
  background: var(--surface-feature);
  border-color: var(--green-dark);
}
.picker__item-text {
  display: grid;
  min-width: 0;
  flex: 1;
}
.picker__item-text strong {
  font-weight: 500;
}
.picker__item-text small {
  color: var(--text-secondary);
  font-size: var(--fs-micro);
}
.picker__check {
  color: var(--green-dark);
  flex-shrink: 0;
}
.picker__more {
  justify-self: center;
}
.picker__own {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  padding: var(--space-md);
  font: inherit;
  text-align: left;
  color: var(--text-strong);
  cursor: pointer;
}
.picker__own span {
  display: grid;
}
.picker__own small {
  color: var(--text-secondary);
}
.picker__attr {
  margin: 0;
  font-size: var(--fs-micro);
}
@media (max-width: 560px) {
  .picker__filters {
    grid-template-columns: 1fr;
  }
}
</style>
