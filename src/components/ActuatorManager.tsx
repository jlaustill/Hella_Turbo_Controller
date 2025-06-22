import { useState } from "react";
import {
  Typography,
  Paper,
  Box,
  Alert,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  Divider,
} from "@mui/material";
import { Refresh, Update, AutoFixHigh, Download } from "@mui/icons-material";

interface ActuatorManagerProps {
  canConnected?: boolean;
}

function ActuatorManager({ canConnected = false }: ActuatorManagerProps) {
  const [newMinPosition, setNewMinPosition] = useState("");
  const [newMaxPosition, setNewMaxPosition] = useState("");

  const actuatorInfo = {
    type: "Hella Universal Turbo Actuator I",
    currentPosition: "0x0180",
    minPosition: "0x0113",
    maxPosition: "0x0220",
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Actuator Management
      </Typography>

      <Alert severity="warning" sx={{ mb: 3 }}>
        <strong>⚠️ Safety Warning</strong> Incorrect configuration can
        permanently damage your actuator. Always backup memory before making
        changes.
      </Alert>

      {!canConnected && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <strong>Note:</strong> Connect to your CAN interface using the sidebar
          to enable actuator management features.
        </Alert>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Box sx={{ mb: 2 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Actuator Information
            </Typography>

            <List>
              <ListItem>
                <ListItemText primary="Type" secondary={actuatorInfo.type} />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Current Position"
                  secondary={actuatorInfo.currentPosition}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Min Position"
                  secondary={actuatorInfo.minPosition}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Max Position"
                  secondary={actuatorInfo.maxPosition}
                />
              </ListItem>
            </List>

            <Button
              variant="outlined"
              startIcon={<Refresh />}
              disabled={!canConnected}
              sx={{ mt: 2 }}
            >
              Refresh Info
            </Button>
          </Paper>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Position Configuration
            </Typography>

            <Box
              sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 3 }}
            >
              <Box sx={{ mb: 2, flex: 1 }}>
                <TextField
                  fullWidth
                  label="New Min Position (hex)"
                  value={newMinPosition}
                  onChange={(e) => setNewMinPosition(e.target.value)}
                  placeholder="0x0113"
                  disabled={!canConnected}
                />
              </Box>
              <Box sx={{ mb: 2, flex: 1 }}>
                <TextField
                  fullWidth
                  label="New Max Position (hex)"
                  value={newMaxPosition}
                  onChange={(e) => setNewMaxPosition(e.target.value)}
                  placeholder="0x0220"
                  disabled={!canConnected}
                />
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <Button
                  fullWidth
                  variant="contained"
                  color="warning"
                  startIcon={<Update />}
                  disabled={!canConnected || !newMinPosition || !newMaxPosition}
                >
                  Update Positions
                </Button>
              </Box>
            </Box>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<AutoFixHigh />}
                disabled={!canConnected}
              >
                Auto Calibrate
              </Button>
              <Button
                variant="contained"
                color="info"
                startIcon={<Download />}
                disabled={!canConnected}
              >
                Read Memory
              </Button>
            </Box>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}

export default ActuatorManager;
