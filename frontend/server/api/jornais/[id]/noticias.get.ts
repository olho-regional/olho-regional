import { eq, desc, count } from 'drizzle-orm'
import { noticias } from '../../../database/schema'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const id = Number(getRouterParam(event, 'id'))

  if (isNaN(id)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid ID' })
  }

  const query = getQuery(event)
  const page = Math.max(1, parseInt(query.page as string) || 1)
  const perPage = Math.min(100, Math.max(1, parseInt(query.per_page as string) || 20))
  const offset = (page - 1) * perPage

  const [totalResult, items] = await Promise.all([
    db.select({ total: count() })
      .from(noticias)
      .where(eq(noticias.jornal_id, id))
      .get(),
    db.select({
      id: noticias.id,
      title: noticias.title,
      date: noticias.date,
      author: noticias.author,
      url: noticias.url,
      archive_url: noticias.archive_url,
    })
      .from(noticias)
      .where(eq(noticias.jornal_id, id))
      .orderBy(desc(noticias.date))
      .limit(perPage)
      .offset(offset)
      .all(),
  ])

  const total = totalResult?.total ?? 0

  return {
    items,
    total,
    page,
    perPage,
    totalPages: Math.ceil(total / perPage),
  }
})
