<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-memory</v-icon>
            Memory Viewer
          </v-card-title>
          <v-card-text>
            <p>View and analyze actuator memory dumps with hex visualization and data interpretation.</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>Memory Dumps</v-card-title>
          <v-card-text>
            <v-file-input
              v-model="selectedFile"
              label="Load Memory Dump"
              prepend-icon="mdi-file-upload"
              accept=".bin,.hex,.dump"
              @change="loadMemoryDump"
            />

            <v-divider class="my-4" />

            <v-list>
              <v-list-subheader>Recent Dumps</v-list-subheader>
              <v-list-item
                v-for="dump in recentDumps"
                :key="dump.id"
                @click="selectDump(dump)"
                :active="selectedDump?.id === dump.id"
              >
                <v-list-item-title>{{ dump.name }}</v-list-item-title>
                <v-list-item-subtitle>{{ dump.timestamp }}</v-list-item-subtitle>
                <template #append>
                  <v-chip size="small" :color="dump.type === 'G-222' ? 'primary' : 'secondary'">
                    {{ dump.type }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card>
          <v-card-title>
            Hex Dump View
            <v-spacer />
            <v-btn-toggle v-model="viewMode" mandatory>
              <v-btn value="hex" size="small">Hex</v-btn>
              <v-btn value="ascii" size="small">ASCII</v-btn>
              <v-btn value="both" size="small">Both</v-btn>
            </v-btn-toggle>
          </v-card-title>
          <v-card-text>
            <div v-if="!selectedDump" class="text-center text-medium-emphasis py-8">
              <v-icon size="64" class="mb-4">mdi-file-search</v-icon>
              <p>Select or load a memory dump to view</p>
            </div>

            <div v-else class="memory-dump">
              <v-row class="mb-4">
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="searchAddress"
                    label="Jump to Address"
                    prepend-icon="mdi-magnify"
                    placeholder="0x0027"
                    @keyup.enter="jumpToAddress"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-select
                    v-model="bytesPerRow"
                    :items="[8, 16, 32]"
                    label="Bytes per Row"
                    prepend-icon="mdi-view-grid"
                  />
                </v-col>
              </v-row>

              <div class="hex-viewer" ref="hexViewer">
                <div
                  v-for="(row, index) in displayedRows"
                  :key="index"
                  class="hex-row"
                  :class="{ highlighted: row.isHighlighted }"
                >
                  <span class="address">{{ formatAddress(row.address) }}</span>
                  <span class="hex-data">
                    <span
                      v-for="(byte, byteIndex) in row.bytes"
                      :key="byteIndex"
                      class="hex-byte"
                      :class="{ 
                        'can-id': isCANIdByte(row.address + byteIndex),
                        'position': isPositionByte(row.address + byteIndex),
                        'important': isImportantByte(row.address + byteIndex)
                      }"
                      @click="selectByte(row.address + byteIndex)"
                    >
                      {{ byte }}
                    </span>
                  </span>
                  <span v-if="viewMode === 'both' || viewMode === 'ascii'" class="ascii-data">
                    {{ row.ascii }}
                  </span>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="selectedDump" class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Data Interpretation</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>CAN ID (0x27-0x28)</v-list-item-title>
                <v-list-item-subtitle>{{ getCANId() }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Position Data Format (0x28 block)</v-list-item-title>
                <v-list-item-subtitle>{{ getPositionFormat() }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Min Position</v-list-item-title>
                <v-list-item-subtitle>{{ getMinPosition() }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Max Position</v-list-item-title>
                <v-list-item-subtitle>{{ getMaxPosition() }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Memory Statistics</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <v-list-item-title>Total Size</v-list-item-title>
                <v-list-item-subtitle>{{ selectedDump.data.length }} bytes</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Non-Zero Bytes</v-list-item-title>
                <v-list-item-subtitle>{{ getNonZeroCount() }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Entropy</v-list-item-title>
                <v-list-item-subtitle>{{ getEntropy() }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-btn variant="outlined" @click="exportAnalysis" class="mt-4">
              <v-icon start>mdi-export</v-icon>
              Export Analysis
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface MemoryDump {
  id: string;
  name: string;
  timestamp: string;
  type: string;
  data: Uint8Array;
}

interface HexRow {
  address: number;
  bytes: string[];
  ascii: string;
  isHighlighted: boolean;
}

// Reactive data
const selectedFile = ref<File[]>([]);
const selectedDump = ref<MemoryDump | null>(null);
const viewMode = ref('both');
const searchAddress = ref('');
const bytesPerRow = ref(16);
const hexViewer = ref<HTMLElement>();

// Sample dumps for demonstration
const recentDumps = ref<MemoryDump[]>([
  {
    id: '1',
    name: 'G-222_20241220_143052.bin',
    timestamp: '2024-12-20 14:30:52',
    type: 'G-222',
    data: new Uint8Array(1024), // Will be populated with actual data
  },
  {
    id: '2', 
    name: 'G-221_reference.bin',
    timestamp: '2024-12-15 10:15:30',
    type: 'G-221',
    data: new Uint8Array(1024),
  },
]);

// Computed properties
const displayedRows = computed(() => {
  if (!selectedDump.value) return [];
  
  const rows: HexRow[] = [];
  const data = selectedDump.value.data;
  const perRow = bytesPerRow.value;
  
  for (let i = 0; i < data.length; i += perRow) {
    const bytes: string[] = [];
    let ascii = '';
    
    for (let j = 0; j < perRow && i + j < data.length; j++) {
      const byte = data[i + j];
      bytes.push(byte.toString(16).padStart(2, '0').toUpperCase());
      ascii += (byte >= 32 && byte <= 126) ? String.fromCharCode(byte) : '.';
    }
    
    rows.push({
      address: i,
      bytes,
      ascii,
      isHighlighted: false,
    });
  }
  
  return rows;
});

// Methods
const loadMemoryDump = async (event: Event) => {
  const files = (event.target as HTMLInputElement).files;
  if (!files || files.length === 0) return;
  
  const file = files[0];
  const arrayBuffer = await file.arrayBuffer();
  const data = new Uint8Array(arrayBuffer);
  
  const dump: MemoryDump = {
    id: Date.now().toString(),
    name: file.name,
    timestamp: new Date().toLocaleString(),
    type: file.name.includes('G-221') ? 'G-221' : 'G-222',
    data,
  };
  
  recentDumps.value.unshift(dump);
  selectedDump.value = dump;
};

const selectDump = (dump: MemoryDump) => {
  selectedDump.value = dump;
};

const formatAddress = (address: number): string => {
  return `0x${address.toString(16).padStart(4, '0').toUpperCase()}`;
};

const jumpToAddress = () => {
  if (!searchAddress.value || !hexViewer.value) return;
  
  let addr = 0;
  try {
    addr = parseInt(searchAddress.value.replace('0x', ''), 16);
  } catch {
    return;
  }
  
  const rowIndex = Math.floor(addr / bytesPerRow.value);
  const element = hexViewer.value.children[rowIndex] as HTMLElement;
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    element.classList.add('highlighted');
    setTimeout(() => element.classList.remove('highlighted'), 2000);
  }
};

const selectByte = (address: number) => {
  console.log(`Selected byte at address: ${formatAddress(address)}`);
};

const isCANIdByte = (address: number): boolean => {
  return address === 0x27 || address === 0x28;
};

const isPositionByte = (address: number): boolean => {
  // Position data is typically in specific ranges
  return (address >= 0x30 && address <= 0x35);
};

const isImportantByte = (address: number): boolean => {
  // Other important configuration bytes
  return (address >= 0x20 && address <= 0x2F);
};

const getCANId = (): string => {
  if (!selectedDump.value) return 'N/A';
  const data = selectedDump.value.data;
  if (data.length > 0x28) {
    const canId = (data[0x27] * 8) + (data[0x28] >> 4);
    return `0x${canId.toString(16).toUpperCase()}`;
  }
  return 'N/A';
};

const getPositionFormat = (): string => {
  if (!selectedDump.value) return 'N/A';
  const data = selectedDump.value.data;
  if (data.length > 0x2C) {
    const format = (data[0x2A] << 8) | (data[0x2C] << 2);
    return `0x${format.toString(16).toUpperCase()}`;
  }
  return 'N/A';
};

const getMinPosition = (): string => {
  // TODO: Implement based on actual memory layout
  return '0x0113';
};

const getMaxPosition = (): string => {
  // TODO: Implement based on actual memory layout
  return '0x0220';
};

const getNonZeroCount = (): number => {
  if (!selectedDump.value) return 0;
  return selectedDump.value.data.filter(byte => byte !== 0).length;
};

const getEntropy = (): string => {
  if (!selectedDump.value) return 'N/A';
  // Simple entropy calculation
  const data = selectedDump.value.data;
  const freq: Record<number, number> = {};
  
  for (const byte of data) {
    freq[byte] = (freq[byte] || 0) + 1;
  }
  
  let entropy = 0;
  for (const count of Object.values(freq)) {
    const p = count / data.length;
    entropy -= p * Math.log2(p);
  }
  
  return entropy.toFixed(2);
};

const exportAnalysis = () => {
  // TODO: Implement analysis export
  console.log('Exporting analysis...');
};
</script>

<style scoped>
.hex-viewer {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  background-color: var(--v-theme-surface);
  border: 1px solid var(--v-border-color);
  border-radius: 4px;
  padding: 16px;
  max-height: 500px;
  overflow-y: auto;
}

.hex-row {
  display: flex;
  margin-bottom: 2px;
  padding: 2px 4px;
  border-radius: 2px;
}

.hex-row.highlighted {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.address {
  color: var(--v-theme-primary);
  margin-right: 16px;
  min-width: 60px;
}

.hex-data {
  margin-right: 16px;
  flex: 1;
}

.hex-byte {
  margin-right: 8px;
  cursor: pointer;
  padding: 1px 2px;
  border-radius: 2px;
}

.hex-byte:hover {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.hex-byte.can-id {
  background-color: rgba(var(--v-theme-warning), 0.3);
  font-weight: bold;
}

.hex-byte.position {
  background-color: rgba(var(--v-theme-info), 0.3);
  font-weight: bold;
}

.hex-byte.important {
  background-color: rgba(var(--v-theme-secondary), 0.2);
}

.ascii-data {
  color: var(--v-medium-emphasis);
  min-width: 200px;
}
</style>