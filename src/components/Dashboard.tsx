// import React from "react"; // Not needed in React 17+
import {
  Typography,
  Paper,
  Box,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Button,
  Stepper,
  Step,
  StepLabel,
} from "@mui/material";
import { CheckCircle, Folder, Warning } from "@mui/icons-material";

const steps = ["Connect CAN", "Configure Actuator", "Read Memory", "Analyze"];

function Dashboard() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Welcome to Hella Turbo Controller
      </Typography>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Box sx={{ mb: 2 }}>
          <Paper sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              <strong>🎉 New TypeScript Version!</strong> This is the modern,
              cross-platform version built with Electron + React + Material-UI.
            </Alert>

            <Typography variant="h6" gutterBottom>
              🔧 What&apos;s New:
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <CheckCircle color="primary" />
                </ListItemIcon>
                <ListItemText primary="Cross-platform GUI (Windows, Mac, Linux)" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <CheckCircle color="primary" />
                </ListItemIcon>
                <ListItemText primary="TypeScript for better safety and development" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <CheckCircle color="primary" />
                </ListItemIcon>
                <ListItemText primary="Modern React + Material-UI Design" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <CheckCircle color="primary" />
                </ListItemIcon>
                <ListItemText primary="Enhanced memory visualization" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <CheckCircle color="primary" />
                </ListItemIcon>
                <ListItemText primary="Real-time CAN monitoring" />
              </ListItem>
            </List>

            <Alert severity="warning" sx={{ mt: 3 }}>
              <Warning sx={{ mr: 1 }} />
              <strong>Safety First!</strong> This tool can permanently damage
              actuators if used incorrectly. Always backup memory dumps and
              understand the analysis before making changes.
            </Alert>
          </Paper>
        </Box>

        <Box sx={{ mb: 2, flex: 1 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Start
            </Typography>
            <Stepper orientation="vertical" activeStep={0}>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>
        </Box>

        <Box sx={{ mb: 2, flex: 1 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Legacy Python Version
            </Typography>
            <Typography variant="body1" paragraph>
              The original Python CLI tools are available in the{" "}
              <code>legacy-python/</code> folder.
            </Typography>
            <Button variant="outlined" startIcon={<Folder />}>
              View Legacy Tools
            </Button>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}

export default Dashboard;
