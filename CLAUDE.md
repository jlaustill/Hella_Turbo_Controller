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
- **Real-time Monitoring**: Read current actuator position (`readCurrentPosition()`)
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

The menu system supports automatic CAN interface management:

| Interface Type  | Description                     | Auto-Setup         | Example                    |
| --------------- | ------------------------------- | ------------------ | -------------------------- |
| **SocketCAN**   | Linux built-in CAN              | ✅ Yes (with sudo) | can0, can1                 |
| **SLCAN**       | USB-to-CAN adapters             | ⚠️ Manual          | /dev/ttyUSB0, /dev/ttyACM0 |
| **Virtual CAN** | Testing with virtual interfaces | ✅ Yes (with sudo) | vcan0                      |
| **Custom**      | Manual configuration            | ❌ No              | Any valid channel          |

**Automatic Setup Features:**

- 🔍 **Auto-detection** of available CAN interfaces
- 📊 **Status checking** (UP/DOWN, bitrate verification)
- 🔧 **Automatic configuration** with sudo password prompt
- ✅ **Smart reconfiguration** if bitrate needs to change

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

## Development Guidelines

### Code Modification Best Practices

**ALWAYS check for existing methods before creating new ones:**

- Use `grep` or code search to find existing functionality
- Check method names with similar patterns (e.g., `readCurrentPosition` vs `read_current_position`)
- Prefer modifying existing methods to return appropriate values rather than duplicating functionality
- When a method exists but doesn't return the expected value, modify it instead of creating a wrapper

**Example:** If you need a method that returns a position value but find an existing method that only prints it, modify the existing method to both print AND return the value rather than creating a duplicate method.

### ⚠️ CRITICAL SAFETY WARNING - Data Format Corrections

**DANGER: Previous assumptions about CAN data format were WRONG and could brick actuators!**

**Original (INCORRECT) assumptions:**

- Position data in bytes 5-6 of CAN messages
- Various hardcoded CAN IDs that may not match actual hardware

**Verified G-222 format (from reverse engineering):**

- **Position**: bytes 2-3 (big endian) - range 688 (0% open) to 212 (100% open)
- **Status**: byte 0
- **Temperature**: byte 5
- **Motor Load**: bytes 6-7 (big endian)
- **CAN ID**: 0x658 (for this specific actuator - varies by model)

**Before making ANY memory modifications:**

1. Verify the exact data format for YOUR specific actuator model
2. Use candump to observe actual CAN traffic patterns
3. Cross-reference memory contents with observed behavior
4. NEVER assume byte positions without verification

### ✍️ CRITICAL: Git Commit Signing Policy

**ALL commits to this repository MUST be GPG signed with ZERO exceptions.**

This is a security-critical project dealing with hardware that can be permanently damaged. Commit signing ensures:

- **Authenticity**: Verify commits come from trusted contributors
- **Integrity**: Detect any tampering with commit history
- **Accountability**: Clear trail of who made what changes
- **Safety**: Critical for projects that can brick expensive hardware

**Setup GPG signing:**

```bash
# Generate GPG key if you don't have one
gpg --full-generate-key

# Configure Git to use your key
git config --global user.signingkey YOUR_KEY_ID
git config --global commit.gpgsign true

# Verify signing works
git commit -S -m "Test signed commit"
```

**If commits fail with signing errors:**

- ❌ **NEVER use `--no-gpg-sign`**
- ✅ **Fix the GPG setup instead**
- ✅ **Ask for help if needed**

This policy protects the community from potentially dangerous unsigned commits.

## 🚫 CRITICAL: NO MOCK/SIMULATION DATA POLICY

**NEVER implement mock, simulated, or fake CAN traffic under ANY circumstances.**

This is a hardware reverse engineering project working with real actuators. Mock data:

- ❌ **Misleads developers** about actual hardware behavior
- ❌ **Masks real connectivity issues** that need to be fixed
- ❌ **Creates false confidence** in non-working systems
- ❌ **Wastes time** debugging fake problems
- ❌ **Dangerous for hardware** - real actuators behave differently than simulations

**When CAN traffic isn't working:**

- ✅ **Show clear error messages** explaining the hardware requirement
- ✅ **Provide troubleshooting steps** for real hardware setup
- ✅ **Display connection status** (connected/disconnected/error)
- ✅ **Guide users to fix the real problem** (hardware, drivers, permissions)

**If you need to test without hardware:**

- ✅ **Use real CAN hardware** with actual actuators
- ✅ **Set up proper CAN interfaces** (can0, can1, etc.)
- ✅ **Test with real vcan interfaces** if absolutely necessary for development

**Remember:** This tool controls expensive automotive hardware that can be permanently damaged. Only real data should ever be displayed to users.

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
