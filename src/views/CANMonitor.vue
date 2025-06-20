<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-network</v-icon>
            CAN Bus Monitor
          </v-card-title>
          <v-card-text>
            <p>Real-time monitoring of CAN bus traffic with message filtering and position tracking.</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Monitor Controls</v-card-title>
          <v-card-text>
            <v-btn
              :color="isMonitoring ? 'error' : 'success'"
              :loading="starting"
              @click="toggleMonitoring"
              block
              class="mb-4"
            >
              <v-icon start>{{ isMonitoring ? 'mdi-stop' : 'mdi-play' }}</v-icon>
              {{ isMonitoring ? 'Stop Monitor' : 'Start Monitor' }}
            </v-btn>

            <v-divider class="my-4" />

            <v-switch
              v-model="autoScroll"
              label="Auto Scroll"
              color="primary"
            />

            <v-switch
              v-model="showTimestamps"
              label="Show Timestamps"
              color="primary"
            />

            <v-switch
              v-model="filterHellaMessages"
              label="Filter Hella Messages Only"
              color="primary"
            />

            <v-text-field
              v-model="maxMessages"
              label="Max Messages"
              type="number"
              min="100"
              max="10000"
              class="mt-4"
            />

            <v-btn
              @click="clearMessages"
              variant="outlined"
              color="warning"
              block
              class="mt-4"
            >
              <v-icon start>mdi-delete</v-icon>
              Clear Messages
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>
            Message Log
            <v-spacer />
            <v-chip color="primary">{{ messageCount }} messages</v-chip>
          </v-card-title>
          <v-card-text>
            <div class="message-log" ref="messageLog">
              <div
                v-for="message in displayedMessages"
                :key="message.id"
                class="message-row"
                :class="getMessageClass(message)"
              >
                <span v-if="showTimestamps" class="timestamp">
                  {{ formatTimestamp(message.timestamp) }}
                </span>
                <span class="can-id">{{ message.canId }}</span>
                <span class="data">{{ message.data }}</span>
                <span v-if="message.interpretation" class="interpretation">
                  {{ message.interpretation }}
                </span>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Position Tracking</v-card-title>
          <v-card-text>
            <div class="position-display">
              <v-row align="center" class="mb-4">
                <v-col cols="6">
                  <div class="text-h4 text-center">{{ currentPosition }}</div>
                  <div class="text-center text-medium-emphasis">Current Position</div>
                </v-col>
                <v-col cols="6">
                  <v-progress-circular
                    :model-value="positionPercentage"
                    :size="80"
                    :width="8"
                    color="primary"
                  >
                    {{ positionPercentage }}%
                  </v-progress-circular>
                </v-col>
              </v-row>

              <v-row>
                <v-col cols="6">
                  <div class="text-subtitle-2">Min: {{ minPosition }}</div>
                </v-col>
                <v-col cols="6">
                  <div class="text-subtitle-2">Max: {{ maxPosition }}</div>
                </v-col>
              </v-row>

              <v-progress-linear
                :model-value="positionPercentage"
                color="primary"
                height="8"
                class="mt-4"
              />
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Message Statistics</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>Total Messages</v-list-item-title>
                <v-list-item-subtitle>{{ messageCount }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Messages/sec</v-list-item-title>
                <v-list-item-subtitle>{{ messagesPerSecond }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Position Updates</v-list-item-title>
                <v-list-item-subtitle>{{ positionUpdateCount }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Error Count</v-list-item-title>
                <v-list-item-subtitle>{{ errorCount }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-btn
              @click="exportLog"
              variant="outlined"
              color="info"
              block
              class="mt-4"
            >
              <v-icon start>mdi-download</v-icon>
              Export Log
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onUnmounted } from 'vue';

interface CANMessage {
  id: string;
  timestamp: Date;
  canId: string;
  data: string;
  interpretation?: string;
  type: 'request' | 'response' | 'error' | 'position';
}

// Reactive data
const isMonitoring = ref(false);
const starting = ref(false);
const autoScroll = ref(true);
const showTimestamps = ref(true);
const filterHellaMessages = ref(true);
const maxMessages = ref(1000);
const messageLog = ref<HTMLElement>();

// Message data
const messages = ref<CANMessage[]>([]);
const messageCount = computed(() => messages.value.length);

// Position tracking
const currentPosition = ref('0x0180');
const minPosition = ref('0x0113');
const maxPosition = ref('0x0220');
const positionUpdateCount = ref(0);

// Statistics
const messagesPerSecond = ref(0);
const errorCount = ref(0);

// Simulation data for demo
let simulationInterval: number | null = null;
let messageIdCounter = 0;

const positionPercentage = computed(() => {
  const current = parseInt(currentPosition.value, 16);
  const min = parseInt(minPosition.value, 16);
  const max = parseInt(maxPosition.value, 16);
  return Math.round(((current - min) / (max - min)) * 100);
});

const displayedMessages = computed(() => {
  let filtered = messages.value;
  
  if (filterHellaMessages.value) {
    filtered = filtered.filter(msg => 
      msg.canId === '0x3F0' || msg.canId === '0x3E8' || 
      msg.canId === '0x3EA' || msg.canId === '0x3EB'
    );
  }
  
  return filtered.slice(-maxMessages.value);
});

// Methods
const toggleMonitoring = async () => {
  if (isMonitoring.value) {
    stopMonitoring();
  } else {
    await startMonitoring();
  }
};

const startMonitoring = async () => {
  starting.value = true;
  
  try {
    // TODO: Implement actual CAN monitoring
    // For now, simulate messages
    simulateCANTraffic();
    isMonitoring.value = true;
  } catch (error) {
    console.error('Failed to start monitoring:', error);
  } finally {
    starting.value = false;
  }
};

const stopMonitoring = () => {
  isMonitoring.value = false;
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
  }
};

const simulateCANTraffic = () => {
  simulationInterval = setInterval(() => {
    if (!isMonitoring.value) return;
    
    // Simulate different types of CAN messages
    const messageTypes = [
      { canId: '0x3F0', type: 'request' as const, data: generateRequestData() },
      { canId: '0x3E8', type: 'response' as const, data: generateMemoryData() },
      { canId: '0x3EA', type: 'position' as const, data: generatePositionData() },
      { canId: '0x3EB', type: 'response' as const, data: generateAckData() },
    ];
    
    const randomMessage = messageTypes[Math.floor(Math.random() * messageTypes.length)];
    
    const message: CANMessage = {
      id: (++messageIdCounter).toString(),
      timestamp: new Date(),
      canId: randomMessage.canId,
      data: randomMessage.data,
      type: randomMessage.type,
      interpretation: interpretMessage(randomMessage.canId, randomMessage.data),
    };
    
    messages.value.push(message);
    
    // Update position if it's a position message
    if (randomMessage.type === 'position') {
      updatePositionFromMessage(randomMessage.data);
      positionUpdateCount.value++;
    }
    
    // Auto-scroll if enabled
    if (autoScroll.value) {
      nextTick(() => {
        if (messageLog.value) {
          messageLog.value.scrollTop = messageLog.value.scrollHeight;
        }
      });
    }
    
    // Update messages per second
    updateMessagesPerSecond();
  }, 200 + Math.random() * 800); // Variable interval
};

const generateRequestData = (): string => {
  const commands = ['22 00 27', '22 00 28', '22 00 30', '2E 00 27'];
  return commands[Math.floor(Math.random() * commands.length)];
};

const generateMemoryData = (): string => {
  return Array.from({ length: 8 }, () => 
    Math.floor(Math.random() * 256).toString(16).padStart(2, '0').toUpperCase()
  ).join(' ');
};

const generatePositionData = (): string => {
  // Generate realistic position data
  const basePosition = parseInt(currentPosition.value, 16);
  const variation = Math.floor(Math.random() * 20) - 10; // ±10 variation
  const newPosition = Math.max(0x0113, Math.min(0x0220, basePosition + variation));
  
  const byte1 = (newPosition >> 8) & 0xFF;
  const byte2 = newPosition & 0xFF;
  
  return `00 00 ${byte1.toString(16).padStart(2, '0').toUpperCase()} ${byte2.toString(16).padStart(2, '0').toUpperCase()} 00 00 00 00`;
};

const generateAckData = (): string => {
  return '6E 00 27 00 00 00 00 00';
};

const interpretMessage = (canId: string, data: string): string => {
  switch (canId) {
    case '0x3F0':
      if (data.startsWith('22')) return 'Memory read request';
      if (data.startsWith('2E')) return 'Memory write request';
      return 'Request message';
    
    case '0x3E8':
      return 'Memory data response';
    
    case '0x3EA':
      const bytes = data.split(' ');
      if (bytes.length >= 4) {
        const position = (parseInt(bytes[2], 16) << 8) | parseInt(bytes[3], 16);
        return `Position: 0x${position.toString(16).toUpperCase()}`;
      }
      return 'Position update';
    
    case '0x3EB':
      return 'Acknowledgment';
    
    default:
      return '';
  }
};

const updatePositionFromMessage = (data: string) => {
  const bytes = data.split(' ');
  if (bytes.length >= 4) {
    const position = (parseInt(bytes[2], 16) << 8) | parseInt(bytes[3], 16);
    currentPosition.value = `0x${position.toString(16).toUpperCase()}`;
  }
};

const updateMessagesPerSecond = () => {
  // Simple approximation - count messages in last second
  const oneSecondAgo = new Date(Date.now() - 1000);
  const recentMessages = messages.value.filter(msg => msg.timestamp > oneSecondAgo);
  messagesPerSecond.value = recentMessages.length;
};

const getMessageClass = (message: CANMessage): string => {
  switch (message.type) {
    case 'request': return 'message-request';
    case 'response': return 'message-response';
    case 'position': return 'message-position';
    case 'error': return 'message-error';
    default: return '';
  }
};

const formatTimestamp = (timestamp: Date): string => {
  return timestamp.toLocaleTimeString() + '.' + timestamp.getMilliseconds().toString().padStart(3, '0');
};

const clearMessages = () => {
  messages.value = [];
  messageIdCounter = 0;
  positionUpdateCount.value = 0;
  errorCount.value = 0;
};

const exportLog = () => {
  const logData = messages.value.map(msg => ({
    timestamp: msg.timestamp.toISOString(),
    canId: msg.canId,
    data: msg.data,
    interpretation: msg.interpretation,
  }));
  
  const blob = new Blob([JSON.stringify(logData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = `can-log-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  a.click();
  
  URL.revokeObjectURL(url);
};

// Cleanup
onUnmounted(() => {
  stopMonitoring();
});
</script>

<style scoped>
.message-log {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  background-color: var(--v-theme-surface);
  border: 1px solid var(--v-border-color);
  border-radius: 4px;
  padding: 8px;
  height: 400px;
  overflow-y: auto;
}

.message-row {
  display: flex;
  gap: 12px;
  padding: 2px 4px;
  border-radius: 2px;
  margin-bottom: 1px;
}

.message-request {
  background-color: rgba(var(--v-theme-info), 0.1);
}

.message-response {
  background-color: rgba(var(--v-theme-success), 0.1);
}

.message-position {
  background-color: rgba(var(--v-theme-warning), 0.1);
  font-weight: bold;
}

.message-error {
  background-color: rgba(var(--v-theme-error), 0.1);
}

.timestamp {
  color: var(--v-medium-emphasis);
  min-width: 120px;
}

.can-id {
  color: var(--v-theme-primary);
  font-weight: bold;
  min-width: 60px;
}

.data {
  font-family: monospace;
  min-width: 200px;
}

.interpretation {
  color: var(--v-medium-emphasis);
  font-style: italic;
}

.position-display {
  text-align: center;
}
</style>