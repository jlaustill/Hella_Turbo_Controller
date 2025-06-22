/**
 * Web Worker for SocketCAN communication
 * Handles CAN bus operations in a separate thread to avoid blocking the UI
 */

let canSocket = null;
let isConnected = false;

// WebSocket-based CAN implementation for browser
class WebSocketCANSocket {
  constructor(channel) {
    this.channel = channel;
    this.websocket = null;
    this.messageListeners = [];
    this.isConnected = false;
  }

  async connect() {
    return new Promise((resolve, reject) => {
      try {
        // Connect to WebSocket server that bridges to real CAN
        const wsUrl = `ws://localhost:3001/ws/can/${this.channel}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
          console.log(
            `Connected to CAN interface via WebSocket: ${this.channel}`,
          );
          this.isConnected = true;
          resolve();
        };

        this.websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === "can_message") {
              this.messageListeners.forEach((listener) =>
                listener({
                  id: message.id,
                  data: message.data,
                  timestamp: message.timestamp || Date.now(),
                }),
              );
            }
          } catch (error) {
            console.error("Error parsing WebSocket message:", error);
          }
        };

        this.websocket.onerror = (error) => {
          console.error("WebSocket error:", error);
          reject(
            new Error(
              `WebSocket connection failed: ${error.message || "Unknown error"}`,
            ),
          );
        };

        this.websocket.onclose = () => {
          console.log("WebSocket connection closed");
          this.isConnected = false;
        };

        // Timeout for connection
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error("WebSocket connection timeout"));
          }
        }, 5000);
      } catch (error) {
        reject(
          new Error(`Failed to connect to WebSocket CAN: ${error.message}`),
        );
      }
    });
  }

  disconnect() {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    this.isConnected = false;
  }

  send(message) {
    if (!this.websocket || !this.isConnected) {
      throw new Error("WebSocket not connected");
    }

    const wsMessage = {
      type: "send_can_message",
      id: message.id,
      data: message.data,
    };

    this.websocket.send(JSON.stringify(wsMessage));
  }

  addMessageListener(listener) {
    this.messageListeners.push(listener);
  }

  removeMessageListener(listener) {
    const index = this.messageListeners.indexOf(listener);
    if (index !== -1) {
      this.messageListeners.splice(index, 1);
    }
  }
}

// Worker message handlers
self.addEventListener("message", async (event) => {
  const { type, channel, message } = event.data;

  try {
    switch (type) {
      case "connect":
        await connectToCAN(channel);
        break;

      case "disconnect":
        disconnectFromCAN();
        break;

      case "send":
        sendCANMessage(message);
        break;

      default:
        console.warn("Unknown message type:", type);
    }
  } catch (error) {
    self.postMessage({
      type: "error",
      message: error.message,
    });
  }
});

async function connectToCAN(channel) {
  try {
    canSocket = new WebSocketCANSocket(channel);
    await canSocket.connect();
    console.log("Connected to CAN interface via WebSocket");

    // Set up message forwarding to main thread
    canSocket.addMessageListener((message) => {
      self.postMessage({
        type: "message",
        message: message,
      });
    });

    isConnected = true;
    self.postMessage({
      type: "connected",
      channel: channel,
    });
  } catch (error) {
    self.postMessage({
      type: "error",
      message: `Failed to connect to CAN: ${error.message}`,
    });
  }
}

function disconnectFromCAN() {
  if (canSocket) {
    canSocket.disconnect();
    canSocket = null;
  }
  isConnected = false;

  self.postMessage({
    type: "disconnected",
  });
}

function sendCANMessage(message) {
  if (!canSocket || !isConnected) {
    throw new Error("CAN socket not connected");
  }

  canSocket.send({
    id: message.id,
    data: message.data,
  });
}

// Handle worker termination
self.addEventListener("beforeunload", () => {
  disconnectFromCAN();
});
