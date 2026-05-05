import { initDB, failoverToTurso, useDB } from '../utils/db'

export default defineEventHandler(async (event) => {
  await initDB(event)
})
