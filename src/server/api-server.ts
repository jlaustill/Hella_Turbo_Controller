/**
 * Simple API server for CAN interface setup
 * Handles system-level CAN interface configuration
 */

import express from "express";
import cors from "cors";
import { spawn } from "child_process";
import { createServer } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { URL } from "url";

// Type definitions for socketcan (no @types available)
interface SocketCANChannel {
  start(): void;
  stop(): void;
  send(message: { id: number; ext: boolean; rtr: boolean; data: Buffer }): void;
  addListener(
    event: "onMessage",
    callback: (msg: { id: number; data: Buffer }) => void,
  ): void;
}

interface SocketCAN {
  createRawChannel(channel: string, timestamps?: boolean): SocketCANChannel;
}

// Import socketcan library
const socketcan: SocketCAN = require("socketcan");
const socketcanPackageJson = require("../../../node_modules/socketcan/package.json");

const app = express();
const PORT = process.env.API_PORT || 3001;

app.use(cors());
app.use(express.json());

interface CANSetupRequest {
  channel: string;
  bitrate: number;
}

interface CANSetupResponse {
  success: boolean;
  message: string;
  channel?: string;
  bitrate?: number;
}

/**
 * Setup CAN interface endpoint
 * POST /api/can-setup
 */
app.post("/api/can-setup", async (req, res) => {
  try {
    const { channel, bitrate = 500000 }: CANSetupRequest = req.body;

    if (!channel) {
      return res.status(400).json({
        success: false,
        message: "Channel is required",
      } as CANSetupResponse);
    }

    // Validate channel format
    if (!/^can\d+$/.test(channel)) {
      return res.status(400).json({
        success: false,
        message: "Invalid channel format. Expected format: can0, can1, etc.",
      } as CANSetupResponse);
    }

    console.log(`Setting up CAN interface: ${channel} at ${bitrate} bps`);

    // Try to setup the CAN interface
    const setupResult = await setupCANInterface(channel, bitrate);

    if (setupResult.success) {
      return res.json({
        success: true,
        message: `CAN interface ${channel} setup successfully`,
        channel,
        bitrate,
      } as CANSetupResponse);
    }

    return res.status(500).json({
      success: false,
      message: setupResult.message,
    } as CANSetupResponse);
  } catch (error: any) {
    console.error("CAN setup error:", error);
    return res.status(500).json({
      success: false,
      message: `CAN setup failed: ${error.message}`,
    } as CANSetupResponse);
  }
});

/**
 * Get CAN interface status
 * GET /api/can-status/:channel
 */
app.get("/api/can-status/:channel", async (req, res) => {
  try {
    const { channel } = req.params;

    if (!/^can\d+$/.test(channel)) {
      return res.status(400).json({
        success: false,
        message: "Invalid channel format",
      });
    }

    const status = await getCANStatus(channel);
    return res.json(status);
  } catch (error: any) {
    return res.status(500).json({
      success: false,
      message: `Failed to get CAN status: ${error.message}`,
    });
  }
});

/**
 * List available CAN interfaces
 * GET /api/can-interfaces
 */
app.get("/api/can-interfaces", async (req, res) => {
  try {
    const interfaces = await listCANInterfaces();
    res.json({
      success: true,
      interfaces,
    });
  } catch (error: any) {
    res.status(500).json({
      success: false,
      message: `Failed to list CAN interfaces: ${error.message}`,
    });
  }
});

/**
 * Setup CAN interface using system commands
 */
async function setupCANInterface(
  channel: string,
  bitrate: number,
): Promise<{ success: boolean; message: string }> {
  return new Promise((resolve) => {
    // Commands to setup CAN interface
    const commands = [
      `sudo ip link set ${channel} down`,
      `sudo ip link set ${channel} type can bitrate ${bitrate}`,
      `sudo ip link set ${channel} up`,
    ];

    let commandIndex = 0;

    const executeNextCommand = () => {
      if (commandIndex >= commands.length) {
        resolve({ success: true, message: "CAN interface setup completed" });
        return;
      }

      const command = commands[commandIndex];
      console.log(`Executing: ${command}`);

      const [cmd, ...args] = command.split(" ");
      const process = spawn(cmd, args);

      let stderr = "";

      process.stdout?.on("data", () => {
        // Ignore stdout for this command
      });

      process.stderr?.on("data", (data) => {
        stderr += data.toString();
      });

      process.on("close", (code) => {
        if (code === 0) {
          commandIndex++;
          executeNextCommand();
        } else {
          console.error(`Command failed with code ${code}: ${stderr}`);
          resolve({
            success: false,
            message: `Command failed: ${command}. Error: ${stderr || "Unknown error"}. Note: This may require sudo privileges.`,
          });
        }
      });

      process.on("error", (error) => {
        console.error(`Command error: ${error.message}`);
        resolve({
          success: false,
          message: `Command error: ${error.message}. Note: This may require sudo privileges or the interface may not exist.`,
        });
      });
    };

    executeNextCommand();
  });
}

/**
 * Get CAN interface status
 */
async function getCANStatus(channel: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const process = spawn("ip", ["link", "show", channel]);

    let stdout = "";

    process.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    process.stderr.on("data", () => {
      // Ignore stderr for status check
    });

    process.on("close", (code) => {
      if (code === 0) {
        const isUp = stdout.includes("UP");
        const isRunning = stdout.includes("RUNNING");

        let status: string;
        if (isUp) {
          status = isRunning ? "running" : "up";
        } else {
          status = "down";
        }

        resolve({
          success: true,
          channel,
          status,
          details: stdout.trim(),
        });
      } else {
        resolve({
          success: false,
          channel,
          status: "not_found",
          message: `Interface ${channel} not found`,
        });
      }
    });

    process.on("error", (error) => {
      reject(new Error(`Failed to check CAN status: ${error.message}`));
    });
  });
}

