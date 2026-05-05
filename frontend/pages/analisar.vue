<template>
  <v-container>
    <h1 class="text-h4 mb-6">Analisar Notícias</h1>

    <!-- Search & Filters -->
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="searchInput"
          label="Pesquisar notícias..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          @keyup.enter="triggerSearch"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-autocomplete
          v-model="selectedDistrito"
          :items="distritosOptions"
          item-title="nome"
          item-value="codigoine"
          label="Distrito"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-autocomplete
          v-model="selectedJornal"
          :items="jornalOptions"
          :loading="jornalOptionsLoading"
          item-title="name"
          item-value="name"
          label="Jornal"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          @update:search="onJornalSearch"
          no-filter
          :no-data-text="jornalSearchQuery ? 'Sem resultados' : 'Escreve para procurar'"
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-autocomplete
          v-model="selectedAuthor"
          :items="authorOptions"
          :loading="authorOptionsLoading"
          item-title="name"
          item-value="name"
          label="Autor"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          @update:search="onAuthorSearch"
          no-filter
          :no-data-text="authorSearchQuery ? 'Sem resultados' : 'Escreve para procurar'"
        />
      </v-col>
    </v-row>

    <!-- Time range -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-range-slider
          v-model="yearRange"
          :min="1996"
          :max="2026"
          :step="1"
          label="Período"
          thumb-label="always"
          color="primary"
          hide-details
        />
      </v-col>
    </v-row>

    <!-- Results summary -->
    <v-row class="mb-4">
      <v-col class="d-flex align-center flex-wrap ga-2">
        <v-chip variant="outlined" class="mr-1">
          {{ yearRange[0] }}–{{ yearRange[1] }}
        </v-chip>
        <v-chip v-if="selectedDistrito" variant="outlined" closable @click:close="selectedDistrito = null">
          {{ selectedDistritoName }}
        </v-chip>
        <v-chip v-if="selectedJornal" variant="outlined" closable @click:close="selectedJornal = null">
          {{ selectedJornal }}
        </v-chip>
        <v-chip v-if="selectedAuthor" variant="outlined" closable @click:close="selectedAuthor = null">
          {{ selectedAuthor }}
        </v-chip>
        <v-btn
          v-if="hasAnyFilter"
          variant="text"
          size="small"
          prepend-icon="mdi-filter-off"
          class="text-medium-emphasis"
          @click="clearAllFilters"
        >
          Limpar filtros
        </v-btn>
        <v-spacer />
        <span class="text-body-2 text-medium-emphasis">
          {{ data?.total?.toLocaleString() ?? 0 }} resultados encontrados
          <template v-if="queryTime !== null">em {{ queryTime }}s</template>
        </span>
        <v-btn
          icon
          size="small"
          variant="text"
          class="ml-1"
          @click="shareUrl"
        >
          <v-icon size="18">mdi-share-variant</v-icon>
          <v-tooltip activator="parent" location="top">Copiar link de partilha</v-tooltip>
        </v-btn>
      </v-col>
    </v-row>
  </v-container>

  <v-container fluid>
    <!-- Main content: Table (left) + Map (center) + Charts (right) on desktop -->
    <v-row class="mb-4" align="start">
      <!-- Results Table -->
      <v-col cols="12" :lg="selectedDistrito ? 7 : 5">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Resultados
            <v-spacer />
            <v-menu :close-on-content-click="false">
              <template #activator="{ props: menuProps }">
                <v-btn icon="mdi-table-cog" variant="text" size="small" v-bind="menuProps" />
              </template>
              <v-card min-width="220">
                <v-card-text class="py-2">
                  <div class="text-caption text-medium-emphasis mb-1">Colunas visíveis</div>
                  <v-checkbox
                    v-for="col in allTableColumns"
                    :key="col.key"
                    v-model="visibleColumnKeys"
                    :label="col.title"
                    :value="col.key"
                    density="compact"
                    hide-details
                    class="my-0"
                  />
                </v-card-text>
              </v-card>
            </v-menu>
          </v-card-title>

          <v-data-table
            :headers="tableHeaders"
            :items="data?.items ?? []"
            :items-per-page="perPage"
            :items-per-page-options="[10, 20, 50, 100]"
            @update:items-per-page="(v: number) => { perPage = v; currentPage = 1 }"
            :loading="status === 'pending'"
            density="compact"
            class="elevation-0 cursor-pointer table-scroll"
            style="max-height: 740px; overflow-y: auto"
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

          <!-- Pagination -->
          <v-row v-if="(data?.totalPages ?? 0) > 1" justify="center" class="py-4">
            <v-pagination
              v-model="currentPage"
              :length="data?.totalPages ?? 0"
              :total-visible="7"
              rounded
              size="small"
            />
          </v-row>
        </v-card>
      </v-col>

      <!-- Map (center column) -->
      <v-col v-if="!selectedDistrito" cols="12" lg="3">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Mapa
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Distribuição geográfica das notícias por região. O mapa mostra a intensidade de cobertura noticiosa em cada distrito.</v-tooltip>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div v-if="facetsStatus === 'pending' && !distritoCounts.length" class="text-center py-4">
              <v-progress-circular indeterminate size="24" />
            </div>
            <template v-else>
            <div class="density-map">
              <PortugalMap :district-counts="districtCountsMap" count-label="notícias" />
            </div>
            <div class="mt-4" style="max-height: 200px; overflow-y: auto">
              <div
                v-for="r in distritoCounts"
                :key="r.name"
                class="d-flex justify-space-between text-caption py-1"
                style="border-bottom: 1px solid rgba(0,0,0,0.06)"
              >
                <span>{{ r.name }}</span>
                <span class="text-medium-emphasis">{{ r.count.toLocaleString() }}</span>
              </div>
            </div>
            </template>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Charts (right column) -->
      <v-col cols="12" :lg="selectedDistrito ? 5 : 4">
        <v-card class="mb-4" elevation="2">
          <v-card-title class="d-flex align-center">
            Resultados por Ano
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Número de notícias publicadas por ano. No modo %, os valores são normalizados pelo total de notícias disponíveis nesse ano.</v-tooltip>
            </v-btn>
            <v-spacer />
            <v-btn-toggle v-model="timelineMode" density="compact" mandatory variant="outlined" color="primary">
              <v-btn value="absolute" size="x-small">
                <v-tooltip activator="parent" location="top">Mostrar números absolutos</v-tooltip>
                Nº
              </v-btn>
              <v-btn value="relative" size="x-small">
                <v-tooltip activator="parent" location="top">Mostrar percentagem relativa ao total de notícias daquele ano</v-tooltip>
                %
              </v-btn>
            </v-btn-toggle>
          </v-card-title>
          <v-card-text style="max-height: 435px; overflow-y: auto">
            <ClientOnly>
              <VChart
                v-if="timeline.length"
                :option="timelineChartOption"
                :style="{ height: Math.max(200, timeline.length * 24) + 'px' }"
                renderer="svg"
                autoresize
              />
            </ClientOnly>
          </v-card-text>
        </v-card>

        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Categorias
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Classificação temática das notícias por tópico. Cada notícia pode ter uma ou mais categorias atribuídas automaticamente.</v-tooltip>
            </v-btn>
          </v-card-title>
          <v-card-text style="max-height: 300px; overflow-y: auto">
            <div v-if="facetsStatus === 'pending' && !visibleCategories.length" class="text-center py-4">
              <v-progress-circular indeterminate size="24" />
            </div>
            <ClientOnly>
              <VChart
                v-if="visibleCategories.length"
                :option="categoriesChartOption"
                :style="{ height: Math.max(200, visibleCategories.length * 28) + 'px' }"
                renderer="svg"
                autoresize
              />
            </ClientOnly>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Entities + Network + Por Jornal -->
    <v-row class="mb-4" align="start">
      <v-col cols="12" md="4">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Entidades Mais Mencionadas
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Pessoas e organizações mais mencionadas nas notícias, extraídas automaticamente por reconhecimento de entidades (NER).</v-tooltip>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-btn-toggle v-model="entityTypeFilter" density="compact" mandatory variant="outlined" color="primary" class="mb-2">
              <v-btn value="ALL" size="x-small">Todos</v-btn>
              <v-btn value="PER" size="x-small">Pessoas</v-btn>
              <v-btn value="ORG" size="x-small">Organizações</v-btn>
            </v-btn-toggle>
            <v-list v-if="entitiesData?.topEntities?.length" density="compact" class="pa-0" style="max-height: 320px; overflow-y: auto">
              <v-list-item
                v-for="(e, i) in entitiesData.topEntities"
                :key="i"
                class="px-0"
                style="min-height: 28px"
              >
                <template #prepend>
                  <v-icon size="14" :color="e.entity_type === 'PER' ? '#1565C0' : '#E65100'" class="mr-2">
                    {{ e.entity_type === 'PER' ? 'mdi-account' : 'mdi-domain' }}
                  </v-icon>
                </template>
                <v-list-item-title class="text-caption">{{ e.name }}</v-list-item-title>
                <template #append>
                  <span class="text-caption text-medium-emphasis">{{ e.count.toLocaleString() }}</span>
                </template>
              </v-list-item>
            </v-list>
            <div v-else-if="entitiesStatus === 'pending'" class="text-center py-4">
              <v-progress-circular indeterminate size="24" />
            </div>
            <div v-else class="text-medium-emphasis text-center py-4 text-body-2">Sem dados de entidades</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-if="entitiesData?.network || forceNetworkData" cols="12" md="4">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Rede de Co-ocorrência
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Grafo de entidades que co-ocorrem nas mesmas notícias. Ligações mais grossas indicam mais artigos em comum.</v-tooltip>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <ClientOnly>
              <VChart
                :key="JSON.stringify(entitiesParams)"
                :option="networkChartOption"
                style="height: 360px"
                renderer="canvas"
                autoresize
              />
            </ClientOnly>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-else-if="entitiesStatus === 'pending'" cols="12" md="4">
        <v-card elevation="2">
          <v-card-text class="d-flex align-center justify-center" style="height: 200px">
            <v-progress-circular indeterminate color="primary" />
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-else-if="(entitiesData?.total ?? 0) > 5000" cols="12" md="4">
        <v-card elevation="2">
          <v-card-text class="text-center py-8 text-medium-emphasis">
            <v-icon size="48" class="mb-2">mdi-graph-outline</v-icon>
            <div>Rede de co-ocorrência disponível com menos de 5.000 resultados</div>
            <div class="text-caption mb-3">(atualmente {{ (entitiesData?.total ?? 0).toLocaleString() }} resultados)</div>
            <v-btn
              variant="outlined"
              size="small"
              color="primary"
              prepend-icon="mdi-graph"
              :loading="forceNetworkLoading"
              @click="generateNetworkForce"
            >
              Gerar mesmo assim
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col v-if="!selectedJornal" cols="12" md="4">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Por Jornal
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Os jornais com mais notícias nos resultados atuais.</v-tooltip>
            </v-btn>
          </v-card-title>
          <v-card-text style="max-height: 360px; overflow-y: auto">
            <div v-if="facetsStatus === 'pending' && !visibleJornais.length" class="text-center py-4">
              <v-progress-circular indeterminate size="24" />
            </div>
            <ClientOnly>
              <VChart
                v-if="visibleJornais.length"
                :option="jornalChartOption"
                :style="{ height: Math.max(200, visibleJornais.length * 28) + 'px' }"
                renderer="svg"
                autoresize
              />
            </ClientOnly>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Calendar heatmap -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center flex-wrap ga-2">
            Calendário de Publicações
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Mapa de calor com o volume diário de publicações. Seleciona os anos que pretendes visualizar nos chips acima.</v-tooltip>
            </v-btn>
            <v-spacer />
            <v-chip-group
              v-if="allCalendarYears.length"
              v-model="selectedCalendarYears"
              multiple
              selected-class="text-primary"
              column
            >
              <v-chip
                v-for="y in allCalendarYears"
                :key="y"
                :value="y"
                size="small"
                variant="outlined"
                filter
              >
                {{ y }}
              </v-chip>
            </v-chip-group>
          </v-card-title>
          <v-card-text>
            <ClientOnly>
              <VChart
                v-if="calendarYears.length"
                :option="calendarChartOption"
                :style="{ height: Math.max(200, calendarYears.length * 180) + 'px' }"
                renderer="svg"
                autoresize
              />
            </ClientOnly>
            <div v-if="!allCalendarYears.length" class="text-medium-emphasis text-center py-4">Sem dados de datas</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Gender balance over time -->
    <v-row v-if="genderYears.length" class="mb-4">
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="d-flex align-center">
            Equilíbrio de Género nas Citações
            <v-btn icon size="x-small" variant="text" class="ml-1">
              <v-icon size="16">mdi-information-outline</v-icon>
              <v-tooltip activator="parent" location="top" max-width="300">Proporção de citações atribuídas a vozes masculinas e femininas por ano. Baseado em análise automática de género dos nomes citados nas notícias.</v-tooltip>
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div class="d-flex ga-3 mb-3">
              <v-chip variant="tonal" size="small" style="color: #1565C0">
                Masculino: {{ genderGlobal.mPct }}% ({{ genderGlobal.mCount.toLocaleString() }})
              </v-chip>
              <v-chip variant="tonal" size="small" style="color: #C62828">
                Feminino: {{ genderGlobal.fPct }}% ({{ genderGlobal.fCount.toLocaleString() }})
              </v-chip>
              <span class="text-caption text-medium-emphasis align-self-center">{{ genderGlobal.total.toLocaleString() }} citações</span>
            </div>
            <ClientOnly>
              <VChart
                :option="genderChartOption"
                style="height: 320px"
                renderer="svg"
                autoresize
              />
            </ClientOnly>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>

  <!-- Article detail modal -->
  <v-dialog v-model="articleDialog" max-width="800" scrollable>
    <v-card v-if="articleDetail">
      <v-card-title class="text-h6 pa-6 pb-2">{{ articleDetail.title || '(sem título)' }}</v-card-title>
      <v-card-text class="px-6 pt-0 pb-2">
        <div class="d-flex flex-wrap ga-3 mb-4">
          <v-chip v-if="articleDetail.jornal_nome" size="small" variant="tonal" color="primary" prepend-icon="mdi-newspaper">
            {{ articleDetail.jornal_nome }}
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

  <v-snackbar v-model="shareSnackbar" :timeout="2000" color="black">
    Link copiado!
  </v-snackbar>
