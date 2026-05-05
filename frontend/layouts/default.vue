<template>
  <v-app>
    <v-app-bar color="primary" density="comfortable">
      <v-app-bar-title>
        <NuxtLink to="/" class="text-white text-decoration-none font-weight-bold">
          Olh'ó Regional
        </NuxtLink>
      </v-app-bar-title>

      <template #append>
        <nav class="app-bar-nav">
          <v-btn to="/analisar" variant="text" class="text-white">
            Analisar
          </v-btn>
          <v-btn to="/analises" variant="text" class="text-white">
            Casos de Estudo
          </v-btn>
          <v-btn to="/jornais" variant="text" class="text-white">
            Jornais
          </v-btn>
          <v-btn to="/dados" variant="text" class="text-white">
            Dados
          </v-btn>
        </nav>
      </template>
    </v-app-bar>

    <v-main class="main-no-overflow">
      <slot />
    </v-main>

    <v-footer class="text-center d-flex flex-column pa-4" style="background-color: #F5F1EB;">
      <div class="text-caption text-medium-emphasis">
        Análise do jornalismo local em Portugal
      </div>
      <DbSourceChip class="mt-2" />
    </v-footer>
  </v-app>
</template>

<style>
.main-no-overflow.v-main {
  --v-layout-top: 64px;
  overflow-y: visible !important;
}

.v-app-bar .v-toolbar__content {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.v-app-bar .v-toolbar__content::-webkit-scrollbar { display: none; }
.v-app-bar .v-toolbar__append {
  margin-inline-start: auto;
  flex-shrink: 0;
}
.v-app-bar .v-app-bar-title {
  flex: 0 1 auto;
  min-width: auto;
  margin-inline-end: 1rem;
}
.v-app-bar .v-app-bar-title a {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
  font-style: italic;
  text-decoration: underline !important;
  text-decoration-color: rgba(255, 255, 255, 0.6);
  text-decoration-thickness: 0.06em;
  text-underline-offset: 0.15em;
  letter-spacing: -0.02em;
}

.app-bar-nav {
  display: flex;
  flex-wrap: nowrap;
  gap: 0;
}
</style>
