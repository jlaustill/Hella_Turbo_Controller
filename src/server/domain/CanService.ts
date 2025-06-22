import CanBus from "../data/CanBus";
import ICanMessage from "../types/ICanMessage";
import ICanInterface from "../types/ICanInterface";
import EConnectionStatus from "../types/EConnectionStatus";
import TMessageHandler from "./types/TMessageHandler";

class CanService {
  private canBus: CanBus;
  private status: EConnectionStatus = EConnectionStatus.DISCONNECTED;
  private messageHandlers: TMessageHandler[] = [];

  // Hella CAN IDs
  static readonly HELLA_CAN_IDS = {
    REQUEST: 0x3f0,
    MEMORY_RESPONSE: 0x3e8,
    POSITION_RESPONSE: 0x3ea,
    ACK_RESPONSE: 0x3eb,
  };

  constructor() {
    this.canBus = new CanBus();
    this.setupMessageHandling();
  }

  async connect(canInterface: ICanInterface, sudoPassword: string): Promise<void> {
    try {
      this.status = EConnectionStatus.CONNECTING;
      await this.canBus.connect(canInterface, sudoPassword);
      this.status = EConnectionStatus.CONNECTED;
    } catch (error) {
      this.status = EConnectionStatus.ERROR;
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    await this.canBus.disconnect();
    this.status = EConnectionStatus.DISCONNECTED;
  }

  getStatus(): EConnectionStatus {
    return this.status;
  }

  async sendMessage(id: number, data: Buffer): Promise<void> {
    if (this.status !== EConnectionStatus.CONNECTED) {
      throw new Error("CAN service not connected");
    }

    const message: ICanMessage = {
      id,
      data,
      timestamp: new Date(),
    };

    await this.canBus.send(message);
  }

  async readCurrentPosition(): Promise<number> {
    if (this.status !== EConnectionStatus.CONNECTED) {
      throw new Error("CAN service not connected");
    }

    // Send position request
    const requestData = Buffer.from([
      0x22, 0x00, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00,
    ]);
    await this.sendMessage(CanService.HELLA_CAN_IDS.REQUEST, requestData);

    // In real implementation, would wait for response
    // For now, return placeholder
    return 0x0180;
  }

  addMessageHandler(handler: TMessageHandler): void {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler: TMessageHandler): void {
    const index = this.messageHandlers.indexOf(handler);
    if (index !== -1) {
      this.messageHandlers.splice(index, 1);
    }
  }

  interpretMessage(message: ICanMessage): string {
    switch (message.id) {
      case CanService.HELLA_CAN_IDS.REQUEST:
        if (message.data[0] === 0x22) return "Memory read request";
        if (message.data[0] === 0x2e) return "Memory write request";
        return "Request message";
      case CanService.HELLA_CAN_IDS.MEMORY_RESPONSE:
        return "Memory data response";
      case CanService.HELLA_CAN_IDS.POSITION_RESPONSE:
        if (message.data.length >= 4) {
          const position = (message.data[2] << 8) | message.data[3];
          return `Position: 0x${position.toString(16).toUpperCase()}`;
        }
        return "Position update";
      case CanService.HELLA_CAN_IDS.ACK_RESPONSE:
        return "Acknowledgment";
      default:
        return `Unknown message ID: 0x${message.id.toString(16)}`;
    }
  }

  private setupMessageHandling(): void {
    this.canBus.addMessageListener((message: ICanMessage) => {
      // Forward to all handlers
      this.messageHandlers.forEach((handler) => {
        try {
          handler(message);
        } catch (error) {
          console.error("Error in message handler:", error);
        }
      });
    });
  }
}

export default CanService;
