# 🚀 How to Start the Hella Turbo Controller

## Quick Start

### Web Version (Recommended for now)

```bash
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

### Electron Desktop App (Coming Soon)

The desktop app is being finalized. For now, use the web version above.

## What You'll See

1. **Dashboard** - Welcome screen with overview
2. **Actuators** - CAN interface setup and actuator configuration
3. **Memory Viewer** - Hex dump analysis and visualization
4. **CAN Monitor** - Real-time CAN bus traffic monitoring
5. **Analysis** - Memory dump comparison tools

## Development Scripts

- `npm run dev` - Start development web server
- `npm run build` - Build for production
- `npm run lint` - Check code quality
- `npm run format` - Format code with Prettier

## Notes

- The TypeScript version is a modern replacement for the Python CLI tools
- All core functionality is implemented in the web interface
- CAN communication will require the socketcan npm package (Linux only for now)
- For actual hardware testing, you'll still need the Python version in `legacy-python/`

## Need the Python Version?

For actual CAN hardware communication right now, use:

```bash
cd legacy-python
./run_menu.sh
```
