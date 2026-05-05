import { sql } from 'drizzle-orm'

/**
 * GET /api/noticias/entities
 *
 * Returns top entities and (optionally) co-occurrence network for the current filter.
 *
 * Query params: same filters as /api/noticias (search, distrito, jornal, author, year_from, year_to)
 *   + entity_type: "PER" | "ORG" | undefined (both)
 *   + network: "1" to include co-occurrence edges (only computed if filtered results < 10k)
 *
 * Returns:
 *   topEntities: { name, entity_type, count }[]   — top 10 per type
 *   network?: { nodes: { id, name, entity_type, count }[], edges: { source, target, weight }[] }
 *   total: number  — number of articles in the filtered set
 */
export default defineEventHandler(async (event) => {
  const db = useDB(event)
  const query = getQuery(event)

  const search = query.search as string | undefined
  const distrito = query.distrito as string | undefined
  const jornal = query.jornal as string | undefined
  const author = query.author as string | undefined
  const yearFrom = query.year_from as string | undefined
  const yearTo = query.year_to as string | undefined
  const entityType = query.entity_type as string | undefined
  const wantNetwork = query.network === '1'
  const forceNetwork = query.force_network === '1'

  // If no filters active and no search, use a fast pre-aggregated path
  const hasFilters = search || distrito || jornal || author ||
    (yearFrom && parseInt(yearFrom) > 1996) || (yearTo && parseInt(yearTo) < 2026)

  if (!hasFilters) {
    // Fast path: query entities table directly (no CTE needed)
    const entityTypeFilter = entityType ? sql`WHERE e.entity_type = ${entityType}` : sql``
    const topEntities = await db.all<{ name: string; entity_type: string; count: number }>(sql`
      SELECT e.name, e.entity_type, count(*) as count
      FROM noticias_entities ne
      JOIN entities e ON e.id = ne.entity_id
      ${entityTypeFilter}
      GROUP BY e.id
      ORDER BY count DESC
      LIMIT 20
    `)
    const total = (await db.get<{ total: number }>(sql`SELECT count(*) as total FROM noticias`))?.total ?? 0
    return { topEntities, network: undefined, total }
  }

  // Build the set of matching noticia IDs via a CTE
  const filterClauses: ReturnType<typeof sql>[] = []
  if (jornal) filterClauses.push(sql`j.nome = ${jornal}`)
  if (author) filterClauses.push(sql`n.author = ${author}`)
  if (yearFrom) filterClauses.push(sql`n.date >= ${`${yearFrom}-01-01`}`)
  if (yearTo) filterClauses.push(sql`n.date <= ${`${yearTo}-12-31`}`)

  const distritoJoin = distrito
    ? sql`JOIN jornais_distritos jd ON jd.jornal_id = j.id`
    : sql``
  if (distrito) filterClauses.push(sql`jd.distrito_codigoine = ${distrito}`)

  const entityTypeFilter = entityType ? sql`AND e.entity_type = ${entityType}` : sql``

  // Use FTS when searching
  let matchedIdsCte: ReturnType<typeof sql>

  if (search) {
    const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
    const extraWhere = filterClauses.length > 0
      ? sql`AND ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    matchedIdsCte = sql`
      matched_ids AS (
        SELECT DISTINCT n.id
        FROM noticias_fts
        JOIN noticias n ON n.rowid = noticias_fts.rowid
        LEFT JOIN jornais j ON n.jornal_id = j.id
        ${distritoJoin}
        WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
      )
    `
  } else {
    const jJoin = sql`LEFT JOIN jornais j ON n.jornal_id = j.id`
    const whereClause = filterClauses.length > 0
      ? sql`WHERE ${sql.join(filterClauses, sql` AND `)}`
      : sql``

    matchedIdsCte = sql`
      matched_ids AS (
        SELECT DISTINCT n.id
        FROM noticias n
        ${jJoin}
        ${distritoJoin}
        ${whereClause}
      )
    `
  }

  // Count total + top entities in one query (single CTE evaluation)
  // Cap the CTE at 10k IDs for performance — entities are approximate for large result sets
  type CombinedRow = { name: string | null; entity_type: string | null; count: number; is_total: number }

  // Get total count separately (fast — just counting matched IDs)
  const totalResult = await db.get<{ total: number }>(sql`
    WITH ${matchedIdsCte}
    SELECT count(*) as total FROM matched_ids
  `)
  const total = totalResult?.total ?? 0

  // For entities, limit the CTE to 10k articles max (good enough for ranking)
  const limitedMatchedIdsCte = search
    ? (() => {
        const ftsMatch = search.split(/\s+/).filter(Boolean).map(w => `"${w.replace(/"/g, '')}"`).join(' ')
        const extraWhere = filterClauses.length > 0
          ? sql`AND ${sql.join(filterClauses, sql` AND `)}`
          : sql``
        return sql`
          matched_ids AS (
            SELECT n.id
            FROM noticias_fts
            JOIN noticias n ON n.rowid = noticias_fts.rowid
            LEFT JOIN jornais j ON n.jornal_id = j.id
            ${distritoJoin}
            WHERE noticias_fts MATCH ${ftsMatch} ${extraWhere}
            LIMIT 10000
          )
        `
      })()
    : (() => {
        const jJoin = sql`LEFT JOIN jornais j ON n.jornal_id = j.id`
        const whereClause = filterClauses.length > 0
          ? sql`WHERE ${sql.join(filterClauses, sql` AND `)}`
          : sql``
        return sql`
          matched_ids AS (
            SELECT n.id
            FROM noticias n
            ${jJoin}
            ${distritoJoin}
            ${whereClause}
            LIMIT 10000
          )
        `
      })()

  const topEntities = await db.all<{ name: string; entity_type: string; count: number }>(sql`
    WITH ${limitedMatchedIdsCte}
    SELECT e.name, e.entity_type, count(*) as count
    FROM noticias_entities ne
    JOIN matched_ids m ON m.id = ne.noticia_id
    JOIN entities e ON e.id = ne.entity_id
    WHERE 1=1 ${entityTypeFilter}
    GROUP BY e.id
    ORDER BY count DESC
    LIMIT 20
  `)

  // Network: only if requested AND total <= 5k (or forced)
  let network: { nodes: { id: number; name: string; entity_type: string; count: number }[]; edges: { source: number; target: number; weight: number }[] } | undefined

  if (wantNetwork && (total <= 5_000 || forceNetwork) && total > 0) {
    // Get top entities to use as nodes (limit to top 30 for readability)
    type NodeRow = { id: number; name: string; entity_type: string; count: number }
    const topNodes: NodeRow[] = await db.all(sql`
      WITH ${limitedMatchedIdsCte}
      SELECT e.id, e.name, e.entity_type, count(*) as count
      FROM noticias_entities ne
      JOIN matched_ids m ON m.id = ne.noticia_id
      JOIN entities e ON e.id = ne.entity_id
      WHERE 1=1 ${entityTypeFilter}
      GROUP BY e.id
      ORDER BY count DESC
      LIMIT 30
    `)

    if (topNodes.length > 1) {
      const nodeIds = topNodes.map(n => n.id)

      // Co-occurrence: two entities appearing in the same article
      type EdgeRow = { source: number; target: number; weight: number }
      const edges: EdgeRow[] = await db.all(sql`
        WITH ${limitedMatchedIdsCte},
        top_entities(eid) AS (VALUES ${sql.join(nodeIds.map(id => sql`(${id})`), sql`,`)})
        SELECT ne1.entity_id as source, ne2.entity_id as target, count(*) as weight
        FROM noticias_entities ne1
        JOIN noticias_entities ne2 ON ne1.noticia_id = ne2.noticia_id AND ne1.entity_id < ne2.entity_id
        JOIN matched_ids m ON m.id = ne1.noticia_id
        JOIN top_entities t1 ON t1.eid = ne1.entity_id
        JOIN top_entities t2 ON t2.eid = ne2.entity_id
        GROUP BY ne1.entity_id, ne2.entity_id
        HAVING weight >= 2
        ORDER BY weight DESC
        LIMIT 100
      `)

      // Only include nodes that have at least one edge
      const connectedIds = new Set<number>()
      for (const e of edges) {
        connectedIds.add(e.source)
        connectedIds.add(e.target)
      }
      const filteredNodes = topNodes.filter(n => connectedIds.has(n.id))

      if (filteredNodes.length > 1 && edges.length > 0) {
        network = { nodes: filteredNodes, edges }
      }
    }
  }

  return { topEntities, network, total }
})
