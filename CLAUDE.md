# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a Python application for programming the Hella Universal turbo actuator I. The actuator is used to control VTG turbos and can operate in both CAN bus and PWM modes. The main functionality allows reading memory, configuring min/max positions, and calibrating actuator endpoints.

## Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
```

- `python-can` library for CAN bus communication (version 4.0.0+)
- Requires either SLCAN interface or SOCKETCAN compatible interface (Linux)

## Core Architecture

The main class `HellaProg` in `hella_prog.py` handles all communication with the turbo actuator:

- **CAN Communication**: Uses python-can library with configurable interfaces (socketcan, slcan)
- **Memory Operations**: Read actuator memory (`readmemory()`) - outputs timestamped binary files
- **Position Management**: Read/write min/max positions (`readmin()`, `readmax()`, `set_min()`, `set_max()`)
- **Calibration**: Auto-discover end positions (`find_end_positions()`)
- **Real-time Monitoring**: Read current actuator position (`read_current_position()`)
- **Error Handling**: Comprehensive exception handling with custom `HellaProgError`
- **Context Manager**: Supports `with` statement for automatic cleanup

## Key CAN Message IDs

- 0x3F0: Request messages to actuator
- 0x3E8: Memory read responses
- 0x3EA: Position status responses  
- 0x3EB: Acknowledgment responses

## Interactive Menu System (Recommended)

The easiest way to use this tool is through the interactive menu system:

```bash
# Easy launcher with dependency checking
./run_menu.sh

# Or run directly
python3 hella_menu.py
```

### Menu Features

- **🔌 Smart Interface Detection**: Automatically detects available CAN interfaces
- **✅ Connection Validation**: Tests hardware connectivity before proceeding
- **📁 Memory Operations**: Read and visualize memory dumps with hex analysis
- **⚙️ Position Management**: Set min/max positions with input validation
- **🎯 Auto-Calibration**: Automatic end position discovery with safety warnings
- **📊 Data Visualization**: View memory dumps in hex format with data analysis
- **🔄 Real-time Monitoring**: Read current actuator position
- **🛡️ Error Handling**: Comprehensive error handling with retry options

### Interface Configuration

The menu system supports:

| Interface Type | Description | Example |
|---------------|-------------|---------|
| **SocketCAN** | Linux built-in CAN | can0, can1 |
| **SLCAN** | USB-to-CAN adapters | /dev/ttyUSB0, /dev/ttyACM0 |
| **Virtual CAN** | Testing with virtual interfaces | vcan0 |
| **Custom** | Manual configuration | Any valid channel |

## Programmatic Usage

For scripting and automation, use the library directly:

```python
from hella_prog import HellaProg

# Use context manager for automatic cleanup
with HellaProg('can0', 'socketcan') as hp:
    # Read memory dump
    filename = hp.readmemory()
    
    # Read current positions
    min_pos = hp.readmin()
    max_pos = hp.readmax()
    
    # Set new positions
    hp.set_min(0x0113)
    hp.set_max(0x0220)
    
    # Automatic calibration
    min_pos, max_pos = hp.find_end_positions()
```

## Testing

Multiple ways to test the system:

```bash
# Interactive menu (recommended for users)
./run_menu.sh

# Direct script execution (for testing/automation)
python3 hella_prog.py

# Library import test
python3 -c "from hella_prog import HellaProg; print('Import successful')"
```

## Improvements Made

### Core Library (hella_prog.py)
- Fixed critical runtime errors (typos, logic bugs)
- Added comprehensive error handling and timeouts
- Implemented proper input validation
- Added context manager support for automatic cleanup
- Extensive code documentation with docstrings
- Reduced code duplication through common message sequences
- Added type hints for better code clarity
- Implemented proper logging instead of print statements

### Interactive Menu System (hella_menu.py)
- **User-Friendly Interface**: Beautiful terminal menus with arrow key navigation
- **Smart Hardware Detection**: Automatically finds available CAN interfaces and USB devices
- **Connection Validation**: Tests hardware before proceeding with operations
- **Input Validation**: Prevents invalid position values and configuration errors
- **Memory Dump Visualization**: Hex dump viewer with data analysis and statistics
- **Safety Features**: Confirmation prompts for destructive operations
- **Progress Indicators**: Visual feedback for long-running operations
- **Error Recovery**: Retry mechanisms and helpful error messages
- **Cross-Platform**: Works on Linux with SocketCAN and Windows/Mac with USB adapters