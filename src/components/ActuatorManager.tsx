import React, { useState } from 'react';
import {
  Typography,
  Paper,
  Box,
  Alert,
  Grid,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import { Wifi, WifiOff, Refresh, Update, AutoFixHigh, Download } from '@mui/icons-material';

interface ActuatorManagerProps {
  canConnected?: boolean;
}

function ActuatorManager({ canConnected = false }: ActuatorManagerProps) {
  const [newMinPosition, setNewMinPosition] = useState('');
  const [newMaxPosition, setNewMaxPosition] = useState('');

  const actuatorInfo = {
    type: 'Hella Universal Turbo Actuator I',
    currentPosition: '0x0180',
    minPosition: '0x0113',
    maxPosition: '0x0220',
  };


  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Actuator Management
      </Typography>

      <Alert severity="warning" sx={{ mb: 3 }}>
        <strong>⚠️ Safety Warning</strong> Incorrect configuration can permanently 
        damage your actuator. Always backup memory before making changes.
      </Alert>

      {!canConnected && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <strong>Note:</strong> Connect to your CAN interface using the sidebar 
          to enable actuator management features.
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Actuator Information
            </Typography>
            
            <List>
              <ListItem>
                <ListItemText 
                  primary="Type" 
                  secondary={actuatorInfo.type} 
                />
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
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Position Configuration
            </Typography>
            
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="New Min Position (hex)"
                  value={newMinPosition}
                  onChange={(e) => setNewMinPosition(e.target.value)}
                  placeholder="0x0113"
                  disabled={!canConnected}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="New Max Position (hex)"
                  value={newMaxPosition}
                  onChange={(e) => setNewMaxPosition(e.target.value)}
                  placeholder="0x0220"
                  disabled={!canConnected}
                />
              </Grid>
              <Grid item xs={12} md={4} sx={{ display: 'flex', alignItems: 'center' }}>
                <Button
                  fullWidth
                  variant="contained"
                  color="warning"
                  startIcon={<Update />}
                  disabled={!canConnected || !newMinPosition || !newMaxPosition}
                >
                  Update Positions
                </Button>
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            <Box sx={{ display: 'flex', gap: 2 }}>
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
        </Grid>
      </Grid>
    </Box>
  );
}

export default ActuatorManager;