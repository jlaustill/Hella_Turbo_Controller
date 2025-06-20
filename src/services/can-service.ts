/**
 * CAN Bus Communication Service
 * 
 * Provides TypeScript interface for CAN bus communication with Hella turbo actuators.
 * Supports both SocketCAN (Linux) and SLCAN (USB adapters) interfaces.
 */

export interface CANMessage {
  id: number;
  data: Buffer;
  timestamp?: Date;
  extended?: boolean;
  remote?: boolean;
}

export interface CANInterface {
  type: 'socketcan' | 'slcan' | 'virtual';
  channel: string;
  bitrate?: number;
}

export interface ActuatorPosition {
  current: number;
  min: number;
  max: number;
  timestamp: Date;
}

export interface MemoryDump {
  data: Uint8Array;
  timestamp: Date;
  size: number;
}

export class HellaProgError extends Error {
  constructor(message: string, public readonly code?: string) {
    super(message);
    this.name = 'HellaProgError';
  }
}

/**
 * CAN Bus service for communicating with Hella turbo actuators
 */
export class CANService {
  private channel: any = null;
  private isConnected = false;
  private messageListeners: Array<(message: CANMessage) => void> = [];

  // CAN Message IDs for Hella actuators
  static readonly CAN_IDS = {
    REQUEST: 0x3F0,      // Request messages to actuator
    MEMORY_RESPONSE: 0x3E8,  // Memory read responses
    POSITION_RESPONSE: 0x3EA, // Position status responses  
    ACK_RESPONSE: 0x3EB,     // Acknowledgment responses
  };

  constructor(private canInterface: CANInterface) {}

  /**
   * Connect to the CAN interface
   */
  async connect(): Promise<void> {
    try {
      if (this.canInterface.type === 'socketcan') {
        await this.connectSocketCAN();
      } else if (this.canInterface.type === 'slcan') {
        await this.connectSLCAN();
      } else {
        throw new HellaProgError(`Unsupported interface type: ${this.canInterface.type}`);
      }

      this.isConnected = true;
      this.setupMessageHandling();
    } catch (error: any) {
      throw new HellaProgError(`Failed to connect to CAN interface: ${error.message}`);
    }
  }

  /**
   * Disconnect from the CAN interface
   */
  async disconnect(): Promise<void> {
    if (this.channel) {
      try {
        await this.channel.stop();
      } catch (error) {
        console.warn('Error stopping CAN channel:', error);
      }
      this.channel = null;
    }
    this.isConnected = false;
  }

  /**
   * Check if connected to CAN interface
   */
  isConnectedToCAN(): boolean {
    return this.isConnected;
  }

  /**
   * Send a CAN message
   */
  async sendMessage(id: number, data: Buffer): Promise<void> {
    if (!this.isConnected || !this.channel) {
      throw new HellaProgError('Not connected to CAN interface');
    }

    const message: CANMessage = {
      id,
      data,
      timestamp: new Date(),
    };

    try {
      await this.channel.send(message);
    } catch (error: any) {
      throw new HellaProgError(`Failed to send CAN message: ${error.message}`);
    }
  }

  /**
   * Add a message listener
   */
  addMessageListener(listener: (message: CANMessage) => void): void {
    this.messageListeners.push(listener);
  }

  /**
   * Remove a message listener
   */
  removeMessageListener(listener: (message: CANMessage) => void): void {
    const index = this.messageListeners.indexOf(listener);
    if (index !== -1) {
      this.messageListeners.splice(index, 1);
    }
  }

