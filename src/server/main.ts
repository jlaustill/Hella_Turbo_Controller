import RestServer from './display/RestServer';
import SocketServer from './display/SocketServer';

class ServerBootstrap {
  private restServer: RestServer;
  private socketServer: SocketServer;
  private readonly port = 3001;

  constructor() {
    this.restServer = new RestServer();
    this.socketServer = new SocketServer();
    this.setupGracefulShutdown();
  }

  start(): void {
    console.log('🚀 Starting Hella CAN Server...');
    console.log('📡 Using mature Node.js socketcan library');
    
    // Start REST server first
    this.restServer.start(this.port);
    
    // Start WebSocket server on same HTTP server
    this.socketServer.start(this.restServer.getHttpServer());
    
    console.log('✅ Server startup complete!');
    console.log(`🌐 REST API: http://localhost:${this.port}/api/health`);
    console.log(`🔌 WebSocket: ws://localhost:${this.port}/ws/can/{channel}`);
  }

  stop(): void {
    console.log('🛑 Shutting down server...');
    this.socketServer.stop();
    this.restServer.stop();
    console.log('✅ Server shutdown complete');
  }

  private setupGracefulShutdown(): void {
    process.on('SIGINT', () => {
      console.log('\n🛑 Received SIGINT, shutting down gracefully...');
      this.stop();
      process.exit(0);
    });

    process.on('SIGTERM', () => {
      console.log('🛑 Received SIGTERM, shutting down gracefully...');
      this.stop();
      process.exit(0);
    });
  }
}

// Bootstrap the server
const server = new ServerBootstrap();
server.start();