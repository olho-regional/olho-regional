import { eq } from 'drizzle-orm'
import { noticias, jornais } from '../../database/schema'

export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const id = getRouterParam(event, 'id')

  if (!id) {
    throw createError({ statusCode: 400, message: 'Missing id' })
  }

  const result = await db
    .select({
      id: noticias.id,
      title: noticias.title,
      text: noticias.text,
      date: noticias.date,
      author: noticias.author,
      url: noticias.url,
      archive_url: noticias.archive_url,
      jornal_nome: jornais.nome,
    })
    .from(noticias)
    .leftJoin(jornais, eq(noticias.jornal_id, jornais.id))
    .where(eq(noticias.id, id))
    .get()

  if (!result) {
    throw createError({ statusCode: 404, message: 'Article not found' })
  }

  return result
})
