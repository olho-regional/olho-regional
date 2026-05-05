import { sqliteTable, integer, text, real, primaryKey, index } from 'drizzle-orm/sqlite-core'

export const distritos = sqliteTable('distritos', {
  codigoine: text('codigoine').primaryKey(),
  nome: text('nome').notNull(),
  regiao: text('regiao').notNull(),
})

export type Distrito = typeof distritos.$inferSelect

export const municipios = sqliteTable('municipios', {
  codigoine: text('codigoine').primaryKey(),
  nome: text('nome').notNull(),
  distritoCodigoine: text('distrito_codigoine').notNull().references(() => distritos.codigoine),
})

export type Municipio = typeof municipios.$inferSelect

export const jornais = sqliteTable('jornais', {
  id: integer('id').primaryKey(),
  nome: text('nome').notNull(),
  proprietario: text('proprietario'),
  estado: text('estado'),
  suporte: text('suporte'),
  data_inscricao: text('data_inscricao'),
  url: text('url'),
  periodicidade: text('periodicidade'),
  data_situacao: text('data_situacao'),
  erc_url: text('erc_url'),
})

export type Jornal = typeof jornais.$inferSelect
export type NewJornal = typeof jornais.$inferInsert

export const jornaisDistritos = sqliteTable('jornais_distritos', {
  jornalId: integer('jornal_id').notNull().references(() => jornais.id),
  distritoCodigoine: text('distrito_codigoine').notNull().references(() => distritos.codigoine),
}, (table) => ({
  pk: primaryKey({ columns: [table.jornalId, table.distritoCodigoine] }),
}))

export const jornaisMunicipios = sqliteTable('jornais_municipios', {
  jornalId: integer('jornal_id').notNull().references(() => jornais.id),
  municipioCodigoine: text('municipio_codigoine').notNull().references(() => municipios.codigoine),
}, (table) => ({
  pk: primaryKey({ columns: [table.jornalId, table.municipioCodigoine] }),
}))

export const noticias = sqliteTable('noticias', {
  id: text('id').primaryKey(),
  url: text('url').notNull(),
  title: text('title'),
  text: text('text'),
  date: text('date'),
  author: text('author'),
  archive_url: text('archive_url'),
  jornal_id: integer('jornal_id').references(() => jornais.id),
})

export type Noticia = typeof noticias.$inferSelect
export type NewNoticia = typeof noticias.$inferInsert

export const labels = sqliteTable('labels', {
  id: integer('id').primaryKey(),
  type: text('type').notNull(),
  name: text('name').notNull(),
})

export type Label = typeof labels.$inferSelect

export const noticiasLabels = sqliteTable('noticias_labels', {
  noticiaId: text('noticia_id').notNull().references(() => noticias.id),
  labelId: integer('label_id').notNull().references(() => labels.id),
  score: real('score'),
}, (table) => ({
  pk: primaryKey({ columns: [table.noticiaId, table.labelId] }),
  labelIdx: index('idx_noticias_labels_label').on(table.labelId),
}))

export type NoticiaLabel = typeof noticiasLabels.$inferSelect

export const quotes = sqliteTable('quotes', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  noticiaId: text('noticia_id').notNull().references(() => noticias.id),
  speaker: text('speaker').notNull(),
  gender: text('gender').notNull(),
}, (table) => ({
  noticiaIdx: index('idx_quotes_noticia').on(table.noticiaId),
  genderIdx: index('idx_quotes_gender').on(table.gender),
}))

export type Quote = typeof quotes.$inferSelect

export const entities = sqliteTable('entities', {
  id: integer('id').primaryKey(),
  name: text('name').notNull(),
  entityType: text('entity_type').notNull(),
}, (table) => ({
  typeIdx: index('idx_entities_type').on(table.entityType),
}))

export type Entity = typeof entities.$inferSelect

export const noticiasEntities = sqliteTable('noticias_entities', {
  noticiaId: text('noticia_id').notNull().references(() => noticias.id),
  entityId: integer('entity_id').notNull().references(() => entities.id),
}, (table) => ({
  pk: primaryKey({ columns: [table.noticiaId, table.entityId] }),
  entityIdx: index('idx_noticias_entities_entity').on(table.entityId),
}))

export type NoticiaEntity = typeof noticiasEntities.$inferSelect
