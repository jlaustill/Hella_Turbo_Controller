import { WebSocket } from "ws";

interface IWebSocketClient {
  ws: WebSocket;
  channel: string;
  id: string;
}

export default IWebSocketClient;
