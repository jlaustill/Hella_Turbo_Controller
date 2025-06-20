<template>
  <v-app>
    <v-app-bar color="primary" dark>
      <v-app-bar-title>
        <v-icon class="mr-2">mdi-car-turbocharger</v-icon>
        Hella Turbo Controller
      </v-app-bar-title>
      
      <v-spacer />
      
      <v-btn icon @click="toggleTheme">
        <v-icon>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
      </v-btn>
    </v-app-bar>

    <v-navigation-drawer permanent>
      <v-list>
        <v-list-item
          v-for="route in routes"
          :key="route.path"
          :to="route.path"
          :prepend-icon="route.icon"
          :title="route.title"
        />
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useTheme } from 'vuetify';

const theme = useTheme();
const isDark = ref(false);

const routes = [
  { path: '/', title: 'Dashboard', icon: 'mdi-view-dashboard' },
  { path: '/actuators', title: 'Actuators', icon: 'mdi-cog' },
  { path: '/memory', title: 'Memory Viewer', icon: 'mdi-memory' },
  { path: '/can-monitor', title: 'CAN Monitor', icon: 'mdi-network' },
  { path: '/analysis', title: 'Analysis', icon: 'mdi-chart-line' },
];

const toggleTheme = () => {
  isDark.value = !isDark.value;
  theme.global.name.value = isDark.value ? 'dark' : 'light';
};
</script>