</template>

<script setup lang="ts">
const route = useRoute()
const router = useRouter()

// --- Search state (initialized from URL query) ---
const searchInput = ref((route.query.search as string) || '')
const debouncedSearch = ref(searchInput.value)
const selectedDistrito = ref<string | null>((route.query.distrito as string) || null)
const selectedJornal = ref<string | null>((route.query.jornal as string) || null)
const selectedAuthor = ref<string | null>((route.query.author as string) || null)
const yearRange = ref([
  parseInt(route.query.year_from as string) || 1996,
  parseInt(route.query.year_to as string) || 2026,
])
const debouncedYearRange = ref([...yearRange.value])
const currentPage = ref(parseInt(route.query.page as string) || 1)
const perPage = ref(parseInt(route.query.per_page as string) || 20)

// Debounce search input and year range (500ms)
let debounceTimer: ReturnType<typeof setTimeout> | null = null
function scheduleDebounce() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debouncedSearch.value = searchInput.value
    debouncedYearRange.value = [...yearRange.value]
    currentPage.value = 1
  }, 500)
}
watch(searchInput, scheduleDebounce)
watch(yearRange, scheduleDebounce, { deep: true })

const queryParams = computed(() => ({
  ...(debouncedSearch.value ? { search: debouncedSearch.value } : {}),
  ...(selectedDistrito.value ? { distrito: selectedDistrito.value } : {}),
  ...(selectedJornal.value ? { jornal: selectedJornal.value } : {}),
  ...(selectedAuthor.value ? { author: selectedAuthor.value } : {}),
  year_from: debouncedYearRange.value[0],
  year_to: debouncedYearRange.value[1],
  page: currentPage.value,
  per_page: perPage.value,
}))

