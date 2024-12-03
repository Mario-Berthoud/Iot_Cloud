// https://nuxt.com/docs/api/configuration/nuxt-config

import Aura from '@primevue/themes/aura';
import Material from '@primevue/themes/material';

export default defineNuxtConfig({
  devtools: {
    enabled: true,
    timeline: {
      enabled: true,
    }
  },
  buildDir: "./dist",
  devServer: {
    host: '0.0.0.0',
    port: '8080'
  },
  // routeRules: {
  //   "/todo": { ssr: false },
  //   "/info": { ssr: false },
  // },
  modules: [
    'unplugin-icons/nuxt',
    ['@nuxtjs/google-fonts', { families: { Inconsolata: [400, 600] }, preconnect: false, prefetch: false, preload: false }],
    '@unocss/nuxt',
    '@primevue/nuxt-module',
    //'@pinia/nuxt',
    //'@pinia-plugin-persistedstate/nuxt',
  ],
  app: {
    head: {
      link: [],
    },
  },
  components: {
    global: true,
    dirs: [
      '~/components'
    ],
  },
  primevue: {
    usePrimeVue: true,
    options: {
      ripple: true,
      inputVariant: 'filled',
      unstyled: false,
      theme: {
        preset: Aura,
        options: {
          prefix: "p-",
          cssLayer: true,
          darkModeSelector: 'light',
        }
      }
    },
    components: {
      prefix: 'Prime',
      include: ['Button', 'Menu', 'Avatar', 'ScrollPanel', 'Card', 'Skeleton', 'InputText', 'Password', 'MultiSelect', 'Dropdown', 'Sidebar', 'Dialog', 'Toast', 'Textarea', 'FileUpload', 'AutoComplete', 'InputGroup', 'IconField', 'InputIcon', 'Message', "FloatLabel", "DataTable", "Column", "Tag"],
    },
  },
  unocss: {
    uno: {
      prefix: 'u-',
    },
  },
  pinia: {
    storesDirs: ['./stores/**']
  },
  // css: [
  //   'primevue/resources/primevue.css',
  //   'primevue/resources/themes/lara-light-blue/theme.css',
  // ],
  vite: {
    vue:
    {
      script:
      {
        defineModel: true,
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler'
        },
        sass: {
          api: 'modern-compiler',
          additionalData: '@use "@/assets/style/global.sass" as *',
        },
      },
    },
  },
})
