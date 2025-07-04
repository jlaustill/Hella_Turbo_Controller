import express, { Request, Response } from "express";
import cors from "cors";
import { createServer, Server } from "http";
import CanService from "../domain/CanService";
import ICanInterface from "../types/ICanInterface";
import IHttpRequest from "./types/IHttpRequest";

class RestServer {
  private app: express.Application;
  private server: Server | null = null;
  private canService: CanService;

  constructor() {
    this.app = express();
    this.canService = new CanService();
    this.setupMiddleware();
    this.setupRoutes();
  }

  start(port: number): void {
    this.server = createServer(this.app);
    this.server.listen(port, () => {
      console.log(`🌐 REST API server running on port ${port}`);
      console.log(`📊 Health check: http://localhost:${port}/api/health`);
    });
  }

  stop(): void {
    if (this.server) {
      this.server.close();
      this.server = null;
    }
  }

  getHttpServer(): Server | null {
    return this.server;
  }

  getCanService(): CanService {
    return this.canService;
  }

  private setupMiddleware(): void {
    this.app.use(cors());
    this.app.use(express.json());
  }

  private setupRoutes(): void {
    // Health check
    this.app.get("/api/health", (_req, res) => {
      res.json({
        success: true,
        message: "CAN API server is running",
        timestamp: new Date().toISOString(),
        status: this.canService.getStatus(),
      });
    });

    // CAN interface setup
    this.app.post("/api/can-setup", async (req: Request, res: Response) => {
      try {
        const { channel, bitrate = 500000, sudoPassword }: IHttpRequest = req.body;

        if (!channel) {
          return res.status(400).json({
            success: false,
            message: "Channel is required",
          });
        }

        if (!sudoPassword) {
          return res.status(400).json({
            success: false,
            message: "Sudo password is required",
          });
        }

        if (!/^can\d+$/.test(channel)) {
          return res.status(400).json({
            success: false,
            message:
              "Invalid channel format. Expected format: can0, can1, etc.",
          });
        }

        const canInterface: ICanInterface = {
          type: "socketcan",
          channel,
          bitrate,
        };

        await this.canService.connect(canInterface, sudoPassword);

        return res.json({
          success: true,
          message: `CAN interface ${channel} setup successfully`,
          channel,
          bitrate,
        });
      } catch (error: any) {
        console.error("CAN setup error:", error);
        return res.status(500).json({
          success: false,
          message: `CAN setup failed: ${error.message}`,
        });
      }
    });

    // Get CAN status
    this.app.get("/api/can-status", (_req, res) => {
      res.json({
        success: true,
        status: this.canService.getStatus(),
      });
    });
  }
}

export default RestServer;