const { data, status } = useNoticias(queryParams)

// --- Entities ---
const entityTypeFilter = ref('ALL')
const entitiesParams = computed(() => ({
  ...(debouncedSearch.value ? { search: debouncedSearch.value } : {}),
  ...(selectedDistrito.value ? { distrito: selectedDistrito.value } : {}),
  ...(selectedJornal.value ? { jornal: selectedJornal.value } : {}),
  ...(selectedAuthor.value ? { author: selectedAuthor.value } : {}),
  year_from: debouncedYearRange.value[0],
  year_to: debouncedYearRange.value[1],
  ...(entityTypeFilter.value !== 'ALL' ? { entity_type: entityTypeFilter.value } : {}),
  network: '1',
}))
interface EntitiesResponse {
  topEntities: { name: string; entity_type: string; count: number }[]
  network?: {
    nodes: { id: number; name: string; entity_type: string; count: number }[]
    edges: { source: number; target: number; weight: number }[]
  }
  total: number
}
const { data: entitiesData, status: entitiesStatus } = useFetch<EntitiesResponse>('/api/noticias/entities', {
  query: entitiesParams,
  watch: [entitiesParams],
  lazy: true,
})

const hasAnyFilter = computed(() =>
  !!debouncedSearch.value || !!selectedDistrito.value || !!selectedJornal.value || !!selectedAuthor.value ||
  yearRange.value[0] !== 1996 || yearRange.value[1] !== 2026
)

