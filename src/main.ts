import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createVuetify } from 'vuetify';
import { createRouter, createWebHashHistory } from 'vue-router';

// Vuetify
import 'vuetify/styles';
import '@mdi/font/css/materialdesignicons.css';
import { md3 } from 'vuetify/blueprints';

import App from './App.vue';
import routes from './router';

// Create router
const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

// Create Vuetify
const vuetify = createVuetify({
  blueprint: md3,
  theme: {
    defaultTheme: 'light',
  },
});

// Create app
const app = createApp(App);
app.use(createPinia());
app.use(router);
app.use(vuetify);

app.mount('#app');