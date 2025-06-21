import React from 'react';
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
  Grid,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import { CheckCircle, Folder, Warning } from '@mui/icons-material';

const steps = ['Connect CAN', 'Configure Actuator', 'Read Memory', 'Analyze'];

function Dashboard() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Welcome to Hella Turbo Controller
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              <strong>🎉 New TypeScript Version!</strong> This is the modern, 
              cross-platform version built with Electron + React + Material-UI.
            </Alert>

            <Typography variant="h6" gutterBottom>
              🔧 What's New:
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon><CheckCircle color="primary" /></ListItemIcon>
                <ListItemText primary="Cross-platform GUI (Windows, Mac, Linux)" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="primary" /></ListItemIcon>
                <ListItemText primary="TypeScript for better safety and development" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="primary" /></ListItemIcon>
                <ListItemText primary="Modern React + Material-UI Design" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="primary" /></ListItemIcon>
                <ListItemText primary="Enhanced memory visualization" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="primary" /></ListItemIcon>
                <ListItemText primary="Real-time CAN monitoring" />
              </ListItem>
            </List>

            <Alert severity="warning" sx={{ mt: 3 }}>
              <Warning sx={{ mr: 1 }} />
              <strong>Safety First!</strong> This tool can permanently damage actuators 
              if used incorrectly. Always backup memory dumps and understand the analysis 
              before making changes.
            </Alert>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Start
            </Typography>
            <Stepper orientation="vertical" activeStep={0}>
              {steps.map((label, index) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Legacy Python Version
            </Typography>
            <Typography variant="body1" paragraph>
              The original Python CLI tools are available in the{' '}
              <code>legacy-python/</code> folder.
            </Typography>
            <Button variant="outlined" startIcon={<Folder />}>
              View Legacy Tools
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;