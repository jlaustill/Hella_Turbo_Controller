<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-car-turbocharger</v-icon>
            Welcome to Hella Turbo Controller
          </v-card-title>
          <v-card-text>
            <v-alert type="info" class="mb-4">
              <strong>🎉 New TypeScript Version!</strong>
              This is the modern, cross-platform version built with Electron + Vue + Vuetify.
            </v-alert>
            
            <p class="text-h6 mb-3">🔧 What's New:</p>
            <v-list>
              <v-list-item prepend-icon="mdi-check-circle" title="Cross-platform GUI (Windows, Mac, Linux)" />
              <v-list-item prepend-icon="mdi-check-circle" title="TypeScript for better safety and development" />
              <v-list-item prepend-icon="mdi-check-circle" title="Modern Vue 3 + Vuetify Material Design" />
              <v-list-item prepend-icon="mdi-check-circle" title="Enhanced memory visualization" />
              <v-list-item prepend-icon="mdi-check-circle" title="Real-time CAN monitoring" />
            </v-list>

            <v-alert type="warning" class="mt-4">
              <strong>⚠️ Safety First!</strong>
              This tool can permanently damage actuators if used incorrectly. 
              Always backup memory dumps and understand the analysis before making changes.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Quick Start</v-card-title>
          <v-card-text>
            <v-stepper alt-labels>
              <v-stepper-header>
                <v-stepper-item value="1" title="Connect CAN" />
                <v-divider />
                <v-stepper-item value="2" title="Configure Actuator" />
                <v-divider />
                <v-stepper-item value="3" title="Read Memory" />
                <v-divider />
                <v-stepper-item value="4" title="Analyze" />
              </v-stepper-header>
            </v-stepper>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Legacy Python Version</v-card-title>
          <v-card-text>
            <p>The original Python CLI tools are available in the <code>legacy-python/</code> folder.</p>
            <v-btn variant="outlined" class="mt-2">
              <v-icon start>mdi-folder</v-icon>
              View Legacy Tools
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
// Dashboard component - landing page
</script>