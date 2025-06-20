<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-cog</v-icon>
            Actuator Management
          </v-card-title>
          <v-card-text>
            <v-alert type="warning" class="mb-4">
              <strong>⚠️ Safety Warning</strong>
              Incorrect configuration can permanently damage your actuator. Always backup memory before making changes.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>CAN Interface Setup</v-card-title>
          <v-card-text>
            <v-select
              v-model="selectedInterface"
              :items="canInterfaces"
              label="CAN Interface"
              prepend-icon="mdi-network"
              hint="Select your CAN interface (socketcan, slcan, etc.)"
              persistent-hint
            />
            
            <v-text-field
              v-model="channel"
              label="Channel"
              prepend-icon="mdi-cable-data"
              hint="e.g., can0, /dev/ttyUSB0"
              persistent-hint
              class="mt-4"
            />

            <v-btn
              :color="connectionStatus === 'connected' ? 'success' : 'primary'"
              :loading="connecting"
              @click="toggleConnection"
              block
              class="mt-4"
            >
              <v-icon start>{{ connectionStatus === 'connected' ? 'mdi-lan-disconnect' : 'mdi-lan-connect' }}</v-icon>
              {{ connectionStatus === 'connected' ? 'Disconnect' : 'Connect' }}
            </v-btn>

            <v-chip
              :color="connectionStatus === 'connected' ? 'success' : 'error'"
              class="mt-2"
            >
              {{ connectionStatus }}
            </v-chip>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Actuator Information</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>Type</v-list-item-title>
                <v-list-item-subtitle>{{ actuatorInfo.type || 'Unknown' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Current Position</v-list-item-title>
                <v-list-item-subtitle>{{ actuatorInfo.currentPosition || 'N/A' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Min Position</v-list-item-title>
                <v-list-item-subtitle>{{ actuatorInfo.minPosition || 'N/A' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Max Position</v-list-item-title>
                <v-list-item-subtitle>{{ actuatorInfo.maxPosition || 'N/A' }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-btn
              :disabled="connectionStatus !== 'connected'"
              @click="readActuatorInfo"
              variant="outlined"
              class="mt-4"
            >
              <v-icon start>mdi-refresh</v-icon>
              Refresh Info
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Position Configuration</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="newMinPosition"
                  label="New Min Position (hex)"
                  prepend-icon="mdi-arrow-down-bold"
                  placeholder="0x0113"
                  :disabled="connectionStatus !== 'connected'"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="newMaxPosition"
                  label="New Max Position (hex)"
                  prepend-icon="mdi-arrow-up-bold"
                  placeholder="0x0220"
                  :disabled="connectionStatus !== 'connected'"
                />
              </v-col>
              <v-col cols="12" md="4" class="d-flex align-center">
                <v-btn
                  :disabled="connectionStatus !== 'connected' || !newMinPosition || !newMaxPosition"
                  @click="updatePositions"
                  color="warning"
                  block
                >
                  <v-icon start>mdi-update</v-icon>
                  Update Positions
                </v-btn>
              </v-col>
            </v-row>

            <v-divider class="my-4" />

            <v-btn
              :disabled="connectionStatus !== 'connected'"
              @click="autoCalibrate"
              color="primary"
              class="mr-4"
            >
              <v-icon start>mdi-auto-fix</v-icon>
              Auto Calibrate
            </v-btn>

            <v-btn
              :disabled="connectionStatus !== 'connected'"
              @click="readMemory"
              color="info"
            >
              <v-icon start>mdi-download</v-icon>
              Read Memory
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

// Interface options
const canInterfaces = ['socketcan', 'slcan', 'virtual'];
const selectedInterface = ref('socketcan');
const channel = ref('can0');

// Connection state
const connectionStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected');
const connecting = ref(false);

// Actuator information
const actuatorInfo = ref({
  type: '',
  currentPosition: '',
  minPosition: '',
  maxPosition: '',
});

// Position configuration
const newMinPosition = ref('');
const newMaxPosition = ref('');

// Methods
const toggleConnection = async () => {
  if (connectionStatus.value === 'connected') {
    // Disconnect
    connectionStatus.value = 'disconnected';
    return;
  }

  // Connect
  connecting.value = true;
  connectionStatus.value = 'connecting';
  
  try {
    // TODO: Implement actual CAN connection
    await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate connection
    connectionStatus.value = 'connected';
  } catch (error) {
    connectionStatus.value = 'disconnected';
    console.error('Connection failed:', error);
  } finally {
    connecting.value = false;
  }
};

const readActuatorInfo = async () => {
  try {
    // TODO: Implement actual actuator reading
    actuatorInfo.value = {
      type: 'Hella Universal Turbo Actuator I',
      currentPosition: '0x0180',
      minPosition: '0x0113',
      maxPosition: '0x0220',
    };
  } catch (error) {
    console.error('Failed to read actuator info:', error);
  }
};

const updatePositions = async () => {
  try {
    // TODO: Implement position updates
    console.log('Updating positions:', { min: newMinPosition.value, max: newMaxPosition.value });
  } catch (error) {
    console.error('Failed to update positions:', error);
  }
};

const autoCalibrate = async () => {
  try {
    // TODO: Implement auto calibration
    console.log('Starting auto calibration...');
  } catch (error) {
    console.error('Auto calibration failed:', error);
  }
};

const readMemory = async () => {
  try {
    // TODO: Implement memory reading
    console.log('Reading memory...');
  } catch (error) {
    console.error('Memory read failed:', error);
  }
};
</script>