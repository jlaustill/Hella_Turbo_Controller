# Repository Structure and Contribution Guide

## Overview

This repository contains tools for safely reverse engineering and programming Hella Universal Turbo Actuators. The project uses an organized structure to store memory dumps from different actuator models, enabling systematic comparison and analysis.

## Repository Structure

```
Hella_Turbo_Controller/
├── README.md                          # Main project documentation
├── CLAUDE.md                          # AI assistant guidance
├── requirements.txt                   # Python dependencies
├── run_menu.sh                        # Easy launcher script
│
├── Core Tools/
├── hella_prog.py                      # Core actuator programming library
├── hella_menu.py                      # Interactive menu system
├── actuator_config.py                 # Actuator configuration management
│
├── Analysis Tools/
├── compare_dumps.py                   # Multi-actuator comparison tool
├── analyze_can_id.py                  # CAN ID bit manipulation analysis
├── analyze_new_actuator.py            # Quick analysis for new actuators
│
├── Documentation/
├── MEMORY_ANALYSIS.md                 # Master reverse engineering analysis
├── FINDINGS_LOG.md                    # Chronological discovery log
├── ACTUATOR_TESTING_PROTOCOL.md       # Field testing procedures
├── REPOSITORY_STRUCTURE.md            # This file
│
├── Configuration/
├── actuator_configs.json              # Auto-generated actuator database
│
└── dumps/                             # Organized memory dumps
    ├── 6NW-008-412/                   # Electronic part number
    │   └── G-222/                     # Gearbox number
    │       ├── 20250124_initial_dump.bin
    │       └── 20250125_test_dump.bin
    ├── 6NW-008-413/                   # Different electronic part
    │   ├── G-350/                     # Different gearbox
    │   └── G-222/                     # Same gearbox, different electronics
    └── [other-part-numbers]/
        └── [gearbox-numbers]/
```

## How to Contribute Memory Dumps

### For New Contributors

1. **Clone the repository**:

   ```bash
   git clone https://github.com/jlaustill/Hella_Turbo_Controller.git
   cd Hella_Turbo_Controller
   ```

2. **Set up your environment**:

   ```bash
   ./run_menu.sh
   ```

   The script will automatically install dependencies if needed.

3. **Connect your actuator and run the menu**:
   - The menu will guide you through CAN interface setup
   - Configure your actuator details (part numbers)
   - Create memory dumps in organized directories

### Adding Your Actuator

When you first run the menu, you'll be prompted to configure your actuator:

- **Electronic Part Number**: Found on the actuator label (e.g., "6NW-008-412")
- **Gearbox Number**: Also on the label (e.g., "G-222")
- **Description**: Brief description (e.g., "Test actuator from VW Golf")
- **Observed CAN ID**: The CAN ID you see in candump (e.g., "0x658")

### Memory Dump Organization

The system automatically organizes dumps as:

```
dumps/[electronic_part]/[gearbox]/[timestamp]_[filename]
```

Each dump is tracked with:

- Timestamp
- Original filename
- Notes about the dump
- Actuator configuration details

## What We're Looking For

### High Priority Actuators Needed:

1. **CAN-controlled actuators** (to verify message format consistency)
2. **Different gearbox numbers** (G-350, G-400, etc.)
3. **Different electronic part numbers** (6NW-008-413, etc.)
4. **Known working vs. non-working** actuators

### Information to Document:

- **Part numbers** (both electronic and gearbox)
- **Vehicle application** (make, model, year, engine)
- **Control method** (CAN vs PWM)
- **Observed CAN ID** (from candump)
- **Working status** (functional vs. bricked)

## Safety Protocol

### ⚠️ CRITICAL: Read-Only Analysis First

1. **ALWAYS backup memory** before any modifications
2. **NEVER modify memory** without understanding bit manipulation patterns
3. **Verify CAN message format** with candump before assuming anything
4. **Compare with multiple actuators** before drawing conclusions

### Dangerous Areas (DO NOT MODIFY):

- Memory addresses 0x28-0x2F (CAN message format configuration)
- Address 0x29 (Programming CAN ID selector)
- Address 0x41 (Interface configuration)
- Addresses 0x68-0x6F (Backup configuration block)

## Analysis Workflow

### For Each New Actuator:

1. **Connect and monitor**: `candump can0` to observe CAN traffic
2. **Memory dump**: Use menu to create organized dump
3. **Quick analysis**: `python3 analyze_new_actuator.py [dump_file] [can_id]`
4. **Document findings**: Update FINDINGS_LOG.md with discoveries
5. **Commit results**: Share findings with the community

### Comparison Analysis:

```bash
# Compare multiple dumps
python3 compare_dumps.py dumps/*/*.bin

# Analyze CAN ID patterns
python3 analyze_can_id.py

# View enhanced visualization
./run_menu.sh  # Select "📊 View memory dump (visualization)"
```

## Key Discoveries So Far

### Verified G-222 Format (6NW-008-412):

- **CAN ID**: 0x658 (calculated from memory via bit manipulation)
- **Position**: bytes 2-3 (big endian), NOT bytes 5-6 as previously assumed
- **Message format**: `[status, ?, pos_h, pos_l, ?, temp, load_h, load_l]`
- **Memory config**: Block at 0x28 controls CAN message format

### Critical Safety Finding:

Previous community assumptions about byte positions were **WRONG** and led to bricked actuators. This repository uses systematic verification to prevent future failures.

## How to Submit Findings

### Quick Contribution:

1. Create memory dump through menu system
2. Run analysis scripts
3. Create pull request with dump files and findings

### Detailed Contribution:

1. Follow the testing protocol in ACTUATOR_TESTING_PROTOCOL.md
2. Update FINDINGS_LOG.md with your actuator's template
3. Include candump output and analysis results
4. Submit pull request with organized documentation

## Questions?

- **Check existing documentation** in the docs/ folder first
- **Search issues** on GitHub for similar actuators
- **Open new issue** with your actuator details if stuck

## Community Impact

Your contributions help:

- ✅ **Prevent bricked actuators** through verified analysis
- ✅ **Build safe modification procedures** based on multiple data points
- ✅ **Understand actuator variations** across different models
- ✅ **Create tools** that work reliably across the actuator family

**Together we can reverse engineer these safely and systematically!** 🚀
