import React, { useState, useEffect, useRef } from "react";
import {
  Typography,
  Paper,
  Box,
  Button,
  Switch,
  FormControlLabel,
  TextField,
  Grid,
  Chip,
  Alert,
} from "@mui/material";
import { Clear } from "@mui/icons-material";
import {
  CANService,
  createCANService,
  type CANMessage as ServiceCANMessage,
  type CANInterface,
} from "../services/canService";

interface CANMessage {
  id: string;
  timestamp: Date;
  canId: string;
  data: string;
  interpretation?: string;
  type: "request" | "response" | "position" | "error";
}

function CANMonitor() {
  const [autoScroll, setAutoScroll] = useState(true);
  const [showTimestamps, setShowTimestamps] = useState(true);
  const [filterHella, setFilterHella] = useState(true);
  const [maxMessages, setMaxMessages] = useState("1000");
  const [messages, setMessages] = useState<CANMessage[]>([]);
  const [, setMessageCount] = useState(0);
  const [messagesPerSecond, setMessagesPerSecond] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);
  const canServiceRef = useRef<CANService | null>(null);

  const hellaCANIds = ["0x3F0", "0x3E8", "0x3EA", "0x3EB"];

  // Initialize CAN service for monitoring (connection handled by sidebar)
  useEffect(() => {
    const initializeCAN = async () => {
      if (!canServiceRef.current) {
        // Use socketcan for real hardware
        const canInterface: CANInterface = {
          type: "socketcan",
          channel: "can0",
        };

        canServiceRef.current = createCANService(canInterface);

        // Set up message listener
        const messageListener = (serviceMessage: ServiceCANMessage) => {
          const uiMessage: CANMessage = {
            id: Date.now().toString(),
            timestamp: serviceMessage.timestamp,
            canId: `0x${serviceMessage.id.toString(16).toUpperCase()}`,
            data: Array.from(serviceMessage.data)
              .map((b) => b.toString(16).padStart(2, "0").toUpperCase())
              .join(" "),
            type: getMessageType(serviceMessage.id),
            interpretation: interpretMessage(
              `0x${serviceMessage.id.toString(16).toUpperCase()}`,
              Array.from(serviceMessage.data)
                .map((b) => b.toString(16).padStart(2, "0").toUpperCase())
                .join(" "),
            ),
          };

          setMessages((prev) => {
            const updated = [uiMessage, ...prev];
            const maxMsg = parseInt(maxMessages, 10) || 1000;
            return updated.slice(0, maxMsg);
          });

          setMessageCount((prev) => prev + 1);
        };

        canServiceRef.current.addMessageListener(messageListener);
      }
    };

    initializeCAN();

    return () => {
      if (canServiceRef.current) {
        canServiceRef.current.removeMessageListener(() => {});
      }
    };
  }, [maxMessages]);

  // Auto-scroll to top when new messages arrive
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = 0;
    }
  }, [messages, autoScroll]);

  // Update messages per second
  useEffect(() => {
    const interval = setInterval(() => {
      const oneSecondAgo = new Date(Date.now() - 1000);
      const recentMessages = messages.filter(
        (msg) => msg.timestamp > oneSecondAgo,
      );
      setMessagesPerSecond(recentMessages.length);
    }, 1000);

    return () => clearInterval(interval);
  }, [messages]);

  const filteredMessages = filterHella
    ? messages.filter((msg) => hellaCANIds.includes(msg.canId))
    : messages;

  const getMessageType = (canId: number): CANMessage["type"] => {
    switch (canId) {
      case CANService.CAN_IDS.REQUEST:
        return "request";
      case CANService.CAN_IDS.MEMORY_RESPONSE:
        return "response";
      case CANService.CAN_IDS.POSITION_RESPONSE:
        return "position";
      case CANService.CAN_IDS.ACK_RESPONSE:
        return "response";
      default:
        return "response";
    }
  };

  const interpretMessage = (canId: string, data: string): string => {
    switch (canId) {
      case "0x3F0":
        if (data.startsWith("22")) return "Memory read request";
        if (data.startsWith("2E")) return "Memory write request";
        return "Request message";
      case "0x3E8":
        return "Memory data response";
      case "0x3EA": {
        const bytes = data.split(" ");
        if (bytes.length >= 4) {
          const position =
            (parseInt(bytes[2], 16) << 8) | parseInt(bytes[3], 16);
          return `Position: 0x${position.toString(16).toUpperCase()}`;
        }
        return "Position update";
      }
      case "0x3EB":
        return "Acknowledgment";
      default:
        return "";
    }
  };

  const getMessageColor = (type: CANMessage["type"]) => {
    switch (type) {
      case "request":
        return "#3b82f6";
      case "response":
        return "#10b981";
      case "position":
        return "#f59e0b";
      case "error":
        return "#ef4444";
      default:
        return "#6b7280";
    }
  };

  const formatTimestamp = (timestamp: Date) =>
    `${timestamp.toLocaleTimeString()}.${timestamp
      .getMilliseconds()
      .toString()
      .padStart(3, "0")}`;

  const clearMessages = () => {
    setMessages([]);
    setMessageCount(0);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        CAN Monitor
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        <strong>Note:</strong> CAN connection is managed in the left sidebar.
        This monitor displays real-time traffic when connected.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Monitor Controls
            </Typography>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                  />
                }
                label="Auto Scroll"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={showTimestamps}
                    onChange={(e) => setShowTimestamps(e.target.checked)}
                  />
                }
                label="Show Timestamps"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={filterHella}
                    onChange={(e) => setFilterHella(e.target.checked)}
                  />
                }
                label="Filter Hella Messages Only"
              />
              <TextField
                label="Max Messages"
                type="number"
                value={maxMessages}
                onChange={(e) => setMaxMessages(e.target.value)}
                size="small"
              />
              <Button
                variant="outlined"
                startIcon={<Clear />}
                onClick={clearMessages}
              >
                Clear Messages
              </Button>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Typography variant="h6">Message Log</Typography>
              <Box sx={{ display: "flex", gap: 1 }}>
                <Chip
                  label={`${filteredMessages.length} messages`}
                  color="primary"
                  size="small"
                />
                <Chip
                  label={`${messagesPerSecond} msg/s`}
                  color="secondary"
                  size="small"
                />
              </Box>
            </Box>

            <Box
              ref={logRef}
              sx={{
                height: 400,
                overflow: "auto",
                fontFamily: "monospace",
                fontSize: "0.875rem",
                backgroundColor: "#1e1e1e",
                color: "#ffffff",
                p: 2,
                borderRadius: 1,
              }}
            >
              {filteredMessages.map((message) => (
                <Box
                  key={message.id}
                  sx={{
                    display: "flex",
                    gap: 2,
                    py: 0.5,
                    borderBottom: "1px solid #333",
                  }}
                >
                  {showTimestamps && (
                    <Box sx={{ color: "#888", minWidth: 120 }}>
                      {formatTimestamp(message.timestamp)}
                    </Box>
                  )}
                  <Box
                    sx={{
                      color: getMessageColor(message.type),
                      minWidth: 60,
                      fontWeight: "bold",
                    }}
                  >
                    {message.canId}
                  </Box>
                  <Box sx={{ minWidth: 200 }}>{message.data}</Box>
                  {message.interpretation && (
                    <Box sx={{ color: "#aaa", fontStyle: "italic" }}>
                      {message.interpretation}
                    </Box>
                  )}
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default CANMonitor;