function clearAllFilters() {
  searchInput.value = ''
  debouncedSearch.value = ''
  selectedDistrito.value = null
  selectedJornal.value = null
  selectedAuthor.value = null
  yearRange.value = [1996, 2026]
  debouncedYearRange.value = [1996, 2026]
  currentPage.value = 1
}

// Sync search state to URL
watch(queryParams, (params) => {
  const q: Record<string, string> = {}
  if (params.search) q.search = params.search
  if (params.distrito) q.distrito = params.distrito
  if (params.jornal) q.jornal = params.jornal
  if (params.author) q.author = params.author
  if (params.year_from !== 1996) q.year_from = String(params.year_from)
  if (params.year_to !== 2026) q.year_to = String(params.year_to)
  if (params.page > 1) q.page = String(params.page)
  if (params.per_page !== 20) q.per_page = String(params.per_page)
  router.replace({ query: q })
}, { deep: true })

// Track query time
const queryTime = ref<string | null>(null)
let queryStartTime = 0
watch(status, (s) => {
  if (s === 'pending') {
    queryStartTime = performance.now()
    queryTime.value = null
  } else if (s === 'success' && queryStartTime) {
    queryTime.value = ((performance.now() - queryStartTime) / 1000).toFixed(2)
  }
})

function triggerSearch() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debouncedSearch.value = searchInput.value
  debouncedYearRange.value = [...yearRange.value]
  currentPage.value = 1
}

