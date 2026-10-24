import { i18n } from '@/i18n'
import type { Role } from '@/types/api'

/** Название роли на текущем языке интерфейса (i18n-ключ `roles.<role>`) */
export function roleLabel(role: Role): string {
  return i18n.global.t(`roles.${role}`)
}

/**
 * Словарь «значение API → подпись» на текущем языке (ключи `labels.<group>.<value>`).
 * Работает и как `map[key]`, и в `v-for="(label, key) in map"`: текст берётся из i18n при каждом чтении,
 * поэтому шаблон перерисовывается при смене языка. Неизвестный ключ → undefined (для `?? key`).
 */
function labelMap<K extends string>(group: string, keys: readonly K[]): Record<string, string> {
  const target = Object.fromEntries(keys.map((k) => [k, k])) as Record<string, string>
  return new Proxy(target, {
    get: (obj, key) => (typeof key === 'string' && key in obj ? i18n.global.t(group ? `labels.${group}.${key}` : `roles.${key}`) : undefined),
  })
}

/** Роли для выпадающих списков (`v-for="(label, key) in roleOptions"`) */
export const roleOptions = labelMap('', ['admin', 'teacher', 'curator', 'student', 'parent'] satisfies Role[])

export const courseTypeLabels = labelMap('courseType', ['school_subject', 'exam_prep', 'club'])
export const courseStatusLabels = labelMap('courseStatus', ['draft', 'published', 'archived'])
export const questionTypeLabels = labelMap('questionType', ['single', 'multi', 'short', 'number', 'match', 'open'])
export const testModeLabels = labelMap('testMode', ['practice', 'quiz', 'exam', 'mock_exam'])
export const attemptStatusLabels = labelMap('attemptStatus', ['in_progress', 'submitted', 'expired', 'graded'])
export const submissionStatusLabels = labelMap('submissionStatus', ['submitted', 'graded', 'returned', 'pending', 'overdue'])
export const attendanceLabels = labelMap('attendance', ['present', 'absent', 'late', 'excused'])
export const orderStatusLabels = labelMap('orderStatus', ['pending', 'paid', 'failed', 'refunded'])
export const enrollmentStatusLabels = labelMap('enrollmentStatus', ['active', 'expired', 'canceled', 'suspended'])
export const auditActionLabels = labelMap('auditAction', [
  'login', 'logout', 'password_change', 'password_reset', 'role_change', 'member_deactivate',
  'course_create', 'course_delete', 'payment_paid', 'payment_refund', 'grade_change',
])

// Числовые форматы (дд.мм.гггг, чч:мм) одинаковы для kk и ru — берём ru-RU, у него данные Intl есть везде
const dateFmt = new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
const dateTimeFmt = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
})
const timeFmt = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })

export const fmtDate = (v?: string | null) => (v ? dateFmt.format(new Date(v)) : '—')
export const fmtDateTime = (v?: string | null) => (v ? dateTimeFmt.format(new Date(v)) : '—')
export const fmtTime = (v?: string | null) => (v ? timeFmt.format(new Date(v)) : '—')

export function fmtMoney(value: string | number, currency = 'KZT') {
  const n = Number(value)
  if (!n) return i18n.global.t('ui.free')
  return `${n.toLocaleString('ru-RU')} ${currency === 'KZT' ? '₸' : currency}`
}

export function fmtDuration(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function fmtBytes(bytes: number) {
  if (!bytes) return ''
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} ${i18n.global.t('ui.kb')}`
  return `${(bytes / 1024 / 1024).toFixed(1)} ${i18n.global.t('ui.mb')}`
}

/** ISO-строка -> значение для <input type="datetime-local"> */
export function toLocalInput(v?: string | null) {
  if (!v) return ''
  const d = new Date(v)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Значение <input type="datetime-local"> -> ISO-строка с часовым поясом */
export const fromLocalInput = (v: string) => (v ? new Date(v).toISOString() : null)

const TAG_TONES = ['', 'purple', 'orange', 'blue', 'pink', 'teal'] as const

/** Цвет тега категории (CategoryTag) по названию предмета — стабильно для одного предмета */
export function subjectTone(subject?: string | null): string {
  if (!subject) return ''
  let h = 0
  for (const ch of subject.toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  const tone = TAG_TONES[h % TAG_TONES.length]
  return tone ? `tag--${tone}` : ''
}

const KK_MONTHS = ['қаңтар', 'ақпан', 'наурыз', 'сәуір', 'мамыр', 'маусым',
  'шілде', 'тамыз', 'қыркүйек', 'қазан', 'қараша', 'желтоқсан']
const KK_MONTHS_SHORT = ['қаң.', 'ақп.', 'нау.', 'сәу.', 'мам.', 'мау.', 'шіл.', 'там.', 'қыр.', 'қаз.', 'қар.', 'жел.']
/** Индекс как у Date.getDay(): 0 — воскресенье */
const KK_WEEKDAYS_SHORT = ['жс', 'дс', 'сс', 'ср', 'бс', 'жм', 'сн']
const ruLongDate = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
const ruDayMonth = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })
const ruDayMonthShort = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const ruWeekdayShort = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' })

const isKk = () => i18n.global.locale.value === 'kk'
const toDate = (v: string | Date) => (v instanceof Date ? v : new Date(v))

/**
 * «24 қазан 2026 ж.» / «24 октября 2026 г.» — дата на текущем языке интерфейса.
 * Казахские месяцы — вручную: во многих браузерах в Intl нет данных kk (выходит «2026 M10 24»).
 */
export function fmtDateLong(v?: string | null): string {
  if (!v) return '—'
  const d = new Date(v)
  if (isKk()) return `${d.getDate()} ${KK_MONTHS[d.getMonth()]} ${d.getFullYear()} ж.`
  return ruLongDate.format(d)
}

/** «24 қазан» / «24 октября»; `short` — «24 қаз.» / «24 окт.» */
export function fmtDayMonth(v: string | Date, short = false): string {
  const d = toDate(v)
  if (isKk()) return `${d.getDate()} ${(short ? KK_MONTHS_SHORT : KK_MONTHS)[d.getMonth()]}`
  return (short ? ruDayMonthShort : ruDayMonth).format(d)
}

/** Короткий день недели: «дс» / «пн» */
export function fmtWeekday(v: string | Date): string {
  const d = toDate(v)
  return isKk() ? KK_WEEKDAYS_SHORT[d.getDay()] : ruWeekdayShort.format(d)
}