  /**
   * Read memory from actuator
   */
  async readMemory(): Promise<MemoryDump> {
    if (!this.isConnected) {
      throw new HellaProgError('Not connected to CAN interface');
    }

    const memoryData = new Uint8Array(1024); // Standard memory size
    let bytesRead = 0;

    try {
      // Read memory in chunks
      for (let address = 0; address < 1024; address += 8) {
        const chunk = await this.readMemoryChunk(address, Math.min(8, 1024 - address));
        memoryData.set(chunk, address);
        bytesRead += chunk.length;
        
        // Add small delay to avoid overwhelming the actuator
        await this.delay(10);
      }

      return {
        data: memoryData,
        timestamp: new Date(),
        size: bytesRead,
      };
    } catch (error: any) {
      throw new HellaProgError(`Failed to read memory: ${error.message}`);
    }
  }

  /**
   * Read current actuator position
   */
  async readCurrentPosition(): Promise<number> {
    if (!this.isConnected) {
      throw new HellaProgError('Not connected to CAN interface');
    }

    try {
      // Send position request
      const requestData = Buffer.from([0x22, 0x00, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00]);
      await this.sendMessage(CANService.CAN_IDS.REQUEST, requestData);

      // Wait for response
      const response = await this.waitForMessage(CANService.CAN_IDS.POSITION_RESPONSE, 1000);
      
      // Extract position from bytes 2-3 (corrected from previous 5-6 assumption)
      if (response.data.length >= 4) {
        return (response.data[2] << 8) | response.data[3];
      }

      throw new HellaProgError('Invalid position response format');
    } catch (error: any) {
      throw new HellaProgError(`Failed to read position: ${error.message}`);
    }
  }

  /**
   * Read minimum position setting
   */
  async readMinPosition(): Promise<number> {
    return this.readPositionSetting(0x27);
  }

  /**
   * Read maximum position setting
   */
  async readMaxPosition(): Promise<number> {
    return this.readPositionSetting(0x28);
  }

  /**
   * Set minimum position
   */
  async setMinPosition(position: number): Promise<void> {
    await this.setPositionSetting(0x27, position);
  }

  /**
   * Set maximum position
   */
  async setMaxPosition(position: number): Promise<void> {
    await this.setPositionSetting(0x28, position);
  }

  /**
   * Auto-discover end positions through calibration
   */
  async findEndPositions(): Promise<{ min: number; max: number }> {
    if (!this.isConnected) {
      throw new HellaProgError('Not connected to CAN interface');
    }

    try {
      // This is a simplified version - actual implementation would involve
      // slowly moving the actuator and monitoring position feedback
      console.warn('Auto-calibration not yet implemented in TypeScript version');
      
      // Return current settings as placeholder
      const min = await this.readMinPosition();
      const max = await this.readMaxPosition();
      
      return { min, max };
    } catch (error: any) {
      throw new HellaProgError(`Auto-calibration failed: ${error.message}`);
    }
  }

  // Private methods

  private async connectSocketCAN(): Promise<void> {
    try {
      // Dynamic import to handle missing socketcan dependency gracefully
      const { createInterface } = await import('socketcan');
      
      this.channel = createInterface(this.canInterface.channel);
      await this.channel.start();
    } catch (error: any) {
      if (error.code === 'MODULE_NOT_FOUND') {
        throw new HellaProgError('SocketCAN module not available. Install with: npm install socketcan');
      }
      throw error;
    }
  }

  private async connectSLCAN(): Promise<void> {
    // TODO: Implement SLCAN support
    throw new HellaProgError('SLCAN support not yet implemented in TypeScript version');
  }

  private setupMessageHandling(): void {
    if (!this.channel) return;

    this.channel.addListener('onMessage', (message: any) => {
      const canMessage: CANMessage = {
        id: message.id,
        data: Buffer.from(message.data),
        timestamp: new Date(),
        extended: message.ext,
        remote: message.rtr,
      };

      // Notify all listeners
      this.messageListeners.forEach(listener => {
        try {
          listener(canMessage);
        } catch (error) {
          console.error('Error in message listener:', error);
        }
      });
    });
  }