const shareSnackbar = ref(false)
async function shareUrl() {
  const url = window.location.href
  try {
    await navigator.clipboard.writeText(url)
    shareSnackbar.value = true
  } catch {
    // Fallback for insecure contexts
    window.prompt('Copiar link:', url)
  }
}

// --- Static options ---
const distritosQuery = computed(() => ({
  ...(selectedJornal.value ? { jornal: selectedJornal.value } : {}),
}))
const { data: distritosData } = useFetch<{ codigoine: string; nome: string }[]>('/api/distritos', { query: distritosQuery })
const distritosOptions = computed(() => distritosData.value ?? [])
const selectedDistritoName = computed(() =>
  distritosOptions.value.find(d => d.codigoine === selectedDistrito.value)?.nome ?? selectedDistrito.value
)

// --- Autocomplete: Jornal ---
const jornalOptions = ref<{ name: string; count: number }[]>([])
const jornalOptionsLoading = ref(false)
const jornalSearchQuery = ref('')
let jornalDebounce: ReturnType<typeof setTimeout> | null = null
function onJornalSearch(q: string) {
  jornalSearchQuery.value = q || ''
  if (jornalDebounce) clearTimeout(jornalDebounce)
  if (!q || q.length < 1) { jornalOptions.value = []; return }
  jornalOptionsLoading.value = true
  jornalDebounce = setTimeout(async () => {
    try {
      jornalOptions.value = await $fetch<{ name: string; count: number }[]>('/api/noticias/autocomplete', { query: { field: 'jornal', q, ...(selectedDistrito.value ? { distrito: selectedDistrito.value } : {}) } })
    } catch { jornalOptions.value = [] }
    jornalOptionsLoading.value = false
  }, 300)
}

// --- Autocomplete: Author ---
const authorOptions = ref<{ name: string; count: number }[]>([])
const authorOptionsLoading = ref(false)
const authorSearchQuery = ref('')
let authorDebounce: ReturnType<typeof setTimeout> | null = null
function onAuthorSearch(q: string) {
  authorSearchQuery.value = q || ''
  if (authorDebounce) clearTimeout(authorDebounce)
  if (!q || q.length < 2) { authorOptions.value = []; return }
  authorOptionsLoading.value = true
  authorDebounce = setTimeout(async () => {
    try {
      authorOptions.value = await $fetch<{ name: string; count: number }[]>('/api/noticias/autocomplete', { query: { field: 'author', q } })
    } catch { authorOptions.value = [] }
    authorOptionsLoading.value = false
  }, 300)
}

const allTableColumns = [
  { title: 'Título', key: 'title', sortable: false },
  { title: 'Jornal', key: 'jornal_nome', sortable: false },
  { title: 'Data', key: 'date' },

  { title: 'Autor', key: 'author', sortable: false },
  { title: 'URL', key: 'url', sortable: false },
]
const visibleColumnKeys = ref(['title', 'jornal_nome', 'date'])

// Persist column selection in localStorage
if (import.meta.client) {
  const saved = localStorage.getItem('analisar-columns')
  if (saved) {
    try { visibleColumnKeys.value = JSON.parse(saved) } catch {}
  }
  watch(visibleColumnKeys, (v) => {
    localStorage.setItem('analisar-columns', JSON.stringify(v))
  }, { deep: true })
}
const tableHeaders = computed(() =>
  allTableColumns.filter(c => visibleColumnKeys.value.includes(c.key))
)

// --- Timeline from API results ---
const timeline = computed(() => {
  const counts = data.value?.yearCounts ?? []
  return counts.map(c => ({ year: c.year, count: c.count })).reverse()
})
const timelineMode = ref<'absolute' | 'relative'>('absolute')

// Global year totals for normalization (cached endpoint)
const { data: globalAggregations } = useFetch<{ yearCounts: { year: string; count: number }[] }>('/api/noticias/aggregations')
const globalYearMap = computed(() => {
  const m = new Map<string, number>()
  for (const r of globalAggregations.value?.yearCounts ?? []) m.set(r.year, r.count)
  return m
})

