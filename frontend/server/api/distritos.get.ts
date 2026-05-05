import { sql } from 'drizzle-orm'
import { distritos } from '~/server/database/schema'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)
  const jornal = query.jornal as string | undefined

  if (jornal) {
    // Only distritos covered by this jornal
    return await db.all<{ codigoine: string; nome: string }>(sql`
      SELECT DISTINCT d.codigoine, d.nome
      FROM distritos d
      JOIN jornais_distritos jd ON jd.distrito_codigoine = d.codigoine
      JOIN jornais j ON j.id = jd.jornal_id
      WHERE j.nome = ${jornal}
      ORDER BY d.nome
    `)
  }

  return await db.select().from(distritos).orderBy(distritos.nome).all()
})
