import { sql } from 'drizzle-orm'

export default defineCachedEventHandler(async (event) => {
  const db = useDB(event)
  const rows = await db.all<{ nome: string }>(sql`
    SELECT nome FROM jornais WHERE nome IS NOT NULL ORDER BY RANDOM()
  `)
  return rows.map(r => r.nome)
}, {
  maxAge: 60 * 60 * 24 * 3,
  swr: true,
  name: 'jornal-names',
})
