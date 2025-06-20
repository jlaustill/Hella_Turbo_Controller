<template>
  <div>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-chart-line</v-icon>
            Memory Analysis & Comparison
          </v-card-title>
          <v-card-text>
            <p>Compare memory dumps between different actuators and analyze differences to understand configuration patterns.</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Dump Selection</v-card-title>
          <v-card-text>
            <v-select
              v-model="selectedDumpA"
              :items="availableDumps"
              item-title="name"
              item-value="id"
              label="Primary Dump (A)"
              prepend-icon="mdi-file-document"
              clearable
            />

            <v-select
              v-model="selectedDumpB"
              :items="availableDumps"
              item-title="name"
              item-value="id"
              label="Comparison Dump (B)"
              prepend-icon="mdi-file-document-outline"
              clearable
              class="mt-4"
            />

            <v-btn
              :disabled="!selectedDumpA || !selectedDumpB"
              @click="performComparison"
              color="primary"
              block
              class="mt-4"
            >
              <v-icon start>mdi-compare</v-icon>
              Compare Dumps
            </v-btn>

            <v-divider class="my-4" />

            <v-file-input
              v-model="uploadFiles"
              label="Upload New Dumps"
              prepend-icon="mdi-upload"
              accept=".bin,.hex,.dump"
              multiple
              @change="handleFileUpload"
            />
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Comparison Summary</v-card-title>
          <v-card-text>
            <div v-if="!comparisonResult" class="text-center text-medium-emphasis py-8">
              <v-icon size="64" class="mb-4">mdi-compare-horizontal</v-icon>
              <p>Select two dumps to see comparison results</p>
            </div>

            <div v-else>
              <v-list>
                <v-list-item>
                  <v-list-item-title>Total Differences</v-list-item-title>
                  <v-list-item-subtitle>{{ comparisonResult.totalDifferences }} bytes</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Similarity</v-list-item-title>
                  <v-list-item-subtitle>{{ comparisonResult.similarity }}%</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Key Differences</v-list-item-title>
                  <v-list-item-subtitle>{{ comparisonResult.keyDifferences }} critical bytes</v-list-item-subtitle>
                </v-list-item>
              </v-list>

              <v-progress-linear
                :model-value="comparisonResult.similarity"
                color="success"
                height="8"
                class="mt-4"
              />
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="comparisonResult" class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            Difference Visualization
            <v-spacer />
            <v-btn-toggle v-model="viewMode" mandatory>
              <v-btn value="differences" size="small">Differences Only</v-btn>
              <v-btn value="side-by-side" size="small">Side by Side</v-btn>
              <v-btn value="overlay" size="small">Overlay</v-btn>
            </v-btn-toggle>
          </v-card-title>
          <v-card-text>
            <div class="comparison-viewer">
              <div v-if="viewMode === 'differences'" class="differences-view">
                <h4 class="mb-4">Critical Differences Found:</h4>
                <div
                  v-for="diff in comparisonResult.criticalDifferences"
                  :key="diff.address"
                  class="difference-row"
                >
                  <span class="address">{{ formatAddress(diff.address) }}</span>
                  <span class="value-a">{{ diff.valueA }}</span>
                  <span class="arrow">→</span>
                  <span class="value-b">{{ diff.valueB }}</span>
                  <span class="interpretation">{{ diff.interpretation }}</span>
                </div>
              </div>

              <div v-else-if="viewMode === 'side-by-side'" class="side-by-side-view">
                <div class="dump-column">
                  <h4>{{ getDumpName(selectedDumpA) }}</h4>
                  <div class="hex-viewer">
                    <div
                      v-for="(row, index) in dumpARows"
                      :key="index"
                      class="hex-row"
                    >
                      <span class="address">{{ formatAddress(row.address) }}</span>
                      <span class="hex-data">
                        <span
                          v-for="(byte, byteIndex) in row.bytes"
                          :key="byteIndex"
                          class="hex-byte"
                          :class="{ different: isDifferent(row.address + byteIndex) }"
                        >
                          {{ byte }}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>

                <div class="dump-column">
                  <h4>{{ getDumpName(selectedDumpB) }}</h4>
                  <div class="hex-viewer">
                    <div
                      v-for="(row, index) in dumpBRows"
                      :key="index"
                      class="hex-row"
                    >
                      <span class="address">{{ formatAddress(row.address) }}</span>
                      <span class="hex-data">
                        <span
                          v-for="(byte, byteIndex) in row.bytes"
                          :key="byteIndex"
                          class="hex-byte"
                          :class="{ different: isDifferent(row.address + byteIndex) }"
                        >
                          {{ byte }}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="overlay-view">
                <div class="hex-viewer">
                  <div
                    v-for="(row, index) in overlayRows"
                    :key="index"
                    class="hex-row"
                  >
                    <span class="address">{{ formatAddress(row.address) }}</span>
                    <span class="hex-data">
                      <span
                        v-for="(byte, byteIndex) in row.bytes"
                        :key="byteIndex"
                        class="hex-byte"
                        :class="getByteClass(row.address + byteIndex)"
                        :title="getByteTooltip(row.address + byteIndex)"
                      >
                        {{ byte }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="comparisonResult" class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Key Findings</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                v-for="finding in comparisonResult.keyFindings"
                :key="finding.title"
                :prepend-icon="finding.icon"
              >
                <v-list-item-title>{{ finding.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ finding.description }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Export Options</v-card-title>
          <v-card-text>
            <v-btn
              @click="exportComparison"
              variant="outlined"
              color="primary"
              block
              class="mb-4"
            >
              <v-icon start>mdi-file-export</v-icon>
              Export Comparison Report
            </v-btn>

            <v-btn
              @click="exportDifferences"
              variant="outlined"
              color="secondary"
              block
              class="mb-4"
            >
              <v-icon start>mdi-file-table</v-icon>
              Export Differences CSV
            </v-btn>

            <v-btn
              @click="generatePatch"
              variant="outlined"
              color="warning"
              block
            >
              <v-icon start>mdi-file-code</v-icon>
              Generate Patch File
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
  type: string;
  data: Uint8Array;
  timestamp: string;
}

interface ComparisonResult {
  totalDifferences: number;
  similarity: number;
  keyDifferences: number;
  criticalDifferences: CriticalDifference[];
  keyFindings: KeyFinding[];
}

interface CriticalDifference {
  address: number;
  valueA: string;
  valueB: string;
  interpretation: string;
}

interface KeyFinding {
  title: string;
  description: string;
  icon: string;
}

interface HexRow {
  address: number;
  bytes: string[];
}

// Reactive data
const selectedDumpA = ref<string>('');
const selectedDumpB = ref<string>('');
const uploadFiles = ref<File[]>([]);
const viewMode = ref('differences');
const comparisonResult = ref<ComparisonResult | null>(null);

// Sample dumps for demonstration
const availableDumps = ref<MemoryDump[]>([
  {
    id: '1',
    name: 'G-222_20241220_143052.bin',
    type: 'G-222',
    data: generateSampleDump('G-222'),
    timestamp: '2024-12-20 14:30:52',
  },
  {
    id: '2',
    name: 'G-221_reference.bin',
    type: 'G-221',
    data: generateSampleDump('G-221'),
    timestamp: '2024-12-15 10:15:30',
  },
]);

// Computed properties for hex views
const dumpARows = computed(() => generateHexRows(getDumpData(selectedDumpA.value)));
const dumpBRows = computed(() => generateHexRows(getDumpData(selectedDumpB.value)));
const overlayRows = computed(() => generateOverlayRows());

// Methods
function generateSampleDump(type: string): Uint8Array {
  const data = new Uint8Array(1024);
  
  // Generate realistic-looking memory data with known patterns
  for (let i = 0; i < data.length; i++) {
    if (i === 0x27) {
      // CAN ID byte 1
      data[i] = type === 'G-222' ? 0x7D : 0x7C;
    } else if (i === 0x28) {
      // CAN ID byte 2 + position format
      data[i] = type === 'G-222' ? 0x08 : 0x00;
    } else if (i >= 0x30 && i <= 0x35) {
      // Position configuration area
      data[i] = Math.floor(Math.random() * 256);
    } else {
      // Random data with some structure
      data[i] = Math.floor(Math.random() * 256);
    }
  }
  
  return data;
}

function getDumpData(dumpId: string): Uint8Array | null {
  const dump = availableDumps.value.find(d => d.id === dumpId);
  return dump?.data || null;
}

function getDumpName(dumpId: string): string {
  const dump = availableDumps.value.find(d => d.id === dumpId);
  return dump?.name || 'Unknown';
}

function generateHexRows(data: Uint8Array | null): HexRow[] {
  if (!data) return [];
  
  const rows: HexRow[] = [];
  const bytesPerRow = 16;
  
  for (let i = 0; i < data.length; i += bytesPerRow) {
    const bytes: string[] = [];
    
    for (let j = 0; j < bytesPerRow && i + j < data.length; j++) {
      bytes.push(data[i + j].toString(16).padStart(2, '0').toUpperCase());
    }
    
    rows.push({ address: i, bytes });
  }
  
  return rows;
}

function generateOverlayRows(): HexRow[] {
  const dataA = getDumpData(selectedDumpA.value);
  const dataB = getDumpData(selectedDumpB.value);
  
  if (!dataA || !dataB) return [];
  
  const rows: HexRow[] = [];
  const bytesPerRow = 16;
  const maxLength = Math.max(dataA.length, dataB.length);
  
  for (let i = 0; i < maxLength; i += bytesPerRow) {
    const bytes: string[] = [];
    
    for (let j = 0; j < bytesPerRow && i + j < maxLength; j++) {
      const byteA = i + j < dataA.length ? dataA[i + j] : 0;
      const byteB = i + j < dataB.length ? dataB[i + j] : 0;
      
      // Show the byte from dump A, but styling will indicate differences
      bytes.push(byteA.toString(16).padStart(2, '0').toUpperCase());
    }
    
    rows.push({ address: i, bytes });
  }
  
  return rows;
}

function performComparison() {
  const dataA = getDumpData(selectedDumpA.value);
  const dataB = getDumpData(selectedDumpB.value);
  
  if (!dataA || !dataB) return;
  
  const differences: CriticalDifference[] = [];
  let totalDifferences = 0;
  let keyDifferences = 0;
  
  const maxLength = Math.max(dataA.length, dataB.length);
  
  for (let i = 0; i < maxLength; i++) {
    const byteA = i < dataA.length ? dataA[i] : 0;
    const byteB = i < dataB.length ? dataB[i] : 0;
    
    if (byteA !== byteB) {
      totalDifferences++;
      
      // Check if this is a critical difference
      if (isCriticalAddress(i)) {
        keyDifferences++;
        differences.push({
          address: i,
          valueA: byteA.toString(16).padStart(2, '0').toUpperCase(),
          valueB: byteB.toString(16).padStart(2, '0').toUpperCase(),
          interpretation: interpretDifference(i, byteA, byteB),
        });
      }
    }
  }
  
  const similarity = Math.round(((maxLength - totalDifferences) / maxLength) * 100);
  
  comparisonResult.value = {
    totalDifferences,
    similarity,
    keyDifferences,
    criticalDifferences: differences,
    keyFindings: generateKeyFindings(differences),
  };
}

function isCriticalAddress(address: number): boolean {
  // CAN ID configuration
  if (address === 0x27 || address === 0x28) return true;
  
  // Position configuration area
  if (address >= 0x30 && address <= 0x35) return true;
  
  // Other known critical areas
  if (address >= 0x20 && address <= 0x2F) return true;
  
  return false;
}

function interpretDifference(address: number, valueA: number, valueB: number): string {
  if (address === 0x27) {
    return `CAN ID byte 1: ${(valueA * 8).toString(16)} vs ${(valueB * 8).toString(16)}`;
  }
  
  if (address === 0x28) {
    return `CAN ID byte 2 + format: Position format differs`;
  }
  
  if (address >= 0x30 && address <= 0x35) {
    return `Position config: Different calibration values`;
  }
  
  return `Configuration difference at ${formatAddress(address)}`;
}

function generateKeyFindings(differences: CriticalDifference[]): KeyFinding[] {
  const findings: KeyFinding[] = [];
  
  const canIdDiff = differences.find(d => d.address === 0x27 || d.address === 0x28);
  if (canIdDiff) {
    findings.push({
      title: 'CAN ID Configuration Differs',
      description: 'The actuators use different CAN IDs, indicating different part numbers or configurations.',
      icon: 'mdi-network-strength-3',
    });
  }
  
  const positionDiffs = differences.filter(d => d.address >= 0x30 && d.address <= 0x35);
  if (positionDiffs.length > 0) {
    findings.push({
      title: 'Position Calibration Differs',
      description: `${positionDiffs.length} bytes differ in position configuration area.`,
      icon: 'mdi-tune',
    });
  }
  
  if (differences.length === 0) {
    findings.push({
      title: 'Identical Configuration',
      description: 'No critical differences found. These actuators have the same configuration.',
      icon: 'mdi-check-circle',
    });
  }
  
  return findings;
}

function isDifferent(address: number): boolean {
  if (!comparisonResult.value) return false;
  return comparisonResult.value.criticalDifferences.some(d => d.address === address);
}

function getByteClass(address: number): string {
  const dataA = getDumpData(selectedDumpA.value);
  const dataB = getDumpData(selectedDumpB.value);
  
  if (!dataA || !dataB) return '';
  
  const byteA = address < dataA.length ? dataA[address] : 0;
  const byteB = address < dataB.length ? dataB[address] : 0;
  
  if (byteA !== byteB) {
    return isCriticalAddress(address) ? 'critical-difference' : 'minor-difference';
  }
  
  return '';
}

function getByteTooltip(address: number): string {
  const dataA = getDumpData(selectedDumpA.value);
  const dataB = getDumpData(selectedDumpB.value);
  
  if (!dataA || !dataB) return '';
  
  const byteA = address < dataA.length ? dataA[address] : 0;
  const byteB = address < dataB.length ? dataB[address] : 0;
  
  if (byteA !== byteB) {
    return `A: 0x${byteA.toString(16).toUpperCase()} | B: 0x${byteB.toString(16).toUpperCase()}`;
  }
  
  return '';
}

function formatAddress(address: number): string {
  return `0x${address.toString(16).padStart(4, '0').toUpperCase()}`;
}

function handleFileUpload(event: Event) {
  // TODO: Implement file upload handling
  console.log('Files uploaded:', uploadFiles.value);
}

function exportComparison() {
  if (!comparisonResult.value) return;
  
  const report = {
    timestamp: new Date().toISOString(),
    dumpA: getDumpName(selectedDumpA.value),
    dumpB: getDumpName(selectedDumpB.value),
    summary: {
      totalDifferences: comparisonResult.value.totalDifferences,
      similarity: comparisonResult.value.similarity,
      keyDifferences: comparisonResult.value.keyDifferences,
    },
    criticalDifferences: comparisonResult.value.criticalDifferences,
    keyFindings: comparisonResult.value.keyFindings,
  };
  
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
  downloadFile(blob, 'memory-comparison-report.json');
}

function exportDifferences() {
  if (!comparisonResult.value) return;
  
  const csvHeader = 'Address,Value A,Value B,Interpretation\n';
  const csvData = comparisonResult.value.criticalDifferences
    .map(d => `${formatAddress(d.address)},${d.valueA},${d.valueB},"${d.interpretation}"`)
    .join('\n');
  
  const blob = new Blob([csvHeader + csvData], { type: 'text/csv' });
  downloadFile(blob, 'memory-differences.csv');
}

function generatePatch() {
  // TODO: Implement patch file generation
  console.log('Generating patch file...');
}

function downloadFile(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
.comparison-viewer {
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.differences-view .difference-row {
  display: flex;
  gap: 16px;
  padding: 8px;
  border-bottom: 1px solid var(--v-border-color);
  align-items: center;
}

.side-by-side-view {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.dump-column h4 {
  text-align: center;
  margin-bottom: 16px;
  padding: 8px;
  background-color: var(--v-theme-surface-variant);
  border-radius: 4px;
}

.hex-viewer {
  background-color: var(--v-theme-surface);
  border: 1px solid var(--v-border-color);
  border-radius: 4px;
  padding: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.hex-row {
  display: flex;
  gap: 12px;
  margin-bottom: 2px;
  padding: 2px 4px;
}

.address {
  color: var(--v-theme-primary);
  min-width: 60px;
}

.hex-byte {
  margin-right: 8px;
  padding: 1px 2px;
  border-radius: 2px;
}

.hex-byte.different {
  background-color: rgba(var(--v-theme-warning), 0.3);
  font-weight: bold;
}

.hex-byte.critical-difference {
  background-color: rgba(var(--v-theme-error), 0.4);
  font-weight: bold;
}

.hex-byte.minor-difference {
  background-color: rgba(var(--v-theme-warning), 0.2);
}

.value-a {
  color: var(--v-theme-info);
  font-weight: bold;
}

.value-b {
  color: var(--v-theme-warning);
  font-weight: bold;
}

.arrow {
  color: var(--v-medium-emphasis);
}

.interpretation {
  color: var(--v-medium-emphasis);
  font-style: italic;
}
</style>