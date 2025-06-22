/**
 * CAN Bus Communication Service for Hella Turbo Actuators
 *
 * Provides real CAN bus communication using socketcan (Linux) or simulation
 */

export interface CANMessage {
  id: number;
  data: Uint8Array;
  timestamp: Date;
  extended?: boolean;
  remote?: boolean;
}

export interface CANInterface {
  type: "socketcan" | "slcan";
  channel: string;
  bitrate?: number;
}

export class HellaProgError extends Error {
  constructor(
    message: string,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "HellaProgError";
  }
}

/**
 * CAN Bus service for communicating with Hella turbo actuators
 */
export class CANService {
  private isConnected = false;
  private messageListeners: Array<(message: CANMessage) => void> = [];
  private socketcanWorker: Worker | null = null;

  // CAN Message IDs for Hella actuators
  static readonly CAN_IDS = {
    REQUEST: 0x3f0, // Request messages to actuator
    MEMORY_RESPONSE: 0x3e8, // Memory read responses
    POSITION_RESPONSE: 0x3ea, // Position status responses
    ACK_RESPONSE: 0x3eb, // Acknowledgment responses
  };

  constructor(private canInterface: CANInterface) {}

  /**
   * Connect to the CAN interface
   */
  async connect(): Promise<void> {
    try {
      if (this.canInterface.type === "socketcan") {
        await this.connectSocketCAN();
      } else {
        throw new HellaProgError(
          `Unsupported interface type: ${this.canInterface.type}. Only 'socketcan' is supported.`,
        );
      }

      this.isConnected = true;
      this.setupMessageHandling();
    } catch (error: any) {
      throw new HellaProgError(
        `Failed to connect to CAN interface: ${error.message}`,
      );
    }
  }

  /**
   * Disconnect from the CAN interface
   */
  async disconnect(): Promise<void> {
    if (this.socketcanWorker) {
      this.socketcanWorker.terminate();
      this.socketcanWorker = null;
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
  async sendMessage(id: number, data: Uint8Array): Promise<void> {
    if (!this.isConnected) {
      throw new HellaProgError("Not connected to CAN interface");
    }

    const message: CANMessage = {
      id,
      data,
      timestamp: new Date(),
    };

    try {
      if (this.socketcanWorker) {
        this.socketcanWorker.postMessage({
          type: "send",
          message: {
            id: message.id,
            data: Array.from(message.data),
          },
        });
      }
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
   * Read current actuator position
   */
  async readCurrentPosition(): Promise<number> {
    if (!this.isConnected) {
      throw new HellaProgError("Not connected to CAN interface");
    }

    try {
      // Send position request
      const requestData = new Uint8Array([
        0x22, 0x00, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00,
      ]);
      await this.sendMessage(CANService.CAN_IDS.REQUEST, requestData);

      // Wait for response
      const response = await this.waitForMessage(
        CANService.CAN_IDS.POSITION_RESPONSE,
        1000,
      );

      // Extract position from bytes 2-3 (corrected from previous 5-6 assumption)
      if (response.data.length >= 4) {
        return (response.data[2] << 8) | response.data[3];
      }

      throw new HellaProgError("Invalid position response format");
    } catch (error: any) {
      throw new HellaProgError(`Failed to read position: ${error.message}`);
    }
  }

  // Private methods

  private async connectSocketCAN(): Promise<void> {
    try {
      // First, try to bring up the CAN interface using the system
      await this.setupCANInterface();

      // Create a Web Worker to handle socketcan communication
      this.socketcanWorker = new Worker(
        new URL("../workers/socketcanWorker.js", import.meta.url),
      );

      // Initialize the worker with our interface
      this.socketcanWorker.postMessage({
        type: "connect",
        channel: this.canInterface.channel,
      });

      // Wait for connection confirmation
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(
          () => reject(new Error("Connection timeout")),
          5000,
        );

        const messageHandler = (event: MessageEvent) => {
          if (event.data.type === "connected") {
            clearTimeout(timeout);
            this.socketcanWorker?.removeEventListener(
              "message",
              messageHandler,
            );
            resolve(true);
          } else if (event.data.type === "error") {
            clearTimeout(timeout);
            this.socketcanWorker?.removeEventListener(
              "message",
              messageHandler,
            );
            reject(new Error(event.data.message));
          }
        };

        this.socketcanWorker?.addEventListener("message", messageHandler);
      });
    } catch (error: any) {
      throw new HellaProgError(`SocketCAN connection failed: ${error.message}`);
    }
  }

  private async connectVirtual(): Promise<void> {
    throw new HellaProgError(
      "Virtual CAN interfaces are not supported. Use socketcan for real hardware.",
    );
  }

  private async setupCANInterface(): Promise<void> {
    try {
      // Try to setup CAN interface - this might require sudo
      const apiUrl =
        process.env.NODE_ENV === "development"
          ? "http://localhost:3001/api/can-setup"
          : "/api/can-setup";

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          channel: this.canInterface.channel,
          bitrate: this.canInterface.bitrate || 500000,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          `CAN setup failed: ${response.statusText}. ${errorData.message || ""}`,
        );
      }

      const result = await response.json();
      console.log("CAN interface setup successful:", result.message);
    } catch (error) {
      // If API fails, try to connect anyway (interface might already be up)
      console.warn(
        "CAN setup API not available, trying direct connection:",
        error,
      );
    }
  }

  private setupMessageHandling(): void {
    if (!this.socketcanWorker) return;

    this.socketcanWorker.addEventListener("message", (event) => {
      if (event.data.type === "message") {
        const canMessage: CANMessage = {
          id: event.data.message.id,
          data: new Uint8Array(event.data.message.data),
          timestamp: new Date(),
        };

        // Notify all listeners
        this.messageListeners.forEach((listener) => {
          try {
            listener(canMessage);
          } catch (error) {
            console.error("Error in message listener:", error);
          }
        });
      }
    });
  }

  private async waitForMessage(
    expectedId: number,
    timeoutMs: number,
  ): Promise<CANMessage> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.removeMessageListener(messageListener);
        reject(
          new HellaProgError(
            `Timeout waiting for CAN message ID ${expectedId.toString(16)}`,
          ),
        );
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

  if (canInterface.type === "socketcan") {
    return /^can\d+$/.test(canInterface.channel);
  }

  if (canInterface.type === "slcan") {
    return /^\/dev\/tty(USB|ACM)\d+$/.test(canInterface.channel);
  }

  return false; // Only socketcan and slcan are supported
}
