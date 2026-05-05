<template>
  <div v-if="analise">
    <AnaliseHeader
      :title="analise.title"
      :description="analise.description"
      :stats="analise.stats"
      :background-color="analise.backgroundColor"
      :background-image="analise.backgroundImage"
    />
    <AnaliseStep
      v-for="step in analise.steps"
      :key="step.id"
      :step="step"
    />
  </div>
  <v-container v-else-if="error">
    <v-alert type="error" variant="tonal">
      Caso de Estudo não encontrado: {{ route.params.id }}
    </v-alert>
    <v-btn to="/analises" variant="text" class="mt-4">← Voltar</v-btn>
  </v-container>
  <v-container v-else>
    <v-skeleton-loader type="article" />
  </v-container>
</template>

<script setup lang="ts">
import type { AnaliseCompiled } from '~/types/analise'

const route = useRoute()

// In dev: server compiles on the fly from source JSON + API
// In prod: reads pre-compiled JSON (run `compile-analises` before deploy)
const { data: analise, error } = await useAsyncData<AnaliseCompiled>(
  `analise-${route.params.id}`,
  () => $fetch(`/api/analises/${route.params.id}`)
)

useHead({
  title: analise.value?.title || 'Análise',
})
</script>
