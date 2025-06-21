import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Container,
  IconButton,
} from '@mui/material';
import {
  CarRepair,
  Dashboard,
  Memory,
  Monitor,
  Analytics,
  Brightness4,
  Brightness7,
} from '@mui/icons-material';

import DashboardView from './components/Dashboard';
import ActuatorManager from './components/ActuatorManager';
import MemoryViewer from './components/MemoryViewer';
import CANMonitor from './components/CANMonitor';
import Analysis from './components/Analysis';

const DRAWER_WIDTH = 240;

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: <Dashboard />, component: DashboardView },
  { id: 'actuator', label: 'Actuator Manager', icon: <CarRepair />, component: ActuatorManager },
  { id: 'memory', label: 'Memory Viewer', icon: <Memory />, component: MemoryViewer },
  { id: 'monitor', label: 'CAN Monitor', icon: <Monitor />, component: CANMonitor },
  { id: 'analysis', label: 'Analysis', icon: <Analytics />, component: Analysis },
];

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [darkMode, setDarkMode] = useState(false);

  const CurrentComponent = menuItems.find(item => item.id === currentView)?.component || DashboardView;

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: `calc(100% - ${DRAWER_WIDTH}px)`,
          ml: `${DRAWER_WIDTH}px`,
        }}
      >
        <Toolbar>
          <CarRepair sx={{ mr: 2 }} />
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Hella Turbo Controller
          </Typography>
          <IconButton
            size="large"
            edge="end"
            color="inherit"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <Toolbar />
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.id} disablePadding>
              <ListItemButton
                selected={currentView === item.id}
                onClick={() => setCurrentView(item.id)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
        }}
      >
        <Toolbar />
        <Container maxWidth="xl">
          <CurrentComponent />
        </Container>
      </Box>
    </Box>
  );
}

export default App;