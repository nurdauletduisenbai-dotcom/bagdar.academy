import { watch } from 'vue'
import { createRouter, createWebHistory, type RouteLocationNormalized, type RouteRecordRaw } from 'vue-router'

import { i18n } from '@/i18n'

import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/stores/toast'
import type { Role } from '@/types/api'

declare module 'vue-router' {
  interface RouteMeta {
    /** Страница без входа (логин, регистрация...) */
    public?: boolean
    /** Только для гостей: авторизованного перекинет на главную */
    guestOnly?: boolean
    /** Кому доступна страница (роль в текущей организации) */
    roles?: Role[]
    /** Ключ i18n заголовка вкладки (`titles.*`); переводится при показе и при смене языка */
    title?: string
  }
}

const STAFF: Role[] = ['admin', 'teacher', 'curator']
const TEACHERS: Role[] = ['admin', 'teacher']

const routes: RouteRecordRaw[] = [
  // ---------- Публичные ----------
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true, guestOnly: true, title: 'titles.login' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true, guestOnly: true, title: 'titles.register' } },
  { path: '/invite', name: 'invite', component: () => import('@/views/auth/InviteRegisterView.vue'), meta: { public: true, guestOnly: true, title: 'titles.invite' } },
  { path: '/forgot-password', name: 'forgot-password', component: () => import('@/views/auth/ForgotPasswordView.vue'), meta: { public: true, guestOnly: true, title: 'titles.forgotPassword' } },
  { path: '/reset-password', name: 'reset-password', component: () => import('@/views/auth/ResetPasswordView.vue'), meta: { public: true, title: 'titles.resetPassword' } },
  { path: '/verify-email', name: 'verify-email', component: () => import('@/views/auth/VerifyEmailView.vue'), meta: { public: true, title: 'titles.verifyEmail' } },

  // ---------- Публичный сайт: главная с новостями (вошедших главная перекидывает в кабинет /home) ----------
  {
    path: '/',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      { path: '', name: 'landing', component: () => import('@/views/public/LandingView.vue'), meta: { public: true, guestOnly: true, title: 'bagdar.academy' } },
      { path: 'news', name: 'news', component: () => import('@/views/public/NewsListView.vue'), meta: { public: true, title: 'titles.news' } },
      { path: 'news/:slug', name: 'news-post', component: () => import('@/views/public/PostView.vue'), props: true, meta: { public: true, title: 'titles.news' } },
    ],
  },

  // ---------- Приложение ----------
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: 'home', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: 'titles.home' } },
      { path: 'catalog', name: 'catalog', component: () => import('@/views/CoursesView.vue'), meta: { title: 'titles.catalog' } },
      { path: 'my-courses', name: 'my-courses', component: () => import('@/views/courses/MyCoursesView.vue'), meta: { title: 'titles.myCourses' } },
      { path: 'courses/:id', name: 'course', component: () => import('@/views/courses/CourseView.vue'), props: true, meta: { title: 'titles.course' } },
      { path: 'lessons/:id', name: 'lesson', component: () => import('@/views/courses/LessonView.vue'), props: true, meta: { title: 'titles.lesson' } },

      { path: 'tests/:id/take', name: 'test-take', component: () => import('@/views/tests/TestTakeView.vue'), props: true, meta: { title: 'titles.test' } },
      { path: 'attempts/:id', name: 'attempt', component: () => import('@/views/tests/AttemptResultView.vue'), props: true, meta: { title: 'titles.result' } },

      { path: 'assignments', name: 'assignments', component: () => import('@/views/assignments/AssignmentsView.vue'), meta: { title: 'titles.assignments' } },
      { path: 'assignments/:id', name: 'assignment', component: () => import('@/views/assignments/AssignmentView.vue'), props: true, meta: { title: 'titles.assignment' } },

      { path: 'schedule', name: 'schedule', component: () => import('@/views/ScheduleView.vue'), meta: { title: 'titles.schedule' } },
      { path: 'notifications', name: 'notifications', component: () => import('@/views/NotificationsView.vue'), meta: { title: 'titles.notifications' } },
      { path: 'announcements', name: 'announcements', component: () => import('@/views/AnnouncementsView.vue'), meta: { title: 'titles.announcements' } },

      { path: 'progress', name: 'progress', component: () => import('@/views/progress/MyProgressView.vue'), meta: { title: 'titles.progress' } },
      { path: 'progress/courses/:courseId', name: 'course-report', component: () => import('@/views/progress/CourseReportView.vue'), props: true, meta: { title: 'titles.courseReport' } },
      { path: 'children', name: 'children', component: () => import('@/views/progress/ChildrenView.vue'), meta: { roles: ['parent'], title: 'titles.children' } },
      { path: 'orders', name: 'orders', component: () => import('@/views/OrdersView.vue'), meta: { title: 'titles.myOrders' } },
      { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { title: 'titles.profile' } },

      // ---------- Преподавание ----------
      { path: 'teach/courses', name: 'teach-courses', component: () => import('@/views/teach/TeachCoursesView.vue'), meta: { roles: STAFF, title: 'titles.teachCourses' } },
      { path: 'teach/courses/:id', name: 'course-editor', component: () => import('@/views/teach/CourseEditorView.vue'), props: true, meta: { roles: STAFF, title: 'titles.courseEditor' } },
      { path: 'teach/lessons/:id', name: 'lesson-editor', component: () => import('@/views/teach/LessonEditorView.vue'), props: true, meta: { roles: TEACHERS, title: 'titles.lessonEditor' } },
      { path: 'teach/tests/:id', name: 'test-editor', component: () => import('@/views/teach/TestEditorView.vue'), props: true, meta: { roles: STAFF, title: 'titles.testEditor' } },
      { path: 'teach/questions', name: 'question-bank', component: () => import('@/views/teach/QuestionBankView.vue'), meta: { roles: TEACHERS, title: 'titles.questionBank' } },
      { path: 'teach/submissions', name: 'submissions', component: () => import('@/views/teach/SubmissionsView.vue'), meta: { roles: TEACHERS, title: 'titles.submissions' } },

      // ---------- Администрирование ----------
      { path: 'admin', name: 'admin', component: () => import('@/views/admin/AdminDashboardView.vue'), meta: { roles: ['admin'], title: 'titles.summary' } },
      { path: 'admin/members', name: 'members', component: () => import('@/views/admin/MembersView.vue'), meta: { roles: STAFF, title: 'titles.members' } },
      { path: 'admin/invites', name: 'invites', component: () => import('@/views/admin/InvitesView.vue'), meta: { roles: TEACHERS, title: 'titles.invites' } },
      { path: 'admin/orders', name: 'admin-orders', component: () => import('@/views/OrdersView.vue'), props: { admin: true }, meta: { roles: ['admin'], title: 'titles.orders' } },
      { path: 'admin/audit', name: 'audit', component: () => import('@/views/admin/AuditView.vue'), meta: { roles: ['admin'], title: 'titles.audit' } },
      { path: 'admin/settings', name: 'org-settings', component: () => import('@/views/admin/OrgSettingsView.vue'), meta: { roles: ['admin'], title: 'titles.settings' } },
    ],
  },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue'), meta: { public: true, title: 'titles.notFound' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // Якоря главной (#about, #courses…) — плавная прокрутка; отступ задаёт scroll-margin-top секции
  scrollBehavior: (to) => (to.hash ? { el: to.hash, behavior: 'smooth' } : { top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: 'home' }
  }
  if (to.meta.roles && !auth.hasRole(...to.meta.roles)) {
    useToast().error(i18n.global.t('ui.forbidden'))
    return { name: 'home' }
  }
})

function applyTitle(to: RouteLocationNormalized) {
  const title = to.meta.title === 'bagdar.academy' ? '' : to.meta.title ? i18n.global.t(to.meta.title) : ''
  document.title = title ? `${title} — EduPlatform` : 'EduPlatform'
}

router.afterEach(applyTitle)
// Заголовок вкладки следует за переключателем языка
watch(i18n.global.locale, () => applyTitle(router.currentRoute.value))

export default router