// --- Facets: separate fetch for map, categories, por jornal, heatmap, gender ---
const facetsParams = computed(() => ({
  ...(debouncedSearch.value ? { search: debouncedSearch.value } : {}),
  ...(selectedDistrito.value ? { distrito: selectedDistrito.value } : {}),
  ...(selectedJornal.value ? { jornal: selectedJornal.value } : {}),
  ...(selectedAuthor.value ? { author: selectedAuthor.value } : {}),
  year_from: debouncedYearRange.value[0],
  year_to: debouncedYearRange.value[1],
  include: 'labels,jornais,distritos,gender,calendar',
}))
const { data: facetsData, status: facetsStatus } = useFetch<FacetsData>('/api/noticias/facets', {
  query: facetsParams,
  watch: [facetsParams],
})

// --- Categories from facets ---
const categories = computed(() => facetsData.value?.labelCounts ?? [])
const visibleCategories = computed(() => categories.value)

// --- Jornal counts from facets ---
const jornalCounts = computed(() => facetsData.value?.jornalCounts ?? [])
const visibleJornais = computed(() => jornalCounts.value)

// --- Force network generation ---
const forceNetworkLoading = ref(false)
const forceNetworkData = ref<EntitiesResponse['network'] | null>(null)

async function generateNetworkForce() {
  forceNetworkLoading.value = true
  try {
    const params = new URLSearchParams()
    if (debouncedSearch.value) params.set('search', debouncedSearch.value)
    if (selectedDistrito.value) params.set('distrito', selectedDistrito.value)
    if (selectedJornal.value) params.set('jornal', selectedJornal.value)
    if (selectedAuthor.value) params.set('author', selectedAuthor.value)
    params.set('year_from', String(debouncedYearRange.value[0]))
    params.set('year_to', String(debouncedYearRange.value[1]))
    if (entityTypeFilter.value !== 'ALL') params.set('entity_type', entityTypeFilter.value)
    params.set('network', '1')
    params.set('force_network', '1')
    const res = await $fetch<EntitiesResponse>(`/api/noticias/entities?${params.toString()}`)
    forceNetworkData.value = res.network ?? null
  } finally {
    forceNetworkLoading.value = false
  }
}

// Reset force network when params change
watch(entitiesParams, () => { forceNetworkData.value = null })

// --- Region counts from facets ---
const distritoCounts = computed(() => facetsData.value?.distritoCounts ?? [])

// --- ECharts: horizontal bar helper ---
function horizontalBarOption(items: { name: string; count: number }[], color: string) {
  const names = items.map(i => i.name)
  const counts = items.map(i => i.count)
  return {
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' as const } },
    grid: { left: 8, right: 48, top: 4, bottom: 4, containLabel: true },
    xAxis: { type: 'value' as const, show: false },
    yAxis: {
      type: 'category' as const,
      data: names,
      inverse: true,
      axisLabel: { fontSize: 11, width: 90, overflow: 'truncate' as const },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [{
      type: 'bar' as const,
      data: counts,
      itemStyle: { color, borderRadius: [0, 3, 3, 0] },
      barMaxWidth: 16,
      label: {
        show: true,
        position: 'right' as const,
        fontSize: 10,
        formatter: (p: { value: number }) => p.value.toLocaleString(),
      },
    }],
  }
}


// --- ECharts: Timeline chart option ---
const timelineChartOption = computed(() => {
  const items = timeline.value.map(t => ({ name: String(t.year), count: t.count }))
  if (timelineMode.value === 'relative') {
    // Normalize: (filtered count for year) / (global total for year) * 100
    const gm = globalYearMap.value
    const normalized = items.map(i => ({
      name: i.name,
      count: gm.get(i.name) ? Math.round((i.count / gm.get(i.name)!) * 10000) / 100 : 0,
    }))
    const names = normalized.map(i => i.name)
    const pcts = normalized.map(i => i.count)
    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
        formatter: (params: { name: string; value: number; dataIndex: number }[] | { name: string; value: number; dataIndex: number }) => {
          const p = Array.isArray(params) ? params[0]! : params
          const orig = items[p.dataIndex]
          const total = gm.get(p.name) ?? 0
          return `${p.name}: ${p.value}% (${orig?.count?.toLocaleString() ?? 0} de ${total.toLocaleString()})`
        },
      },
      grid: { left: 8, right: 48, top: 4, bottom: 4, containLabel: true },
      xAxis: { type: 'value' as const, show: false },
      yAxis: {
        type: 'category' as const,
        data: names,
        inverse: true,
        axisLabel: { fontSize: 11, width: 90, overflow: 'truncate' as const },
        axisTick: { show: false },
        axisLine: { show: false },
      },
      series: [{
        type: 'bar' as const,
        data: pcts,
        itemStyle: { color: '#1565C0', borderRadius: [0, 3, 3, 0] },
        barMaxWidth: 16,
        label: {
          show: true,
          position: 'right' as const,
          fontSize: 10,
          formatter: (p: { value: number }) => `${p.value}%`,
        },
      }],
    }
  }
  return horizontalBarOption(items, '#1565C0')
})

