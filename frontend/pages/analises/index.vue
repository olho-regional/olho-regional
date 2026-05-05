<template>
  <v-container>
    <h1 class="text-h4 mb-2">Casos de Estudo</h1>
    <p class="text-body-1 text-medium-emphasis mb-6">
      Uma Coletânea em crescimento, aqui encontras análises realizadas sobre os dados recolhidos, convidamos a comunidade a fazer novas sugestões ou mesmo partilhar resultados que queiram incluir nesta páginas.
    </p>

    <v-row>
      <v-col
        v-for="item in analyses"
        :key="item.id"
        cols="12"
        sm="6"
        md="4"
      >
        <v-card class="d-flex flex-column" height="100%" :to="`/analises/${item.id}`">
          <div
            class="d-flex align-end pa-4"
            style="height: 120px; position: relative"
            :style="{ backgroundColor: item.backgroundColor || '#f5f5f5' }"
          >
            <span class="text-h6 font-weight-bold" style="line-height: 1.3">{{ item.title }}</span>
          </div>
          <v-card-text class="flex-grow-1">
            <p class="text-body-2">{{ item.description }}</p>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="primary"
              variant="tonal"
            >
              Ver análise
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Contact / suggestion card -->
      <v-col cols="12" sm="6" md="4">
        <v-card
          class="d-flex flex-column"
          height="100%"
          variant="outlined"
          href="https://github.com/msramalho/olho-regional/issues"
          target="_blank"
          rel="noopener"
        >
          <div
            class="d-flex align-end pa-4"
            style="height: 120px; background: repeating-linear-gradient(135deg, #f5f5f5, #f5f5f5 10px, #fafafa 10px, #fafafa 20px)"
          >
            <span class="text-h6 font-weight-bold" style="line-height: 1.3">Contribuir</span>
          </div>
          <v-card-text class="flex-grow-1 d-flex align-center">
            <p class="text-body-2">
              Tens sugestões ou resultados de análises sobre estes dados? Entra em contacto com a equipa.
            </p>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="grey-darken-2"
              variant="outlined"
              prepend-icon="mdi-github"
            >
              GitHub
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
const { data: analyses } = await useAsyncData('analises-list', () => $fetch('/api/analises'))
</script>

<style scoped>
.v-card .text-h6 {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif !important;
}
</style>
