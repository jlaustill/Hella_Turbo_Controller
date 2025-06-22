import React, { useState } from "react";
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Container,
  IconButton,
  Tabs,
  Tab,
  Drawer,
} from "@mui/material";
import {
  CarRepair,
  Dashboard,
  Memory,
  Monitor,
  Analytics,
  Brightness4,
  Brightness7,
} from "@mui/icons-material";

import DashboardView from "./components/Dashboard";
import ActuatorManager from "./components/ActuatorManager";
import MemoryViewer from "./components/MemoryViewer";
import CANMonitor from "./components/CANMonitor";
import Analysis from "./components/Analysis";
import CANStatusSidebar from "./components/CANStatusSidebar";

const SIDEBAR_WIDTH = 280;

const theme = createTheme({
  palette: {
    mode: "light",
  },
});

const darkTheme = createTheme({
  palette: {
    mode: "dark",
  },
});

const menuItems = [
  { id: "dashboard", label: "Dashboard", icon: <Dashboard /> },
  { id: "actuator", label: "Actuator Manager", icon: <CarRepair /> },
  { id: "memory", label: "Memory Viewer", icon: <Memory /> },
  { id: "monitor", label: "CAN Monitor", icon: <Monitor /> },
  { id: "analysis", label: "Analysis", icon: <Analytics /> },
];

function App() {
  const [currentView, setCurrentView] = useState("dashboard");
  const [darkMode, setDarkMode] = useState(false);
  const [canConnected, setCanConnected] = useState(false);

  const renderCurrentComponent = () => {
    switch (currentView) {
      case "dashboard":
        return <DashboardView />;
      case "actuator":
        return <ActuatorManager canConnected={canConnected} />;
      case "memory":
        return <MemoryViewer />;
      case "monitor":
        return <CANMonitor />;
      case "analysis":
        return <Analysis />;
      default:
        return <DashboardView />;
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: string) => {
    setCurrentView(newValue);
  };

  return (
    <ThemeProvider theme={darkMode ? darkTheme : theme}>
      <CssBaseline />
      <Box sx={{ display: "flex", height: "100vh" }}>
        {/* Top AppBar */}
        <AppBar
          position="fixed"
          sx={{
            width: `calc(100% - ${SIDEBAR_WIDTH}px)`,
            ml: `${SIDEBAR_WIDTH}px`,
            zIndex: (themeZIndex) => themeZIndex.zIndex.drawer + 1,
          }}
        >
          <Toolbar>
            <CarRepair sx={{ mr: 2 }} />
            <Typography
              variant="h6"
              noWrap
              component="div"
              sx={{ flexGrow: 1 }}
            >
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

          {/* Navigation Tabs */}
          <Tabs
            value={currentView}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              borderBottom: 1,
              borderColor: "divider",
              bgcolor: "rgba(255, 255, 255, 0.1)",
              "& .MuiTab-root": {
                color: "rgba(255, 255, 255, 0.7)",
                "&.Mui-selected": {
                  color: "white",
                },
              },
              "& .MuiTabs-indicator": {
                backgroundColor: "white",
              },
            }}
          >
            {menuItems.map((item) => (
              <Tab
                key={item.id}
                value={item.id}
                label={item.label}
                icon={item.icon}
                iconPosition="start"
                sx={{ minHeight: 48 }}
              />
            ))}
          </Tabs>
        </AppBar>

        {/* Left Sidebar for CAN Status */}
        <Drawer
          sx={{
            width: SIDEBAR_WIDTH,
            flexShrink: 0,
            "& .MuiDrawer-paper": {
              width: SIDEBAR_WIDTH,
              boxSizing: "border-box",
              pt: 2,
              pb: 2,
              px: 2,
            },
          }}
          variant="permanent"
          anchor="left"
        >
          <CANStatusSidebar onConnectionChange={setCanConnected} />
        </Drawer>

        {/* Main Content Area */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            bgcolor: "background.default",
            p: 3,
            mt: "112px", // Account for AppBar + Tabs height
            overflow: "auto",
          }}
        >
          <Container maxWidth="xl">{renderCurrentComponent()}</Container>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
