<template>
  <v-container>
    <!-- Filters -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchInput"
          label="Pesquisar jornal..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          @update:model-value="onSearchInput"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-autocomplete
          v-model="selectedDistrito"
          :items="distritos"
          item-title="nome"
          item-value="codigoine"
          label="Distrito"
          variant="outlined"
          density="comfortable"
          clearable
          hide-details
          @update:model-value="onFilterChange"
        />
      </v-col>
      <v-col cols="12" md="2" class="d-flex align-center">
        <v-chip v-if="data" color="primary" variant="tonal">
          {{ data.total }} resultados
        </v-chip>
      </v-col>
    </v-row>

    <!-- Loading -->
    <v-row v-if="status === 'pending'" justify="center" class="my-8">
      <v-progress-circular indeterminate color="primary" size="64" />
    </v-row>

    <!-- Error -->
    <v-alert v-else-if="error" type="error" class="mb-4">
      Erro ao carregar jornais: {{ error.message }}
    </v-alert>

    <!-- Results grid -->
    <template v-else-if="data">
      <v-row>
        <v-col
          v-for="jornal in data.items"
          :key="jornal.id"
          cols="12"
          sm="6"
          md="4"
          lg="3"
        >
          <JornalCard :jornal="jornal" />
        </v-col>

        <v-col v-if="data.items.length === 0" cols="12">
          <v-empty-state
            icon="mdi-newspaper-variant-outline"
            title="Nenhum jornal encontrado"
            text="Tente ajustar os filtros de pesquisa."
          />
        </v-col>
      </v-row>

      <!-- Pagination -->
      <v-row v-if="data.totalPages > 1" justify="center" class="mt-4">
        <v-pagination
          v-model="currentPage"
          :length="data.totalPages"
          :total-visible="7"
          rounded
        />
      </v-row>
    </template>
  </v-container>
</template>

<script setup lang="ts">
const route = useRoute()
const searchInput = ref('')
const searchDebounced = ref('')
const selectedDistrito = ref<string | null>((route.query.distrito as string) || null)
const currentPage = ref(1)

let searchTimeout: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    searchDebounced.value = searchInput.value
    currentPage.value = 1
  }, 350)
}

const queryParams = computed(() => ({
  ...(searchDebounced.value ? { search: searchDebounced.value } : {}),
  ...(selectedDistrito.value ? { distrito: selectedDistrito.value } : {}),
  page: currentPage.value,
}))

const { data, status, error } = useJornais(queryParams)

const { data: distritosData } = useFetch<{ codigoine: string; nome: string }[]>('/api/distritos')
const distritos = computed(() => distritosData.value ?? [])

function onFilterChange() {
  currentPage.value = 1
}
</script>
