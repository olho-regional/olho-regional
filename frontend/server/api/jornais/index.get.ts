import { like, and, count, sql } from 'drizzle-orm'
import { jornais } from '../../database/schema'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const distrito = query.distrito as string | undefined
  const search = query.search as string | undefined
  const page = Math.max(1, parseInt(query.page as string) || 1)
  const perPage = Math.min(100, Math.max(1, parseInt(query.per_page as string) || 24))
  const offset = (page - 1) * perPage

  // If filtering by distrito codigoine, find matching jornal IDs via junction table
  if (distrito) {
    const searchCond = search ? sql`AND j.nome LIKE ${`%${search}%`}` : sql``
    const totalResult = (await db.get(sql`
      SELECT count(DISTINCT j.id) as total
      FROM jornais j
      JOIN jornais_distritos jd ON jd.jornal_id = j.id
      WHERE jd.distrito_codigoine = ${distrito} ${searchCond}
    `)) as { total: number } | undefined
    const items = await db.all(sql`
      SELECT DISTINCT j.*
      FROM jornais j
      JOIN jornais_distritos jd ON jd.jornal_id = j.id
      WHERE jd.distrito_codigoine = ${distrito} ${searchCond}
      ORDER BY j.nome
      LIMIT ${perPage} OFFSET ${offset}
    `)
    const total = totalResult?.total ?? 0
    return { items, total, page, perPage, totalPages: Math.ceil(total / perPage) }
  }

  const conditions = []
  if (search) conditions.push(like(jornais.nome, `%${search}%`))

  const where = conditions.length > 0 ? and(...conditions) : undefined

  const [totalResult, items] = await Promise.all([
    db.select({ total: count() }).from(jornais).where(where).get(),
    db.select().from(jornais).where(where).limit(perPage).offset(offset).all(),
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
