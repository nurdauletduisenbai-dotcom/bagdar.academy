import type {
  ApplicationStatus,
  DirectorySchool,
  KzRegion,
  ManagedApplication,
  ManagedApplicationPatch,
  Paginated,
  SchoolApplicationPayload,
  SchoolKind,
} from '@/types/api'

import { http } from './http'

const data = <T>(p: Promise<{ data: T }>) => p.then((r) => r.data)

export interface SchoolSearch {
  search?: string
  region?: number
  kind?: SchoolKind
  page?: number
}

/** Справочник школ — публичный, работает до входа (страница регистрации) */
export const schoolsApi = {
  regions: () => data(http.get<KzRegion[]>('/schools/regions/')),
  search: (params: SchoolSearch) => data(http.get<Paginated<DirectorySchool>>('/schools/', { params })),
  apply: (payload: SchoolApplicationPayload) => http.post('/schools/applications/', payload),
}

export const SCHOOL_KINDS: SchoolKind[] = ['school', 'gymnasium', 'lyceum', 'specialized', 'college', 'center', 'extra', 'club', 'other']

const MANAGE = '/schools/applications/manage/'

/** Рассмотрение заявок школ — только суперпользователь */
export const applicationsApi = {
  list: (params: { status?: ApplicationStatus; search?: string; page?: number } = {}) =>
    data(http.get<Paginated<ManagedApplication>>(MANAGE, { params })),
  get: (id: number) => data(http.get<ManagedApplication>(`${MANAGE}${id}/`)),
  update: (id: number, payload: ManagedApplicationPatch) => data(http.patch<ManagedApplication>(`${MANAGE}${id}/`, payload)),
  approve: (id: number) => data(http.post<ManagedApplication>(`${MANAGE}${id}/approve/`, {})),
  reject: (id: number, review_note: string) => data(http.post<ManagedApplication>(`${MANAGE}${id}/reject/`, { review_note })),
  requestInfo: (id: number, review_note: string) =>
    data(http.post<ManagedApplication>(`${MANAGE}${id}/request-info/`, { review_note })),
  summary: () => data(http.get<Record<ApplicationStatus, number>>(`${MANAGE}summary/`)),
}
