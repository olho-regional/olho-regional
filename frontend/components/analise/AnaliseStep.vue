<template>
  <v-container class="analise-step py-8">
    <!-- Type 1: Text only -->
    <div v-if="step.type === 'text'" class="analise-step__text">
      <h2 v-if="step.title" class="text-h5 font-weight-bold mb-3">{{ step.title }}</h2>
      <div class="text-body-1 analise-step__prose" v-html="renderedText" />
    </div>

    <!-- Type 2: Text + Visualization (split) -->
    <v-row v-else-if="step.type === 'split' && step.layout !== 'viz-bottom'" align="center">
      <v-col
        cols="12"
        md="5"
        :order-md="step.layout === 'viz-left' ? 2 : 1"
      >
        <h2 v-if="step.title" class="text-h5 font-weight-bold mb-3">{{ step.title }}</h2>
        <div class="text-body-1 analise-step__prose" v-html="renderedText" />
      </v-col>
      <v-col
        cols="12"
        md="7"
        :order-md="step.layout === 'viz-left' ? 1 : 2"
      >
        <AnaliseViz v-if="step.viz" :viz="step.viz" />
      </v-col>
    </v-row>

    <!-- Type 2b: Text above Visualization (viz-bottom) -->
    <div v-else-if="step.type === 'split' && step.layout === 'viz-bottom'">
      <h2 v-if="step.title" class="text-h5 font-weight-bold mb-3">{{ step.title }}</h2>
      <div class="text-body-1 analise-step__prose mb-4" v-html="renderedText" />
      <AnaliseViz v-if="step.viz" :viz="step.viz" />
    </div>

    <!-- Type 3: Side-by-side visualizations -->
    <div v-else-if="step.type === 'side-by-side'">
      <h2 v-if="step.title" class="text-h5 font-weight-bold mb-4">{{ step.title }}</h2>
      <div v-if="step.text" class="text-body-1 analise-step__prose mb-4" v-html="renderedText" />
      <v-row>
        <v-col
          v-for="(viz, i) in step.vizzes"
          :key="i"
          cols="12"
          :md="12 / (step.vizzes?.length || 2)"
        >
          <AnaliseViz :viz="viz" />
        </v-col>
      </v-row>
    </div>

    <!-- Type 4: Grid of small vizzes -->
    <div v-else-if="step.type === 'grid'">
      <h2 v-if="step.title" class="text-h5 font-weight-bold mb-4">{{ step.title }}</h2>
      <div v-if="step.text" class="text-body-1 analise-step__prose mb-4" v-html="renderedText" />
      <v-row>
        <v-col
          v-for="(item, i) in step.items"
          :key="i"
          cols="6"
          sm="4"
          md="3"
        >
          <div class="analise-grid-item text-center">
            <p class="text-subtitle-2 font-weight-bold mb-1">
              {{ item.label }}
              <a v-if="item.link" :href="item.link" target="_blank" rel="noopener noreferrer" class="ml-1">
                <v-icon size="14" color="grey">mdi-wikipedia</v-icon>
              </a>
            </p>
            <AnaliseViz :viz="item.viz" />
          </div>
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnaliseStepCompiled } from '~/types/analise'

const props = defineProps<{
  step: AnaliseStepCompiled
}>()

const renderedText = computed(() => {
  const text = props.step.text || ''
  return text
    .split('\n\n')
    .map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('')
})
</script>

<style scoped>
.analise-step {
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.analise-step:last-child {
  border-bottom: none;
}

.analise-step__prose :deep(p) {
  margin-bottom: 0.75rem;
}

.analise-step__prose :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
