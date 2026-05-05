import { eq, sql } from 'drizzle-orm'
import { jornais, noticias, jornaisDistritos, jornaisMunicipios, distritos, municipios } from '../../database/schema'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const id = Number(getRouterParam(event, 'id'))

  if (isNaN(id)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid ID' })
  }

  const result = await db.select().from(jornais)
    .where(eq(jornais.id, id))
    .get()

  if (!result) {
    throw createError({ statusCode: 404, statusMessage: 'Jornal not found' })
  }

  const [stats, jornalDistritos, jornalMunicipios, genderByYear] = await Promise.all([
    db.select({
      totalArticles: sql<number>`count(*)`,
      oldestDate: sql<string | null>`min(${noticias.date})`,
      newestDate: sql<string | null>`max(${noticias.date})`,
    }).from(noticias)
      .where(eq(noticias.jornal_id, id))
      .get(),
    db.select({
      codigoine: distritos.codigoine,
      nome: distritos.nome,
      regiao: distritos.regiao,
    }).from(jornaisDistritos)
      .innerJoin(distritos, eq(jornaisDistritos.distritoCodigoine, distritos.codigoine))
      .where(eq(jornaisDistritos.jornalId, id))
      .all(),
    db.select({
      codigoine: municipios.codigoine,
      nome: municipios.nome,
    }).from(jornaisMunicipios)
      .innerJoin(municipios, eq(jornaisMunicipios.municipioCodigoine, municipios.codigoine))
      .where(eq(jornaisMunicipios.jornalId, id))
      .all(),
    db.all<{ year: string; gender: string; count: number }>(sql`
      SELECT substr(n.date, 1, 4) as year, q.gender, count(*) as count
      FROM quotes q
      JOIN noticias n ON n.id = q.noticia_id
      WHERE n.jornal_id = ${id}
        AND n.date IS NOT NULL AND length(n.date) >= 4
      GROUP BY year, q.gender ORDER BY year
    `),
  ])

  return {
    ...result,
    distritos: jornalDistritos,
    municipios: jornalMunicipios,
    totalArticles: stats?.totalArticles ?? 0,
    oldestDate: stats?.oldestDate ?? null,
    newestDate: stats?.newestDate ?? null,
    genderByYear,
  }
})
