import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Chip,
  Button,
  Card,
  CardContent,
  CardActions,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
} from '@mui/material';
import {
  Cable,
  CheckCircle,
  Error,
  Warning,
  PlayArrow,
  Stop,
  ExpandMore,
  ExpandLess,
  SignalCellularAlt,
  Speed,
  Memory,
  Settings,
  Refresh,
} from '@mui/icons-material';
import { CANService, createCANService, type CANMessage as ServiceCANMessage, type CANInterface } from '../services/canService';

interface CANStatusSidebarProps {
  onConnectionChange?: (connected: boolean) => void;
}

function CANStatusSidebar({ onConnectionChange }: CANStatusSidebarProps) {
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [messageCount, setMessageCount] = useState(0);
  const [messagesPerSecond, setMessagesPerSecond] = useState(0);
  const [lastMessage, setLastMessage] = useState<string>('');
  const [showDetails, setShowDetails] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedInterface, setSelectedInterface] = useState<'socketcan' | 'slcan'>('socketcan');
  const [channel, setChannel] = useState('can0');
  const [availableInterfaces, setAvailableInterfaces] = useState<string[]>([]);
  const canServiceRef = useRef<CANService | null>(null);
  const messageTimestamps = useRef<number[]>([]);

  // Load available interfaces on component mount
  useEffect(() => {
    loadAvailableInterfaces();
  }, []);

  // Initialize CAN service
  useEffect(() => {
    const initializeCAN = async () => {
      if (!canServiceRef.current) {
        const canInterface: CANInterface = {
          type: selectedInterface,
          channel: channel
        };
        
        canServiceRef.current = createCANService(canInterface);
        
        // Set up message listener
        const messageListener = (serviceMessage: ServiceCANMessage) => {
          const now = Date.now();
          messageTimestamps.current.push(now);
          
          // Keep only last 10 seconds of timestamps
          messageTimestamps.current = messageTimestamps.current.filter(ts => now - ts < 10000);
          
          setMessageCount(prev => prev + 1);
          setLastMessage(`0x${serviceMessage.id.toString(16).toUpperCase()}: ${Array.from(serviceMessage.data).map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ')}`);
        };

        canServiceRef.current.addMessageListener(messageListener);
      }
    };

    initializeCAN();

    return () => {
      if (canServiceRef.current) {
        canServiceRef.current.disconnect();
      }
    };
  }, [selectedInterface, channel]);

  // Update messages per second
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      const recentMessages = messageTimestamps.current.filter(ts => now - ts < 1000);
      setMessagesPerSecond(recentMessages.length);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Notify parent of connection changes
  useEffect(() => {
    onConnectionChange?.(connectionStatus === 'connected');
  }, [connectionStatus, onConnectionChange]);

  const loadAvailableInterfaces = async () => {
    try {
      const apiUrl = process.env.NODE_ENV === 'development' 
        ? 'http://localhost:3001/api/can-interfaces'
        : '/api/can-interfaces';
        
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.interfaces) {
          setAvailableInterfaces(data.interfaces);
        }
      }
    } catch (error) {
      console.warn('Could not load available CAN interfaces:', error);
      // Set default interfaces if API fails
      setAvailableInterfaces(['can0', 'can1']);
    }
  };

  const handleInterfaceChange = (newInterface: 'socketcan' | 'slcan') => {
    setSelectedInterface(newInterface);
    // Update default channel based on interface type
    if (newInterface === 'socketcan') {
      setChannel('can0');
    } else {
      setChannel('/dev/ttyUSB0');
    }
  };

  const handleConnect = async () => {
    if (!canServiceRef.current) return;

    if (connectionStatus === 'connected') {
      await canServiceRef.current.disconnect();
      setConnectionStatus('disconnected');
      setMessageCount(0);
      setMessagesPerSecond(0);
      setLastMessage('');
      messageTimestamps.current = [];
    } else {
      try {
        setConnectionStatus('connecting');
        setErrorMessage('');
        await canServiceRef.current.connect();
        setConnectionStatus('connected');
      } catch (error: any) {
        setConnectionStatus('error');
        setErrorMessage(error.message || 'Failed to connect to CAN interface');
      }
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'success';
      case 'connecting': return 'info';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'connected': return <CheckCircle />;
      case 'connecting': return <Cable />;
      case 'error': return <Error />;
      default: return <Warning />;
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'error': return 'Error';
      default: return 'Disconnected';
    }
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Cable sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6" component="div">
            CAN Status
          </Typography>
        </Box>

        <Box sx={{ mb: 2 }}>
          <Chip
            icon={getStatusIcon()}
            label={getStatusText()}
            color={getStatusColor()}
            variant="filled"
            size="small"
            sx={{ width: '100%', justifyContent: 'flex-start' }}
          />
        </Box>

        {connectionStatus === 'error' && (
          <Alert severity="error" sx={{ mb: 2, fontSize: '0.75rem' }}>
            {errorMessage}
          </Alert>
        )}

        {connectionStatus === 'connected' && (
          <>
            <List dense sx={{ py: 0 }}>
              <ListItem sx={{ px: 0, py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <SignalCellularAlt fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={`${messageCount} messages`}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
              <ListItem sx={{ px: 0, py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <Speed fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={`${messagesPerSecond} msg/s`}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
            </List>

            <Button
              size="small"
              onClick={() => setShowDetails(!showDetails)}
              endIcon={showDetails ? <ExpandLess /> : <ExpandMore />}
              sx={{ mt: 1, width: '100%' }}
            >
              Details
            </Button>

            <Collapse in={showDetails}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="caption" color="text.secondary">
                Interface: {selectedInterface} ({channel})
              </Typography>
              {lastMessage && (
                <>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                    Last Message:
                  </Typography>
                  <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.65rem' }}>
                    {lastMessage}
                  </Typography>
                </>
              )}
            </Collapse>
          </>
        )}

        {/* Interface Settings */}
        <Box sx={{ mt: 2 }}>
          <Button
            size="small"
            onClick={() => setShowSettings(!showSettings)}
            startIcon={<Settings />}
            endIcon={showSettings ? <ExpandLess /> : <ExpandMore />}
            sx={{ width: '100%' }}
            disabled={connectionStatus === 'connected'}
          >
            Interface Setup
          </Button>

          <Collapse in={showSettings}>
            <Divider sx={{ my: 1 }} />
            
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Interface Type</InputLabel>
              <Select
                value={selectedInterface}
                label="Interface Type"
                onChange={(e) => handleInterfaceChange(e.target.value as 'socketcan' | 'slcan')}
                disabled={connectionStatus === 'connected'}
              >
                <MenuItem value="socketcan">SocketCAN</MenuItem>
                <MenuItem value="slcan">SLCAN</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                fullWidth
                size="small"
                label="Channel"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                disabled={connectionStatus === 'connected'}
                helperText={selectedInterface === 'socketcan' ? 'e.g., can0' : 'e.g., /dev/ttyUSB0'}
              />
              <IconButton 
                size="small" 
                onClick={loadAvailableInterfaces}
                disabled={connectionStatus === 'connected'}
                title="Refresh interfaces"
              >
                <Refresh />
              </IconButton>
            </Box>

            {availableInterfaces.length > 0 && selectedInterface === 'socketcan' && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Available: {availableInterfaces.join(', ')}
                </Typography>
              </Box>
            )}
          </Collapse>
        </Box>

        {connectionStatus === 'disconnected' && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Configure your CAN interface above, then connect to begin monitoring Hella turbo actuator traffic.
          </Typography>
        )}
      </CardContent>

      <CardActions sx={{ p: 2, pt: 0 }}>
        <Button
          fullWidth
          variant={connectionStatus === 'connected' ? 'outlined' : 'contained'}
          color={connectionStatus === 'connected' ? 'error' : 'primary'}
          startIcon={connectionStatus === 'connected' ? <Stop /> : <PlayArrow />}
          onClick={handleConnect}
          disabled={connectionStatus === 'connecting'}
          size="small"
        >
          {connectionStatus === 'connecting' ? 'Connecting...' : 
           connectionStatus === 'connected' ? 'Disconnect' : 'Connect'}
        </Button>
      </CardActions>
    </Card>
  );
}

export default CANStatusSidebar;