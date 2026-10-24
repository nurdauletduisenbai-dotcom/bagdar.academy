/**
 * Демо-аккаунты для локальной проверки (создаются `make seed`).
 * Кнопки быстрого входа показываются, только если VITE_SHOW_DEMO_ACCOUNTS !== 'false'.
 */
export interface DemoAccount {
  /** Ключ i18n `demo.<key>.role` / `demo.<key>.note` — подпись кнопки и подсказка */
  key: string
  email: string
  password: string
}

export const demoAccounts: DemoAccount[] = [
  { key: 'admin', email: 'admin@fizmat.kz', password: 'AdminPassword123!' },
  { key: 'teacher', email: 'teacher@fizmat.kz', password: 'TeacherPassword123!' },
  { key: 'curator', email: 'curator@fizmat.kz', password: 'CuratorPassword123!' },
  { key: 'student', email: 'student1@fizmat.kz', password: 'StudentPassword123!' },
  { key: 'student2', email: 'student2@fizmat.kz', password: 'StudentPassword123!' },
  { key: 'parent', email: 'parent@fizmat.kz', password: 'ParentPassword123!' },
  { key: 'multi', email: 'multi@fizmat.kz', password: 'MultiPassword123!' },
  { key: 'school2', email: 'admin@school2.kz', password: 'School2Password123!' },
]

export const showDemoAccounts = import.meta.env.VITE_SHOW_DEMO_ACCOUNTS !== 'false'
