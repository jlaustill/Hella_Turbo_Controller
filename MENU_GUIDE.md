# Hella Turbo Controller - Interactive Menu Guide

## Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the menu:**
   ```bash
   ./run_menu.sh
   ```

## Menu Navigation

- **Arrow keys**: Navigate menu options
- **Enter**: Select option
- **Ctrl+C**: Cancel current operation or exit
- **Tab**: Auto-complete in text inputs

## Interface Setup Guide

### SocketCAN (Linux built-in CAN)

Best for Raspberry Pi or Linux systems with built-in CAN controllers:

```bash
# Setup CAN interface (run once)
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0

# Then select "SocketCAN" in menu and choose "can0"
```

### SLCAN (USB-to-CAN Adapter)

Best for USB CAN adapters on any operating system:

1. Connect your USB-to-CAN adapter
2. Select "SLCAN" in menu
3. Choose detected device (usually `/dev/ttyUSB0` or `/dev/ttyACM0`)

### Virtual CAN (Testing)

For testing without hardware:

```bash
# Create virtual CAN interface
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Then select "Virtual CAN" and choose "vcan0"
```

## Menu Options Explained

### 📁 Read Memory Dump

- Downloads complete actuator memory (128 bytes)
- Saves to timestamped file or custom filename
- Use this to backup current settings

### 📍 Read Current Positions

- Shows min/max position settings
- Displays values in hex, decimal, and percentage
- No hardware movement involved

### ⚙️ Set Positions

- **Minimum**: Sets lowest position value
- **Maximum**: Sets highest position value
- Input validation prevents invalid values
- Confirmation required before writing

### 🎯 Auto-Calibrate End Positions

- **⚠️ WARNING**: Moves actuator to physical limits!
- Automatically finds min/max positions
- Only use when actuator is safe to move
- Results shown in detailed table

### 📊 View Memory Dump

- Visualizes previously saved memory dumps
- Shows hex dump, ASCII representation
- Data analysis and statistics
- Interprets position values

### 🔄 Read Current Position

- Shows real-time actuator position
- Displays percentage within min/max range
- Useful for monitoring movement

### 🔧 Connection Information

- Shows active interface details
- Communication test option
- Useful for troubleshooting

## Input Formats

Position values can be entered as:

- **Decimal**: `1234`
- **Hexadecimal**: `0x04D2`
- **Range**: 0 to 65535 (0x0000 to 0xFFFF)

## Safety Notes

- ⚠️ **Auto-calibration moves the actuator!** Only use when safe
- 🔒 All destructive operations require confirmation
- 💾 Always backup memory before making changes
- 🔍 Test connection before performing operations

## Troubleshooting

### "No CAN interfaces detected"

- Check if CAN hardware is connected
- Verify interface is configured (for SocketCAN)
- Try manual configuration option

### "Permission denied"

- USB devices: Check user permissions or use sudo
- SocketCAN: May need sudo for interface setup

### "Connection failed"

- Verify correct interface type selected
- Check device paths (USB devices may change)
- Ensure actuator is powered and connected

### "No acknowledgment received"

- Check CAN bus termination
- Verify bitrate (should be 500kbps)
- Ensure actuator is responsive

## Advanced Usage

### Batch Operations

For multiple operations, use the programmatic interface:

```python
from hella_prog import HellaProg

with HellaProg('can0', 'socketcan') as hp:
    # Read current settings
    min_pos = hp.readmin()
    max_pos = hp.readmax()

    # Backup memory
    hp.readmemory("backup.bin")

    # Set new positions
    hp.set_minmax(0x0100, 0x0300)
```

### Custom Configurations

The menu system can be extended by modifying `hella_menu.py`. Key areas:

- Interface detection logic
- Menu options and handlers
- Visualization features
- Error handling

## File Outputs

- **Memory dumps**: `YYYYMMDD-HHMMSS.bin` or custom names
- **Location**: Current working directory
- **Size**: 128 bytes (actuator memory size)
- **Format**: Raw binary data

Use the visualization feature to view dump contents in human-readable format.