// --- ECharts: Categories chart option ---
const categoriesChartOption = computed(() =>
  horizontalBarOption(visibleCategories.value, '#1E88E5')
)

// --- ECharts: Jornais chart option ---
const jornalChartOption = computed(() =>
  horizontalBarOption(visibleJornais.value, '#0D47A1')
)

const districtCountsMap = computed(() => {
  const map: Record<string, number> = {}
  for (const r of distritoCounts.value) {
    map[r.name] = r.count
  }
  return map
})

// --- Article detail modal ---
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
} | null>(null)

async function openArticle(item: { id: string }) {
  articleDetail.value = null
  articleDialog.value = true
  const result = await $fetch(`/api/noticias/${item.id}`)
  articleDetail.value = result as typeof articleDetail.value
}

// --- Calendar Heatmap ---

// All years that have date data (exclude years with 0 publications)
const allCalendarYears = computed(() => {
  const counts = articleCountByYear.value
  return [...counts.entries()]
    .filter(([, c]) => c > 0)
    .map(([y]) => y)
    .sort()
})

// Count articles per year for ranking
const articleCountByYear = computed(() => {
  const raw = facetsData.value?.dateCounts ?? []
  const counts = new Map<number, number>()
  for (const r of raw) {
    const y = parseInt(r.date.substring(0, 4))
    if (!isNaN(y)) counts.set(y, (counts.get(y) ?? 0) + r.count)
  }
  return counts
})

// Default to top 2 years by article count
const defaultCalendarYears = computed(() => {
  const counts = articleCountByYear.value
  return [...counts.entries()]
    .filter(([, c]) => c > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([y]) => y)
    .sort()
})

// User-selected years (reset to defaults whenever data changes)
const selectedCalendarYears = ref<number[]>([])
watch(defaultCalendarYears, (v) => {
  selectedCalendarYears.value = [...v]
}, { immediate: true })

// The years actually displayed
const calendarYears = computed(() => {
  const sel = selectedCalendarYears.value
  if (!sel.length) return defaultCalendarYears.value
  return [...sel].sort()
})

const calendarChartOption = computed(() => {
  const raw = facetsData.value?.dateCounts ?? []
  const years = calendarYears.value
  if (!years.length) return {}

  const maxCount = Math.max(1, ...raw.map(r => r.count))

  return {
    tooltip: {
      formatter: (p: { value: [string, number] }) => `${p.value[0]}: ${p.value[1].toLocaleString()} artigos`,
    },
    visualMap: {
      min: 0,
      max: maxCount,
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: 0,
      inRange: {
        color: ['#E3F2FD', '#90CAF9', '#42A5F5', '#1E88E5', '#1565C0', '#0D47A1'],
      },
    },
    calendar: years.map((year, i) => ({
      top: i * 170 + 40,
      range: String(year),
      cellSize: ['auto', 14],
      left: 60,
      right: 30,
      itemStyle: { borderWidth: 2, borderColor: '#fff' },
      yearLabel: { fontSize: 13 },
      dayLabel: { fontSize: 10 },
      monthLabel: { fontSize: 10 },
    })),
    series: years.map((_year, i) => ({
      type: 'heatmap' as const,
      coordinateSystem: 'calendar' as const,
      calendarIndex: i,
      data: raw
        .filter(r => r.date.startsWith(String(years[i])))
        .map(r => [r.date, r.count]),
    })),
  }
})

