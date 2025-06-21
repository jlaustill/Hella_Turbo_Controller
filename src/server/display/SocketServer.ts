import { WebSocketServer, WebSocket } from 'ws';
import { Server } from 'http';
import { URL } from 'url';
import CanService from '../domain/CanService';
import ICanMessage from '../types/ICanMessage';
import IWebSocketClient from './types/IWebSocketClient';

class SocketServer {
  private wss: WebSocketServer | null = null;
  private canService: CanService;
  private clients: Map<string, IWebSocketClient> = new Map();

  constructor() {
    this.canService = new CanService();
    this.setupCanMessageForwarding();
  }

  start(httpServer: Server | null): void {
    if (!httpServer) {
      throw new Error('HTTP server required for WebSocket upgrade');
    }

    this.wss = new WebSocketServer({
      server: httpServer
    });

    this.wss.on('connection', this.handleConnection.bind(this));
    console.log(`🔌 WebSocket server started`);
  }

  stop(): void {
    if (this.wss) {
      this.wss.close();
      this.wss = null;
    }
    this.clients.clear();
  }

  private handleConnection(ws: WebSocket, req: any): void {
    try {
      const url = new URL(req.url!, `http://${req.headers.host}`);
      
      // Only handle /ws/can/* paths
      if (!url.pathname.startsWith('/ws/can/')) {
        ws.close(1008, 'Invalid WebSocket path');
        return;
      }
      
      const pathParts = url.pathname.split('/');
      const channel = pathParts[pathParts.length - 1];
      
      if (!channel || !/^can\d+$/.test(channel)) {
        ws.close(1008, 'Invalid channel format');
        return;
      }

      const clientId = this.generateClientId();
      const client: IWebSocketClient = {
        ws,
        channel,
        id: clientId
      };

      this.clients.set(clientId, client);
      console.log(`📱 WebSocket client connected: ${clientId} for channel ${channel}`);

      // Setup client event handlers
      ws.on('message', (data) => this.handleMessage(clientId, data));
      ws.on('close', () => this.handleDisconnect(clientId));
      ws.on('error', (error) => this.handleError(clientId, error));

      // Send connection confirmation
      this.sendToClient(clientId, {
        type: 'connected',
        channel: channel,
        message: 'Connected to CAN interface'
      });

    } catch (error) {
      console.error('WebSocket connection error:', error);
      ws.close(1011, 'Internal server error');
    }
  }

  private handleMessage(clientId: string, data: any): void {
    try {
      const message = JSON.parse(data.toString());
      
      if (message.type === 'send_can_message') {
        const canData = Buffer.from(message.data);
        this.canService.sendMessage(message.id, canData);
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }

  private handleDisconnect(clientId: string): void {
    const client = this.clients.get(clientId);
    if (client) {
      console.log(`📱 WebSocket client disconnected: ${clientId}`);
      this.clients.delete(clientId);
    }
  }

  private handleError(clientId: string, error: Error): void {
    console.error(`WebSocket client error ${clientId}:`, error);
  }

  private setupCanMessageForwarding(): void {
    this.canService.addMessageHandler((message: ICanMessage) => {
      const wsMessage = {
        type: 'can_message',
        id: message.id,
        data: Array.from(message.data),
        timestamp: message.timestamp.getTime()
      };

      // Send to all connected clients
      this.clients.forEach(client => {
        this.sendToClient(client.id, wsMessage);
      });
    });
  }

  private sendToClient(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (client && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(message));
    }
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

export default SocketServer;