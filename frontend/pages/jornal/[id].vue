<template>
  <v-container fluid>
    <!-- Back button -->
    <v-btn
      variant="text"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
      @click="$router.push('/jornais')"
    >
      Voltar
    </v-btn>

    <v-row align="start">
      <v-col cols="12" lg="5" xl="4">
        <!-- Loading -->
        <v-skeleton-loader v-if="status === 'pending'" type="card" />

        <!-- Error -->
        <v-alert v-else-if="error" type="error">
          Jornal não encontrado.
        </v-alert>

        <!-- Detail card -->
        <v-card v-else-if="jornal" ref="cardRef" elevation="4">
          <div class="d-flex align-center pa-6 pb-2">
            <v-avatar v-if="logoUrl" size="56" rounded="lg" class="mr-4">
              <v-img :src="logoUrl" :alt="jornal.nome" />
            </v-avatar>
            <v-avatar v-else size="56" rounded="lg" color="grey-lighten-3" class="mr-4">
              <v-icon size="28" color="grey">mdi-newspaper</v-icon>
            </v-avatar>
            <v-card-title class="text-h5 pa-0">
              {{ jornal.nome }}
            </v-card-title>
          </div>

          <!-- Stats row -->
          <v-card-text class="pa-6 pb-2">
            <v-row>
              <v-col cols="4" class="text-center">
                <div class="text-h5 font-weight-bold text-primary">{{ jornal.totalArticles?.toLocaleString() ?? 0 }}</div>
                <div class="text-caption text-medium-emphasis">Artigos</div>
              </v-col>
              <v-col cols="4" class="text-center">
                <div class="text-h6 font-weight-medium">{{ jornal.oldestDate ?? '—' }}</div>
                <div class="text-caption text-medium-emphasis">Mais antigo</div>
              </v-col>
              <v-col cols="4" class="text-center">
                <div class="text-h6 font-weight-medium">{{ jornal.newestDate ?? '—' }}</div>
                <div class="text-caption text-medium-emphasis">Mais recente</div>
              </v-col>
            </v-row>
            <v-row v-if="genderTotals.total > 0" class="mt-2">
              <v-col cols="6" class="text-center">
                <div class="text-h6 font-weight-medium" style="color: #1565C0">{{ genderTotals.mPct }}%</div>
                <div class="text-caption text-medium-emphasis">Masculino</div>
                <v-tooltip activator="parent" location="bottom" max-width="260">{{ genderTotals.mPct }}% das citações são atribuídas a vozes masculinas ({{ genderTotals.mCount.toLocaleString() }} de {{ genderTotals.total.toLocaleString() }})</v-tooltip>
              </v-col>
              <v-col cols="6" class="text-center">
                <div class="text-h6 font-weight-medium" style="color: #C62828">{{ genderTotals.fPct }}%</div>
                <div class="text-caption text-medium-emphasis">Feminino</div>
                <v-tooltip activator="parent" location="bottom" max-width="260">{{ genderTotals.fPct }}% das citações são atribuídas a vozes femininas ({{ genderTotals.fCount.toLocaleString() }} de {{ genderTotals.total.toLocaleString() }})</v-tooltip>
              </v-col>
            </v-row>
          </v-card-text>

          <v-divider class="mx-6" />

          <v-card-text class="pa-6 pt-0">
            <v-list lines="two">
              <v-list-item v-if="jornal.distritos?.length" prepend-icon="mdi-map-marker">
                <v-list-item-title>Distrito(s)</v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip
                    v-for="d in jornal.distritos"
                    :key="d.codigoine"
                    size="small"
                    variant="tonal"
                    color="primary"
                    class="mr-1 mb-1"
                  >
                    {{ d.nome }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.municipios?.length" prepend-icon="mdi-city">
                <v-list-item-title>Município(s)</v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip
                    v-for="m in jornal.municipios"
                    :key="m.codigoine"
                    size="small"
                    variant="tonal"
                    class="mr-1 mb-1"
                  >
                    {{ m.nome }}
                  </v-chip>
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.url" prepend-icon="mdi-web">
                <v-list-item-title>Website</v-list-item-title>
                <v-list-item-subtitle>
                  <a
                    :href="normalizeUrl(jornal.url)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {{ jornal.url }}
                  </a>
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.erc_url" prepend-icon="mdi-certificate">
                <v-list-item-title>Registo ERC</v-list-item-title>
                <v-list-item-subtitle>
                  <a
                    :href="jornal.erc_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Ver no Portal da Transparência
                  </a>
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.estado" prepend-icon="mdi-information">
                <v-list-item-title>Estado</v-list-item-title>
                <v-list-item-subtitle>{{ jornal.estado }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.suporte" prepend-icon="mdi-newspaper-variant">
                <v-list-item-title>Suporte</v-list-item-title>
                <v-list-item-subtitle>{{ jornal.suporte }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.periodicidade" prepend-icon="mdi-calendar-clock">
                <v-list-item-title>Periodicidade</v-list-item-title>
                <v-list-item-subtitle>{{ jornal.periodicidade }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.data_inscricao" prepend-icon="mdi-calendar-start">
                <v-list-item-title>Data de inscrição</v-list-item-title>
                <v-list-item-subtitle>{{ jornal.data_inscricao }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="jornal.proprietario" prepend-icon="mdi-domain">
                <v-list-item-title>Proprietário</v-list-item-title>
                <v-list-item-subtitle>{{ jornal.proprietario }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>

          <v-card-actions class="pa-6 pt-0">
            <v-btn
              v-if="jornal.url"
              color="primary"
              variant="elevated"
              :href="normalizeUrl(jornal.url)"
              target="_blank"
              prepend-icon="mdi-open-in-new"
            >
              Visitar website
            </v-btn>
            <v-btn
              v-if="jornal.url"
              color="secondary"
              variant="outlined"
              :href="`https://arquivo.pt/page/search?q=${encodeURIComponent(jornal.url)}`"
              target="_blank"
              prepend-icon="mdi-archive"
            >
              Ver no Arquivo.pt
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Articles list (right column on wide screens) -->
      <v-col cols="12" lg="7" xl="8">
        <v-card v-if="jornal && jornal.totalArticles > 0" elevation="2">
          <v-card-title>
            Notícias
            <span class="text-body-2 text-medium-emphasis ml-2">({{ jornal.totalArticles?.toLocaleString() }})</span>
          </v-card-title>
          <v-data-table
            :headers="articleHeaders"
            :items="articles?.items ?? []"
            :items-per-page="articlesPerPage"
            :items-per-page-options="[10, 20, 50]"
            :loading="articlesStatus === 'pending'"
            density="compact"
            class="elevation-0"
            @update:items-per-page="(v: number) => { articlesPerPage = v; articlesPage = 1 }"
            @click:row="(_e: any, { item }: any) => openArticle(item)"
          >
            <template #item.title="{ item }">
              <span>{{ item.title || '(sem título)' }}</span>
            </template>
            <template #item.date="{ item }">
              {{ item.date ?? '—' }}
            </template>
            <template #item.author="{ item }">
              {{ item.author || '—' }}
            </template>
          </v-data-table>
          <v-row v-if="(articles?.totalPages ?? 0) > 1" justify="center" class="py-4">
            <v-pagination
              v-model="articlesPage"
              :length="articles?.totalPages ?? 0"
              :total-visible="7"
              rounded
              size="small"
            />
          </v-row>
        </v-card>


      </v-col>
    </v-row>

    <!-- Article detail modal -->
    <v-dialog v-model="articleDialog" max-width="800" scrollable>
      <v-card v-if="articleDetail">
        <v-card-title class="text-h6 pa-6 pb-2">{{ articleDetail.title || '(sem título)' }}</v-card-title>
        <v-card-text class="px-6 pt-0 pb-2">
          <div class="d-flex flex-wrap ga-3 mb-4">
            <v-chip v-if="articleDetail.jornal_nome" size="small" variant="tonal" color="primary" prepend-icon="mdi-newspaper">
              {{ articleDetail.jornal_nome }}
            </v-chip>
            <v-chip v-if="articleDetail.jornal_regiao" size="small" variant="tonal" prepend-icon="mdi-map-marker">
              {{ articleDetail.jornal_regiao }}
            </v-chip>
            <v-chip v-if="articleDetail.date" size="small" variant="tonal" prepend-icon="mdi-calendar">
              {{ articleDetail.date }}
            </v-chip>
            <v-chip v-if="articleDetail.author" size="small" variant="tonal" prepend-icon="mdi-account">
              {{ articleDetail.author }}
            </v-chip>
          </div>
          <v-divider class="mb-4" />
          <div class="article-text">
            {{ articleDetail.text || '(sem conteúdo)' }}
          </div>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4 d-flex flex-wrap ga-2">
          <v-btn
            v-if="articleDetail.archive_url?.includes('arquivo.pt')"
            :href="articleDetail.archive_url"
            target="_blank"
            variant="tonal"
            size="small"
            color="primary"
            prepend-icon="mdi-archive"
          >
            Ver no Arquivo.pt
          </v-btn>
          <v-btn
            v-if="!articleDetail.archive_url?.includes('arquivo.pt')"
            :href="`https://arquivo.pt/page/search?q=${encodeURIComponent(articleDetail.url)}`"
            target="_blank"
            variant="tonal"
            size="small"
            color="primary"
            prepend-icon="mdi-magnify"
          >
            Procurar no Arquivo.pt
          </v-btn>
          <v-btn
            v-if="articleDetail.url && !articleDetail.archive_url?.includes('arquivo.pt')"
            :href="`https://arquivo.pt/services/archivepagenow?url=${encodeURIComponent(articleDetail.url)}`"
            target="_blank"
            variant="tonal"
            size="small"
            color="primary"
            prepend-icon="mdi-archive-arrow-up"
          >
            Arquivar Agora
          </v-btn>
          <v-btn
            v-if="articleDetail.url?.includes('web.archive.org') || articleDetail.archive_url?.includes('web.archive.org')"
            :href="articleDetail.url?.includes('web.archive.org') ? articleDetail.url : articleDetail.archive_url!"
            target="_blank"
            variant="tonal"
            size="small"
            prepend-icon="mdi-web"
          >
            Ver Wayback
          </v-btn>
          <v-btn
            v-if="articleDetail.url && !articleDetail.url.includes('arquivo.pt') && !articleDetail.url.includes('web.archive.org')"
            :href="articleDetail.url"
            target="_blank"
            variant="tonal"
            size="small"
            prepend-icon="mdi-open-in-new"
          >
            Ver original
          </v-btn>
          <v-spacer />
          <v-btn variant="text" @click="articleDialog = false">Fechar</v-btn>
        </v-card-actions>
      </v-card>
      <v-card v-else>
        <v-card-text class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { getLogoUrl } from '~/composables/useLogos'

const route = useRoute()
const jornalId = route.params.id as string
const { data: jornal, status, error } = useJornal(jornalId)

// Articles pagination
const articlesPage = ref(1)
const articlesPerPage = ref(20)
const articlesParams = computed(() => ({
  page: articlesPage.value,
  per_page: articlesPerPage.value,
}))
const { data: articles, status: articlesStatus } = useJornalNoticias(jornalId, articlesParams)

// Article detail modal (fetches full text via /api/noticias/[id])
const articleDialog = ref(false)
const articleDetail = ref<{
  id: string
  title: string | null
  text: string | null
  date: string | null
  author: string | null
  url: string
  archive_url: string | null
  jornal_nome: string | null
  jornal_regiao: string | null
} | null>(null)

async function openArticle(item: { id: string }) {
  articleDetail.value = null
  articleDialog.value = true
  const result = await $fetch(`/api/noticias/${item.id}`)
  articleDetail.value = result as typeof articleDetail.value
}

const articleHeaders = [
  { title: 'Título', key: 'title', sortable: false },
  { title: 'Data', key: 'date', width: '120px', sortable: false },
  { title: 'Autor', key: 'author', width: '150px', sortable: false },
]

const logoUrl = computed(() => {
  if (!jornal.value?.url) return null
  const domain = jornal.value.url
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '')
  return getLogoUrl(domain)
})

function normalizeUrl(url: string): string {
  if (!url) return '#'
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return `https://${url}`
}

// --- Gender balance ---
const genderTotals = computed(() => {
  const data = jornal.value?.genderByYear ?? []
  let m = 0, f = 0
  for (const r of data) {
    if (r.gender === 'M') m += r.count
    else if (r.gender === 'F') f += r.count
  }
  const total = m + f
  return {
    total,
    mCount: m,
    fCount: f,
    mPct: total ? Math.round((m / total) * 1000) / 10 : 0,
    fPct: total ? Math.round((f / total) * 1000) / 10 : 0,
  }
})

// GSAP entrance animation
const { $gsap } = useNuxtApp()
const cardRef = ref<HTMLElement | null>(null)

onMounted(() => {
  if ($gsap && cardRef.value) {
    $gsap.from(cardRef.value, {
      opacity: 0,
      y: 20,
      duration: 0.5,
      ease: 'power2.out',
    })
  }
})
</script>