  private async readMemoryChunk(address: number, length: number): Promise<Uint8Array> {
    // Send memory read request
    const requestData = Buffer.from([
      0x22, // Read command
      (address >> 8) & 0xFF, // Address high byte
      address & 0xFF, // Address low byte
      length, // Length
      0x00, 0x00, 0x00, 0x00 // Padding
    ]);

    await this.sendMessage(CANService.CAN_IDS.REQUEST, requestData);

    // Wait for memory response
    const response = await this.waitForMessage(CANService.CAN_IDS.MEMORY_RESPONSE, 1000);
    
    // Extract data payload (skip header bytes)
    return new Uint8Array(response.data.slice(3, 3 + length));
  }

  private async readPositionSetting(address: number): Promise<number> {
    // Send position setting read request
    const requestData = Buffer.from([0x22, 0x00, address, 0x00, 0x00, 0x00, 0x00, 0x00]);
    await this.sendMessage(CANService.CAN_IDS.REQUEST, requestData);

    // Wait for response
    const response = await this.waitForMessage(CANService.CAN_IDS.MEMORY_RESPONSE, 1000);
    
    if (response.data.length >= 5) {
      return (response.data[3] << 8) | response.data[4];
    }

    throw new HellaProgError('Invalid position setting response');
  }

  private async setPositionSetting(address: number, position: number): Promise<void> {
    // Send position setting write request
    const requestData = Buffer.from([
      0x2E, // Write command
      0x00,
      address,
      (position >> 8) & 0xFF, // Position high byte
      position & 0xFF, // Position low byte
      0x00, 0x00, 0x00 // Padding
    ]);

    await this.sendMessage(CANService.CAN_IDS.REQUEST, requestData);

    // Wait for acknowledgment
    await this.waitForMessage(CANService.CAN_IDS.ACK_RESPONSE, 1000);
  }

  private async waitForMessage(expectedId: number, timeoutMs: number): Promise<CANMessage> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.removeMessageListener(messageListener);
        reject(new HellaProgError(`Timeout waiting for CAN message ID ${expectedId.toString(16)}`));
      }, timeoutMs);

      const messageListener = (message: CANMessage) => {
        if (message.id === expectedId) {
          clearTimeout(timeout);
          this.removeMessageListener(messageListener);
          resolve(message);
        }
      };

      this.addMessageListener(messageListener);
    });
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Factory function to create CAN service instance
 */
export function createCANService(canInterface: CANInterface): CANService {
  return new CANService(canInterface);
}

/**
 * Utility function to validate CAN interface configuration
 */
export function validateCANInterface(canInterface: CANInterface): boolean {
  if (!canInterface.type || !canInterface.channel) {
    return false;
  }

  if (canInterface.type === 'socketcan') {
    return /^can\d+$/.test(canInterface.channel);
  }

  if (canInterface.type === 'slcan') {
    return /^\/dev\/tty(USB|ACM)\d+$/.test(canInterface.channel);
  }

  return true;
}

/**
 * Utility function to detect available CAN interfaces
 */
export async function detectCANInterfaces(): Promise<CANInterface[]> {
  const interfaces: CANInterface[] = [];

  try {
    // Try to detect SocketCAN interfaces (Linux only)
    if (process.platform === 'linux') {
      const fs = await import('fs');
      const files = await fs.promises.readdir('/sys/class/net');
      
      for (const file of files) {
        if (file.startsWith('can')) {
          interfaces.push({
            type: 'socketcan',
            channel: file,
          });
        }
      }
    }

    // Try to detect USB-to-CAN devices
    const fs = await import('fs');
    try {
      const devices = await fs.promises.readdir('/dev');
      for (const device of devices) {
        if (device.startsWith('ttyUSB') || device.startsWith('ttyACM')) {
          interfaces.push({
            type: 'slcan',
            channel: `/dev/${device}`,
          });
        }
      }
    } catch {
      // /dev might not be accessible or not exist (non-Linux)
    }
  } catch (error) {
    console.warn('Error detecting CAN interfaces:', error);
  }

  return interfaces;
}