<template>
  <v-card
    :to="`/jornal/${jornal.id}`"
    hover
    class="h-100 d-flex flex-column"
  >
    <div class="d-flex align-center pa-4 pb-0">
      <v-avatar v-if="logoUrl && !logoError" size="40" rounded="lg" class="mr-3 flex-shrink-0">
        <v-img :src="logoUrl" :alt="jornal.nome" @error="logoError = true" />
      </v-avatar>
      <v-avatar v-else size="40" rounded="lg" color="grey-lighten-3" class="mr-3 flex-shrink-0">
        <v-icon color="grey">mdi-newspaper</v-icon>
      </v-avatar>
      <div class="text-subtitle-1 font-weight-bold" style="min-width: 0; white-space: normal; word-break: break-word; line-height: 1.3">
        {{ jornal.nome }}
      </div>
    </div>

    <v-card-text class="flex-grow-1">
      <div v-if="jornal.estado" class="text-body-2 mb-1">
        <v-chip size="x-small" :color="jornal.estado === 'Ativo' ? 'success' : 'grey'" variant="tonal">
          {{ jornal.estado }}
        </v-chip>
      </div>
    </v-card-text>

    <v-card-actions>
      <v-btn
        v-if="jornal.url"
        size="small"
        variant="text"
        color="primary"
        :href="normalizeUrl(jornal.url)"
        target="_blank"
        @click.stop
        prepend-icon="mdi-open-in-new"
      >
        Website
      </v-btn>
      <v-spacer />
      <v-icon size="small" color="grey">mdi-chevron-right</v-icon>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import type { Jornal } from '~/server/database/schema'
import { getLogoUrl } from '~/composables/useLogos'

const props = defineProps<{
  jornal: Jornal
}>()

const logoUrl = computed(() => {
  const domain = props.jornal.url
    ?.replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '')
  return getLogoUrl(domain)
})
const logoError = ref(false)

function normalizeUrl(url: string): string {
  if (!url) return '#'
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return `https://${url}`
}
</script>
