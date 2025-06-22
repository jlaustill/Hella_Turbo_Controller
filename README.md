# Hella Turbo Controller

Programming tool for the [Hella Universal turbo actuator I](https://www.hella.com/microsite-electronics/en/Universal-turbo-actuator-I-133.html) with an easy-to-use interactive menu system.

## Overview

This turbo actuator is used on many vehicles, especially to control VTG turbos. Two main interfaces to the ECU are used: the CAN bus or the PWM interface. The actuators are actually all the same and can be configured to work in either mode. Especially in PWM mode, the range and sensitivity can be configured.

This repository provides both:

- **🎯 Interactive Menu System**: User-friendly interface for easy operation
- **🔧 Python Library**: Programmatic access for automation and scripting

## ⚡ Quick Start

### Option 1: Automatic Setup (Recommended)

```bash
# The launcher handles dependencies automatically
./run_menu.sh
```

### Option 2: Manual Setup

**For newer Ubuntu/Debian systems (recommended):**

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the menu
python3 hella_menu.py
```

**For older systems or if you prefer system-wide install:**

```bash
# Install dependencies system-wide
pip install -r requirements.txt

# Run the menu
./run_menu.sh
```

That's it! The menu will guide you through interface selection, connection testing, and all operations.

## 🎮 Using the Interactive Menu

### Interface Selection

The menu automatically detects available interfaces:

| Interface Type  | Best For                 | Example                              |
| --------------- | ------------------------ | ------------------------------------ |
| **SocketCAN**   | Linux with built-in CAN  | Raspberry Pi, embedded systems       |
| **SLCAN**       | USB-to-CAN adapters      | Windows, Mac, Linux with USB adapter |
| **Virtual CAN** | Testing without hardware | Development and testing              |

### Main Operations

#### 📁 Read Memory Dump

- Downloads complete actuator memory (128 bytes)
- Saves to timestamped or custom filename
- Use this to backup current settings before changes

#### 📍 Read Current Positions

- Shows min/max position settings
- Displays values in hex, decimal, and percentage
- Safe operation - no hardware movement

#### ⚙️ Set Positions

- **Input formats**: Decimal (`1234`) or hex (`0x04D2`)
- **Range**: 0 to 65535 (0x0000 to 0xFFFF)
- **Validation**: Prevents invalid values
- **Safety**: Confirmation required before writing

#### 🎯 Auto-Calibrate End Positions

- ⚠️ **WARNING**: Moves actuator to physical limits!
- Automatically finds min/max positions
- Only use when actuator is safe to move
- Results displayed in detailed table

#### 📊 View Memory Dump

- **Intelligent analysis** of all 128 memory bytes
- **Position extraction** from addresses 0x03-0x06
- **CAN ID detection** and configuration analysis
- **Actuator type identification** (G-221, G-22, G-222 variants)
- **Control mode detection** (CAN vs PWM)
- **Safety warnings** for dangerous memory locations
- **Hex dump viewer** with ASCII representation
- **Complete documentation** in [MEMORY_LAYOUT.md](MEMORY_LAYOUT.md)

#### ✏️ Write Memory Byte

- ⚠️ **ADVANCED USERS ONLY**: Modify individual memory bytes
- **Safety validation**: Automatic backup requirement
- **Dangerous address warnings** for critical configuration bytes
- **Input validation**: Supports both hex (`0x41`) and decimal (`65`) formats
- **Multiple confirmations** to prevent accidental changes
- **Protocol compliance**: Uses proper actuator write sequence

### Navigation

- **Arrow keys**: Navigate menu options
- **Enter**: Select option
- **Ctrl+C**: Cancel current operation or exit
- **Tab**: Auto-complete in text inputs

## 🔧 Hardware Setup

### SocketCAN (Linux)

```bash
# Setup CAN interface
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0

# Then select "SocketCAN" in menu and choose "can0"
```

### SLCAN (USB-to-CAN Adapter)

1. Connect your USB-to-CAN adapter
2. Select "SLCAN" in menu
3. Choose detected device (usually `/dev/ttyUSB0` or `/dev/ttyACM0`)

### Virtual CAN (Testing)

```bash
# Create virtual CAN interface for testing
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Then select "Virtual CAN" and choose "vcan0"
```

## 🐍 Programmatic Usage

For automation and scripting, use the Python library directly:

```python
from hella_prog import HellaProg

# Use context manager for automatic cleanup
with HellaProg('can0', 'socketcan') as hp:
    # Read memory dump
    filename = hp.readmemory("backup.bin")
    print(f"Memory saved to: {filename}")

    # Read current positions
    min_pos = hp.readmin()
    max_pos = hp.readmax()
    print(f"Current range: {min_pos:04X} - {max_pos:04X}")

    # Set new positions (with validation)
    hp.set_min(0x0113)
    hp.set_max(0x0220)

    # Write single memory byte (ADVANCED - be very careful!)
    # hp.write_memory_byte(0x41, 0x50)  # Enable CAN control

    # Auto-calibrate (be careful!)
    # min_pos, max_pos = hp.find_end_positions()
```

## 📖 Documentation

- **[ROADMAP.md](ROADMAP.md)**: Project roadmap and development phases
- **[MEMORY_LAYOUT.md](MEMORY_LAYOUT.md)**: Complete memory dump analysis and configuration guide
- **[CLAUDE.md](CLAUDE.md)**: Technical documentation and API reference

## 🛠️ Troubleshooting

### Common Issues

**"externally-managed-environment" error**

```bash
# Modern Ubuntu/Debian systems protect the system Python
# Solution 1: Use virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Solution 2: Use the automatic launcher
./run_menu.sh  # Handles this automatically

# Solution 3: Install missing system packages
sudo apt install python3-venv python3-pip
```

**"No CAN interfaces detected"**

- Check if CAN hardware is connected
- Verify interface is configured (for SocketCAN)
- Try manual configuration option

**"Permission denied"**

- USB devices: Check user permissions or use sudo
- SocketCAN: May need sudo for interface setup

**"Connection failed"**

- Verify correct interface type selected
- Check device paths (USB devices may change)
- Ensure actuator is powered and connected

**"No acknowledgment received"**

- Check CAN bus termination
- Verify bitrate (should be 500kbps)
- Ensure actuator is responsive

### Getting Help

- Run `./run_menu.sh` for automatic dependency checking
- Check connection with the built-in test feature
- Use Virtual CAN mode for testing without hardware

## ⚠️ Safety Warning

**IMPORTANT**: Applying this information and/or software may break your actuator, computer, turbo, engine or car. If you do not know what you are doing, do not use this. Use this information and software at your own risk. I will not take any responsibility.

**Auto-calibration specifically**: Only use the auto-calibration feature when the actuator is safe to move and not under load. This feature will move the actuator to its physical limits.

## 📄 License & Disclaimer

This repository and/or the information relayed here is in no way provided or affiliated with Hella company and is the result of private reverse engineering work.

## 🤖 Development

This project includes significant improvements and a user-friendly interface created with assistance from [Claude Code](https://claude.ai/code).
