// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  modules: [
    'vuetify-nuxt-module',
  ],

  app: {
    head: {
      title: "Olh'ó Regional",
      htmlAttrs: { lang: 'pt' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Um projeto de análise dos últimos 30 anos de jornalismo local em Portugal com base no Arquivo.pt, 1996-2026.' },
        { property: 'og:title', content: "Olh'ó Regional" },
        { property: 'og:description', content: 'Um projeto de análise dos últimos 30 anos de jornalismo local em Portugal com base no Arquivo.pt, 1996-2026.' },
        { property: 'og:type', content: 'website' },
        { property: 'og:locale', content: 'pt_PT' },
        { name: 'twitter:card', content: 'summary' },
        { name: 'twitter:title', content: "Olh'ó Regional" },
        { name: 'twitter:description', content: 'Um projeto de análise dos últimos 30 anos de jornalismo local em Portugal com base no Arquivo.pt, 1996-2026.' },
        { name: 'theme-color', content: '#1565C0' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32.png' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700;1,800;1,900&display=swap' },
      ],
    },
  },

  vuetify: {
    moduleOptions: {
      styles: { configFile: 'assets/styles/vuetify.scss' },
    },
    vuetifyOptions: {
      theme: {
        defaultTheme: 'light',
        themes: {
          light: {
            colors: {
              primary: '#1565C0',
              secondary: '#424242',
              accent: '#FF8F00',
              background: '#FAF7F2',
              surface: '#FFFFFF',
            },
          },
        },
      },
    },
  },

  nitro: {
    preset: 'cloudflare_pages',
  },

  vite: {
    server: {
      watch: {
        // Also trigger HMR on public/ JSON changes
        ignored: ['!**/public/**'],
      },
    },
  },

  css: [
    'assets/styles/main.scss',
  ],
})
