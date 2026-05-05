import type { Jornal } from '~/server/database/schema'

export interface PaginatedResponse {
  items: Jornal[]
  total: number
  page: number
  perPage: number
  totalPages: number
}

export interface JornalDetail extends Jornal {
  distritos: { codigoine: string; nome: string; regiao: string }[]
  municipios: { codigoine: string; nome: string }[]
  totalArticles: number
  oldestDate: string | null
  newestDate: string | null
  genderByYear: { year: string; gender: string; count: number }[]
}

export interface JornalArticle {
  id: string
  title: string | null
  date: string | null
  author: string | null
  url: string
  archive_url: string | null
}

export interface PaginatedArticles {
  items: JornalArticle[]
  total: number
  page: number
  perPage: number
  totalPages: number
}

export function useJornais(params: Ref<{ distrito?: string; search?: string; page?: number }>) {
  return useFetch<PaginatedResponse>('/api/jornais', {
    query: params,
    watch: [params],
  })
}

export function useJornal(id: number | string) {
  return useFetch<JornalDetail>(`/api/jornais/${id}`)
}

export function useJornalNoticias(id: number | string, params: Ref<{ page: number; per_page: number }>) {
  return useFetch<PaginatedArticles>(`/api/jornais/${id}/noticias`, {
    query: params,
    watch: [params],
  })
}
