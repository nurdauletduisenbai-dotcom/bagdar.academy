import type { DirectorySchool, KzRegion, Paginated, SchoolKind } from '@/types/api'

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
}

export const SCHOOL_KINDS: SchoolKind[] = ['school', 'gymnasium', 'lyceum', 'specialized', 'college', 'center', 'extra', 'club', 'other']
