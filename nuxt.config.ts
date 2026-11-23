export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  ssr: false,
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],
  ui: {
    colorMode: false,
  },
  devServer: {
    host: '127.0.0.1',
    port: 3000,
  },
  vite: {
    clearScreen: false,
    server: {
      strictPort: true,
    },
  },
})
