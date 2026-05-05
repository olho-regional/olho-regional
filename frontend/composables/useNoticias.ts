export interface NoticiaResult {
  id: string
  title: string | null
  date: string | null
  author: string | null
  url: string
  archive_url: string | null
  jornal_nome: string | null
}

export interface PaginatedNoticias {
  items: NoticiaResult[]
  total: number
  page: number
  perPage: number
  totalPages: number
  yearCounts: { year: string; count: number }[]
}

export interface FacetsData {
  labelCounts?: { name: string; count: number }[]
  jornalCounts?: { name: string; count: number }[]
  distritoCounts?: { name: string; count: number }[]
  genderByYear?: { year: string; gender: string; count: number }[]
  dateCounts?: { date: string; count: number }[]
}

export function useNoticias(params: Ref<{
  search?: string
  distrito?: string
  year_from?: number
  year_to?: number
  page?: number
  per_page?: number
}>) {
  return useFetch<PaginatedNoticias>('/api/noticias', {
    query: params,
    watch: [params],
  })
}
