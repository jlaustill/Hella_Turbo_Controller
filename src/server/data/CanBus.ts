// Import socketcan library
import * as socketcan from "socketcan";
import { spawn } from "child_process";
import ICanMessage from "../types/ICanMessage";
import ICanInterface from "../types/ICanInterface";
import ISocketCanChannel from "./types/ISocketCanChannel";

class CanBus {
  private socket: ISocketCanChannel | null = null;
  private messageListeners: Array<(message: ICanMessage) => void> = [];

  async connect(canInterface: ICanInterface): Promise<void> {
    // Setup CAN interface first
    await this.setupCANInterface(
      canInterface.channel,
      canInterface.bitrate || 500000,
    );

    // Create socketcan channel
    this.socket = socketcan.createRawChannel(canInterface.channel, true);

    // Setup message forwarding
    this.socket.addListener("onMessage", (msg) => {
      const message: ICanMessage = {
        id: msg.id,
        data: msg.data,
        timestamp: new Date(),
      };

      this.messageListeners.forEach((listener) => listener(message));
    });

    // Start the channel
    this.socket.start();
    console.log(
      `📡 Real CAN socket started for ${canInterface.channel} using socketcan library`,
    );
  }

  async disconnect(): Promise<void> {
    if (this.socket) {
      this.socket.stop();
      this.socket = null;
    }
    this.messageListeners = [];
  }

  async send(message: ICanMessage): Promise<void> {
    if (!this.socket) {
      throw new Error("CAN interface not connected");
    }

    const canMessage = {
      id: message.id,
      ext: message.extended || false,
      rtr: message.remote || false,
      data: message.data,
    };

    this.socket.send(canMessage);
  }

  addMessageListener(listener: (message: ICanMessage) => void): void {
    this.messageListeners.push(listener);
  }

  removeMessageListener(listener: (message: ICanMessage) => void): void {
    const index = this.messageListeners.indexOf(listener);
    if (index !== -1) {
      this.messageListeners.splice(index, 1);
    }
  }

  private async setupCANInterface(
    channel: string,
    bitrate: number,
  ): Promise<void> {
    const commands = [
      `sudo ip link set ${channel} down`,
      `sudo ip link set ${channel} type can bitrate ${bitrate}`,
      `sudo ip link set ${channel} up`,
    ];

    // Execute commands sequentially using reduce to avoid await-in-loop
    await commands.reduce(async (previousPromise, command) => {
      await previousPromise;
      try {
        await this.executeCommand(command);
      } catch (error) {
        console.warn(
          `CAN setup command failed: ${command}. Interface may already be configured.`,
        );
      }
    }, Promise.resolve());
  }

  private executeCommand(command: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const [cmd, ...args] = command.split(" ");
      const process = spawn(cmd, args);

      process.on("close", (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`Command failed with code ${code}`));
        }
      });

      process.on("error", (error) => {
        reject(error);
      });
    });
  }
}

export default CanBus;
