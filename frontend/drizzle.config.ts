import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  out: './drizzle',
  schema: './server/database/schema.ts',
  dialect: 'sqlite',
})