/**
 * List available CAN interfaces
 */
async function listCANInterfaces(): Promise<string[]> {
  return new Promise((resolve, reject) => {
    const process = spawn("ip", ["link", "show", "type", "can"]);

    let stdout = "";

    process.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    process.stderr.on("data", () => {
      // Ignore stderr for interface listing
    });

    process.on("close", (code) => {
      if (code === 0) {
        // Parse interface names from output
        const interfaces = stdout
          .split("\n")
          .filter((line) => line.includes(":"))
          .map((line) => {
            const match = line.match(/\d+:\s+(\w+):/);
            return match ? match[1] : null;
          })
          .filter((name) => name && name.startsWith("can"));

        resolve(interfaces as string[]);
      } else {
        resolve([]); // No CAN interfaces found
      }
    });

    process.on("error", (error) => {
      reject(new Error(`Failed to list CAN interfaces: ${error.message}`));
    });
  });
}

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    message: "CAN API server is running",
    timestamp: new Date().toISOString(),
  });
});

// CAN WebSocket bridge functionality
interface CANConnection {
  channel: string;
  socket?: SocketCANChannel; // socketcan socket
  clients: Set<WebSocket>;
}

const canConnections = new Map<string, CANConnection>();

/**
 * Setup real CAN socket connection
 */
async function setupRealCANSocket(channel: string): Promise<SocketCANChannel> {
  // First, ensure CAN interface is up
  await setupCANInterface(channel, 500000);

  // Create real CAN socket using imported socketcan library
  const socket = socketcan.createRawChannel(channel, true);

  console.log(
    `Setting up real CAN socket for ${channel} using socketcan library`,
  );
  return socket;
}

// Start server with WebSocket support
if (require.main === module) {
  const server = createServer(app);

  // Create WebSocket server
  const wss = new WebSocketServer({
    server,
    path: "/ws/can/*",
  });

  wss.on("connection", async (ws, req) => {
    try {
      const url = new URL(req.url!, `http://${req.headers.host}`);
      const pathParts = url.pathname.split("/");
      const channel = pathParts[pathParts.length - 1]; // Extract channel from /ws/can/can0

      if (!channel || !/^can\d+$/.test(channel)) {
        ws.close(1008, "Invalid channel format");
        return;
      }

      console.log(`WebSocket client connected for CAN channel: ${channel}`);

      // Get or create CAN connection
      let connection = canConnections.get(channel);
      if (!connection) {
        connection = {
          channel,
          clients: new Set(),
        };
        canConnections.set(channel, connection);

        // Setup real CAN socket - NEVER use mock/simulation
        connection.socket = await setupRealCANSocket(channel);

        // Setup message forwarding from CAN to WebSocket clients (using correct socketcan API)
        connection.socket.addListener("onMessage", (msg: any) => {
          const message = {
            type: "can_message",
            id: msg.id,
            data: Array.from(msg.data),
            timestamp: Date.now(),
          };

          console.log(
            `📡 Real CAN message received: ID=0x${msg.id.toString(16)}, Data=[${Array.from(
              msg.data,
            )
              .map((b: number) => `0x${b.toString(16).padStart(2, "0")}`)
              .join(", ")}]`,
          );

          connection!.clients.forEach((client) => {
            if (client.readyState === WebSocket.OPEN) {
              client.send(JSON.stringify(message));
            }
          });
        });

        connection.socket.start();
        console.log(`Real CAN socket started for ${channel}`);
      }

      // Add client to connection
      connection.clients.add(ws);

      // Handle incoming messages from WebSocket client
      ws.on("message", (data) => {
        try {
          const message = JSON.parse(data.toString());

          if (message.type === "send_can_message" && connection?.socket) {
            const canMessage = {
              id: message.id,
              ext: false,
              rtr: false,
              data: Buffer.from(message.data),
            };

            connection.socket.send(canMessage);
          }
        } catch (error) {
          console.error("Error handling WebSocket message:", error);
        }
      });

      // Handle client disconnect
      ws.on("close", () => {
        console.log(`WebSocket client disconnected from ${channel}`);
        if (connection) {
          connection.clients.delete(ws);

          // Clean up connection if no more clients
          if (connection.clients.size === 0) {
            if (connection.socket && connection.socket.stop) {
              connection.socket.stop();
            }
            canConnections.delete(channel);
            console.log(`Cleaned up CAN connection for ${channel}`);
          }
        }
      });

      // Send connection confirmation
      ws.send(
        JSON.stringify({
          type: "connected",
          channel,
          message: "Connected to CAN interface",
        }),
      );
    } catch (error: any) {
      console.error("WebSocket connection error:", error);
      ws.close(1011, "Internal server error");
    }
  });

  server.listen(PORT, () => {
    console.log(
      `🚀 CAN API server with WebSocket support running on port ${PORT}`,
    );
    console.log(
      `📡 Using mature Node.js socketcan library v${socketcanPackageJson.version}`,
    );
    console.log(`🌐 HTTP API: http://localhost:${PORT}/api/health`);
    console.log(`🔌 WebSocket: ws://localhost:${PORT}/ws/can/{channel}`);
    console.log(`✅ Ready for real CAN hardware communication!`);
  });
} else {
  module.exports = app;
}

export default app;