// --- Gender balance over time ---
const genderByYear = computed(() => facetsData.value?.genderByYear ?? [])
const genderGlobal = computed(() => {
  let m = 0, f = 0
  for (const r of genderByYear.value) {
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
const genderYears = computed(() => {
  const years = new Set<string>()
  for (const r of genderByYear.value) years.add(r.year)
  return [...years].sort()
})

const genderChartOption = computed(() => {
  const years = genderYears.value
  const mMap = new Map<string, number>()
  const fMap = new Map<string, number>()
  for (const r of genderByYear.value) {
    if (r.gender === 'M') mMap.set(r.year, r.count)
    else if (r.gender === 'F') fMap.set(r.year, r.count)
  }
  const mPct = years.map(y => {
    const m = mMap.get(y) ?? 0
    const f = fMap.get(y) ?? 0
    const total = m + f
    return total ? Math.round((m / total) * 1000) / 10 : 0
  })
  const fPct = years.map(y => {
    const m = mMap.get(y) ?? 0
    const f = fMap.get(y) ?? 0
    const total = m + f
    return total ? Math.round((f / total) * 1000) / 10 : 0
  })
  return {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: { seriesName: string; value: number; axisValue: string; color: string }[]) => {
        if (!Array.isArray(params)) return ''
        const year = params[0]?.axisValue
        const m = mMap.get(year!) ?? 0
        const f = fMap.get(year!) ?? 0
        return params.map(p =>
          `<span style="color:${p.color}">●</span> ${p.seriesName}: ${p.value}% (${(p.seriesName === 'Masculino' ? m : f).toLocaleString()})`
        ).join('<br>') + `<br><span style="color:#999">Total: ${(m + f).toLocaleString()}</span>`
      },
    },
    legend: { data: ['Masculino', 'Feminino'], bottom: 0 },
    grid: { left: 48, right: 24, top: 16, bottom: 40 },
    xAxis: { type: 'category' as const, data: years, boundaryGap: false, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value' as const, max: 100, axisLabel: { formatter: '{value}%', fontSize: 11 } },
    series: [
      {
        name: 'Masculino',
        type: 'line' as const,
        stack: 'gender',
        data: mPct,
        areaStyle: { opacity: 0.85 },
        lineStyle: { width: 0 },
        itemStyle: { color: '#1565C0' },
        symbol: 'none',
        smooth: true,
        emphasis: { focus: 'series' as const },
      },
      {
        name: 'Feminino',
        type: 'line' as const,
        stack: 'gender',
        data: fPct,
        areaStyle: { opacity: 0.85 },
        lineStyle: { width: 0 },
        itemStyle: { color: '#C62828' },
        symbol: 'none',
        smooth: true,
        emphasis: { focus: 'series' as const },
      },
    ],
  }
})

// --- Network chart ---
const networkChartOption = computed(() => {
  const net = forceNetworkData.value || entitiesData.value?.network
  if (!net) return {}

  const maxCount = Math.max(1, ...net.nodes.map(n => n.count))
  const maxWeight = Math.max(1, ...net.edges.map(e => e.weight))

  const idToIndex = new Map(net.nodes.map((n, i) => [n.id, i]))

  return {
    tooltip: {
      formatter: (p: { dataType: string; data: { name?: string; count?: number; source?: string; target?: string; weight?: number } }) => {
        if (p.dataType === 'node') {
          return `<b>${p.data.name}</b><br>${(p.data.count ?? 0).toLocaleString()} menções`
        }
        if (p.dataType === 'edge') {
          return `${p.data.source} — ${p.data.target}<br>${(p.data.weight ?? 0).toLocaleString()} artigos em comum`
        }
        return ''
      },
    },
    series: [{
      type: 'graph' as const,
      layout: 'force' as const,
      roam: true,
      draggable: true,
      label: {
        show: true,
        position: 'right' as const,
        fontSize: 10,
        formatter: (p: { data: { name: string } }) => {
          const name = p.data.name
          return name.length > 20 ? name.substring(0, 18) + '…' : name
        },
      },
      force: {
        repulsion: 200,
        edgeLength: [80, 250],
        gravity: 0.15,
      },
      nodes: net.nodes.map(n => ({
        id: String(n.id),
        name: n.name,
        count: n.count,
        symbolSize: 12 + (n.count / maxCount) * 30,
        itemStyle: { color: n.entity_type === 'PER' ? '#1565C0' : '#E65100' },
        category: n.entity_type === 'PER' ? 0 : 1,
      })),
      edges: net.edges.map(e => ({
        source: String(e.source),
        target: String(e.target),
        weight: e.weight,
        lineStyle: {
          width: 1 + (e.weight / maxWeight) * 6,
          opacity: 0.4,
          curveness: 0.1,
        },
      })),
      categories: [
        { name: 'Pessoas', itemStyle: { color: '#1565C0' } },
        { name: 'Organizações', itemStyle: { color: '#E65100' } },
      ],
    }],
    legend: {
      data: ['Pessoas', 'Organizações'],
      bottom: 0,
    },
  }
})
</script>

<style scoped>
.article-text {
  white-space: pre-wrap;
  max-height: 50vh;
  overflow-y: auto;
  line-height: 1.7;
  font-size: 0.95rem;
}
.cursor-pointer :deep(tbody tr) {
  cursor: pointer;
}
.cursor-pointer :deep(table) {
  font-size: 0.8rem;
}
.cursor-pointer :deep(th) {
  font-size: 0.75rem !important;
}
.table-scroll :deep(.v-table__wrapper) {
  overflow-x: auto;
}
.density-map {
  position: relative;
  min-height: 300px;
}
</style>
