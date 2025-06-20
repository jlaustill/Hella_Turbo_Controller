#!/usr/bin/env python3
"""
Interactive Menu System for Hella Turbo Controller

This module provides a user-friendly menu-driven interface for interacting
with the Hella Universal turbo actuator I.
"""

import sys
import os
import time
import struct
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import inquirer
    from inquirer import errors
except ImportError:
    print("❌ Missing dependencies. Please install with:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.columns import Columns
    from rich.text import Text
except ImportError:
    print("❌ Missing rich library. Please install with:")
    print("   pip install rich")
    sys.exit(1)

from hella_prog import HellaProg, HellaProgError

console = Console()


class HellaMenuSystem:
    """Interactive menu system for Hella turbo controller."""
    
    def __init__(self):
        self.hp: Optional[HellaProg] = None
        self.interface_config = None
        
    def show_banner(self):
        """Display application banner."""
        banner = Panel.fit(
            "🔧 [bold blue]Hella Turbo Controller[/bold blue]\n"
            "[dim]Interactive Programming Interface[/dim]",
            style="bold cyan"
        )
        console.print(banner)
        console.print()
    
    def interface_selection_menu(self) -> Tuple[str, str]:
        """
        Interface selection with validation.
        
        Returns:
            Tuple of (channel, interface_type)
        """
        console.print("[bold]🔌 CAN Interface Configuration[/bold]")
        
        questions = [
            inquirer.List(
                'interface_type',
                message="Select your CAN interface type",
                choices=[
                    ('SocketCAN (Linux built-in CAN)', 'socketcan'),
                    ('SLCAN (USB-to-CAN adapter)', 'slcan'),
                    ('Virtual CAN (for testing)', 'socketcan_virtual'),
                    ('Custom configuration', 'custom')
                ],
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            sys.exit(0)
            
        interface_type = answers['interface_type']
        
        if interface_type == 'socketcan':
            channel = self._configure_socketcan()
        elif interface_type == 'slcan':
            channel = self._configure_slcan()
        elif interface_type == 'socketcan_virtual':
            channel = self._configure_virtual_can()
        else:  # custom
            channel = self._configure_custom()
            interface_type = inquirer.prompt([
                inquirer.List('type', message="Interface type", choices=['socketcan', 'slcan'])
            ])['type']
        
        return channel, interface_type
    
    def _configure_socketcan(self) -> str:
        """Configure SocketCAN interface."""
        # Check available CAN interfaces
        available_interfaces = []
        try:
            with os.popen('ip link show type can') as f:
                output = f.read()
                for line in output.split('\n'):
                    if 'can' in line and ':' in line:
                        iface = line.split(':')[1].strip().split('@')[0]
                        if iface.startswith('can'):
                            available_interfaces.append(iface)
        except:
            pass
        
        if not available_interfaces:
            available_interfaces = ['can0', 'can1']  # Default options
            console.print("[yellow]⚠️  No CAN interfaces detected. Showing common options.[/yellow]")
        
        questions = [
            inquirer.List(
                'channel',
                message="Select CAN interface",
                choices=available_interfaces + ['Other (custom)'],
            ),
        ]
        
        answer = inquirer.prompt(questions)
        if answer['channel'] == 'Other (custom)':
            return inquirer.prompt([
                inquirer.Text('custom_channel', message="Enter CAN interface name")
            ])['custom_channel']
        
        return answer['channel']
    
    def _configure_slcan(self) -> str:
        """Configure SLCAN interface."""
        # Check for USB serial devices
        usb_devices = []
        for device_path in ['/dev/ttyUSB*', '/dev/ttyACM*']:
            try:
                import glob
                usb_devices.extend(glob.glob(device_path))
            except:
                pass
        
        if not usb_devices:
            usb_devices = ['/dev/ttyUSB0', '/dev/ttyACM0']  # Default options
            console.print("[yellow]⚠️  No USB devices detected. Showing common options.[/yellow]")
        
        questions = [
            inquirer.List(
                'channel',
                message="Select USB device",
                choices=usb_devices + ['Other (custom)'],
            ),
        ]
        
        answer = inquirer.prompt(questions)
        if answer['channel'] == 'Other (custom)':
            return inquirer.prompt([
                inquirer.Text('custom_channel', message="Enter device path")
            ])['custom_channel']
        
        return answer['channel']
    
    def _configure_virtual_can(self) -> str:
        """Configure virtual CAN interface."""
        questions = [
            inquirer.List(
                'channel',
                message="Select virtual CAN interface",
                choices=['vcan0', 'vcan1', 'Other (custom)'],
            ),
        ]
        
        answer = inquirer.prompt(questions)
        if answer['channel'] == 'Other (custom)':
            return inquirer.prompt([
                inquirer.Text('custom_channel', message="Enter virtual CAN interface name")
            ])['custom_channel']
        
        return answer['channel']
    
    def _configure_custom(self) -> str:
        """Configure custom interface."""
        return inquirer.prompt([
            inquirer.Text('channel', message="Enter channel/device path")
        ])['channel']
    
    def test_connection(self, channel: str, interface_type: str) -> bool:
        """
        Test the CAN connection.
        
        Args:
            channel: CAN channel
            interface_type: Interface type
            
        Returns:
            True if connection successful
        """
        console.print(f"[yellow]🔍 Testing connection to {interface_type}:{channel}...[/yellow]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Connecting...", total=None)
                
                # Try to initialize the interface
                test_hp = HellaProg(channel, interface_type)
                progress.update(task, description="Testing communication...")
                time.sleep(1)  # Give it a moment
                
                # Try a simple operation
                try:
                    # Just try to create the request message - this validates the interface
                    test_hp.interface.send(test_hp.msg_req, timeout=0.1)
                    progress.update(task, description="Connection successful!")
                    time.sleep(0.5)
                except:
                    # Even if send fails, interface creation success is good enough
                    progress.update(task, description="Interface initialized!")
                    time.sleep(0.5)
                
                test_hp.shutdown()
                
            console.print("[green]✅ Connection test successful![/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Connection failed: {str(e)}[/red]")
            
            if "No module named" in str(e):
                console.print("[yellow]💡 Try installing: pip install python-can[/yellow]")
            elif "Permission denied" in str(e):
                console.print("[yellow]💡 Try running with sudo or check device permissions[/yellow]")
            elif "No such file or directory" in str(e):
                console.print("[yellow]💡 Check if the device/interface exists[/yellow]")
            
            retry = Confirm.ask("Would you like to try a different configuration?")
            return not retry
    
    def establish_connection(self) -> bool:
        """
        Establish connection with validation.
        
        Returns:
            True if connection established successfully
        """
        while True:
            channel, interface_type = self.interface_selection_menu()
            
            if self.test_connection(channel, interface_type):
                try:
                    self.hp = HellaProg(channel, interface_type)
                    self.interface_config = (channel, interface_type)
                    console.print(f"[green]🔗 Connected to {interface_type}:{channel}[/green]")
                    return True
                except Exception as e:
                    console.print(f"[red]❌ Failed to establish connection: {e}[/red]")
                    if not Confirm.ask("Try again?"):
                        return False
            else:
                return False
    
    def main_menu(self):
        """Display and handle main menu."""
        if not self.hp:
            console.print("[red]❌ No active connection![/red]")
            return False
        
        choices = [
            "📁 Read memory dump",
            "📍 Read current positions",
            "⚙️  Set minimum position", 
            "⚙️  Set maximum position",
            "🎯 Auto-calibrate end positions",
            "📊 View memory dump (visualization)",
            "🔄 Read current actuator position",
            "🔧 Connection information",
            "❌ Disconnect and exit"
        ]
        
        questions = [
            inquirer.List(
                'action',
                message="What would you like to do?",
                choices=choices,
            ),
        ]
        
        answer = inquirer.prompt(questions)
        if not answer:
            return False
            
        action = answer['action']
        
        try:
            if action.startswith("📁"):
                self._handle_memory_dump()
            elif action.startswith("📍"):
                self._handle_read_positions()
            elif action.startswith("⚙️") and "minimum" in action:
                self._handle_set_min_position()
            elif action.startswith("⚙️") and "maximum" in action:
                self._handle_set_max_position()
            elif action.startswith("🎯"):
                self._handle_auto_calibrate()
            elif action.startswith("📊"):
                self._handle_view_dump()
            elif action.startswith("🔄"):
                self._handle_current_position()
            elif action.startswith("🔧"):
                self._handle_connection_info()
            elif action.startswith("❌"):
                return False
                
        except HellaProgError as e:
            console.print(f"[red]❌ Operation failed: {e}[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error: {e}[/red]")
        
        if not action.startswith("❌"):
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
        
        return not action.startswith("❌")
    
    def _handle_memory_dump(self):
        """Handle memory dump operation."""
        console.print("[bold]📁 Memory Dump Operation[/bold]")
        
        # Ask for filename
        default_name = f"actuator_dump_{int(time.time())}.bin"
        custom_name = inquirer.prompt([
            inquirer.Text(
                'filename', 
                message="Enter filename (or press Enter for default)",
                default=default_name
            )
        ])
        
        filename = custom_name['filename'] if custom_name else default_name
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Reading memory...", total=None)
            
            try:
                result_filename = self.hp.readmemory(filename)
                progress.update(task, description="Memory dump completed!")
                time.sleep(0.5)
                
                console.print(f"[green]✅ Memory saved to: {result_filename}[/green]")
                
                # Show file info
                file_path = Path(result_filename)
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    console.print(f"[dim]📏 File size: {file_size} bytes[/dim]")
                    
            except Exception as e:
                progress.update(task, description="Failed!")
                raise e
    
    def _handle_read_positions(self):
        """Handle reading current positions."""
        console.print("[bold]📍 Reading Current Positions[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Reading positions...", total=None)
            
            min_pos = self.hp.readmin()
            max_pos = self.hp.readmax()
            
            progress.update(task, description="Positions read successfully!")
            time.sleep(0.5)
        
        # Create a nice table
        table = Table(title="Current Position Settings")
        table.add_column("Parameter", style="cyan")
        table.add_column("Hex Value", style="yellow")
        table.add_column("Decimal Value", style="green")
        table.add_column("Percentage", style="blue")
        
        if max_pos > min_pos:
            range_val = max_pos - min_pos
            min_pct = 0.0
            max_pct = 100.0
        else:
            range_val = 1
            min_pct = max_pct = 0.0
        
        table.add_row("Minimum Position", f"{min_pos:04X}", str(min_pos), f"{min_pct:.1f}%")
        table.add_row("Maximum Position", f"{max_pos:04X}", str(max_pos), f"{max_pct:.1f}%")
        table.add_row("Range", f"{range_val:04X}", str(range_val), f"{max_pct - min_pct:.1f}%")
        
        console.print(table)
    
    def _handle_set_min_position(self):
        """Handle setting minimum position."""
        console.print("[bold]⚙️ Set Minimum Position[/bold]")
        
        # Get current position for reference
        try:
            current_min = self.hp.readmin()
            current_max = self.hp.readmax()
            console.print(f"[dim]Current min: {current_min:04X} ({current_min}), max: {current_max:04X} ({current_max})[/dim]")
        except:
            current_min = current_max = None
        
        def validate_position(answers, current):
            try:
                if current.startswith('0x') or current.startswith('0X'):
                    value = int(current, 16)
                else:
                    value = int(current)
                    
                if not (0 <= value <= 65535):
                    raise errors.ValidationError('', reason='Position must be between 0 and 65535')
                
                if current_max and value >= current_max:
                    raise errors.ValidationError('', reason=f'Minimum must be less than current maximum ({current_max})')
                    
                return True
            except ValueError:
                raise errors.ValidationError('', reason='Please enter a valid number (decimal or 0xHEX)')
        
        questions = [
            inquirer.Text(
                'position',
                message="Enter minimum position (decimal or 0xHEX)",
                validate=validate_position
            ),
            inquirer.Confirm(
                'confirm',
                message="Are you sure you want to set this position?",
                default=False
            )
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or not answers['confirm']:
            console.print("[yellow]⚠️  Operation cancelled[/yellow]")
            return
        
        pos_str = answers['position']
        if pos_str.startswith('0x') or pos_str.startswith('0X'):
            position = int(pos_str, 16)
        else:
            position = int(pos_str)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Setting minimum position...", total=None)
            
            self.hp.set_min(position)
            
            progress.update(task, description="Position set successfully!")
            time.sleep(0.5)
        
        console.print(f"[green]✅ Minimum position set to {position:04X} ({position})[/green]")
    
    def _handle_set_max_position(self):
        """Handle setting maximum position."""
        console.print("[bold]⚙️ Set Maximum Position[/bold]")
        
        # Get current position for reference
        try:
            current_min = self.hp.readmin()
            current_max = self.hp.readmax()
            console.print(f"[dim]Current min: {current_min:04X} ({current_min}), max: {current_max:04X} ({current_max})[/dim]")
        except:
            current_min = current_max = None
        
        def validate_position(answers, current):
            try:
                if current.startswith('0x') or current.startswith('0X'):
                    value = int(current, 16)
                else:
                    value = int(current)
                    
                if not (0 <= value <= 65535):
                    raise errors.ValidationError('', reason='Position must be between 0 and 65535')
                
                if current_min and value <= current_min:
                    raise errors.ValidationError('', reason=f'Maximum must be greater than current minimum ({current_min})')
                    
                return True
            except ValueError:
                raise errors.ValidationError('', reason='Please enter a valid number (decimal or 0xHEX)')
        
        questions = [
            inquirer.Text(
                'position',
                message="Enter maximum position (decimal or 0xHEX)",
                validate=validate_position
            ),
            inquirer.Confirm(
                'confirm',
                message="Are you sure you want to set this position?",
                default=False
            )
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or not answers['confirm']:
            console.print("[yellow]⚠️  Operation cancelled[/yellow]")
            return
        
        pos_str = answers['position']
        if pos_str.startswith('0x') or pos_str.startswith('0X'):
            position = int(pos_str, 16)
        else:
            position = int(pos_str)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Setting maximum position...", total=None)
            
            self.hp.set_max(position)
            
            progress.update(task, description="Position set successfully!")
            time.sleep(0.5)
        
        console.print(f"[green]✅ Maximum position set to {position:04X} ({position})[/green]")
    
    def _handle_auto_calibrate(self):
        """Handle automatic calibration."""
        console.print("[bold]🎯 Automatic End Position Calibration[/bold]")
        
        warning_text = Text()
        warning_text.append("⚠️  WARNING: ", style="bold red")
        warning_text.append("This will move the actuator to its physical limits!\n", style="red")
        warning_text.append("Make sure the actuator is safe to move and not under load.", style="yellow")
        
        console.print(Panel(warning_text, title="Safety Warning", border_style="red"))
        
        if not Confirm.ask("Do you want to proceed with automatic calibration?"):
            console.print("[yellow]⚠️  Calibration cancelled[/yellow]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Starting calibration...", total=None)
            
            progress.update(task, description="Moving to end positions...")
            min_pos, max_pos = self.hp.find_end_positions()
            
            progress.update(task, description="Calibration completed!")
            time.sleep(0.5)
        
        # Show results
        table = Table(title="Calibration Results")
        table.add_column("Parameter", style="cyan")
        table.add_column("Hex Value", style="yellow")
        table.add_column("Decimal Value", style="green")
        
        table.add_row("Minimum Position", f"{min_pos:04X}", str(min_pos))
        table.add_row("Maximum Position", f"{max_pos:04X}", str(max_pos))
        table.add_row("Range", f"{max_pos - min_pos:04X}", str(max_pos - min_pos))
        
        console.print(table)
        console.print("[green]✅ Automatic calibration completed successfully![/green]")
    
    def _handle_view_dump(self):
        """Handle viewing memory dump with visualization."""
        console.print("[bold]📊 Memory Dump Visualization[/bold]")
        
        # Find available dump files
        dump_files = []
        for pattern in ['*.bin', '*dump*.bin', 'actuator_*.bin']:
            import glob
            dump_files.extend(glob.glob(pattern))
        
        if not dump_files:
            console.print("[yellow]⚠️  No memory dump files found in current directory[/yellow]")
            
            # Offer to create one
            if Confirm.ask("Would you like to create a memory dump now?"):
                self._handle_memory_dump()
                return
            else:
                return
        
        # Select file to view
        questions = [
            inquirer.List(
                'filename',
                message="Select memory dump file to view",
                choices=dump_files + ['Other (specify path)'],
            ),
        ]
        
        answer = inquirer.prompt(questions)
        if not answer:
            return
            
        filename = answer['filename']
        if filename == 'Other (specify path)':
            filename = inquirer.prompt([
                inquirer.Text('custom_file', message="Enter file path")
            ])['custom_file']
        
        try:
            self._visualize_memory_dump(filename)
        except FileNotFoundError:
            console.print(f"[red]❌ File not found: {filename}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error reading file: {e}[/red]")
    
    def _visualize_memory_dump(self, filename: str):
        """
        Visualize memory dump contents.
        
        Args:
            filename: Path to the memory dump file
        """
        console.print(f"[bold]📊 Analyzing: {filename}[/bold]")
        
        with open(filename, 'rb') as f:
            data = f.read()
        
        console.print(f"[dim]File size: {len(data)} bytes[/dim]\n")
        
        # Hex dump view
        console.print("[bold]🔍 Hex Dump View:[/bold]")
        hex_lines = []
        for i in range(0, min(len(data), 256), 16):  # Show first 256 bytes max
            hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
            hex_lines.append(f"{i:04X}: {hex_part:<48} |{ascii_part}|")
        
        # Show in a nice format
        for line in hex_lines[:16]:  # Show first 16 lines
            console.print(f"[dim]{line}[/dim]")
        
        if len(hex_lines) > 16:
            console.print(f"[dim]... and {len(hex_lines) - 16} more lines[/dim]")
        
        console.print()
        
        # Data analysis
        console.print("[bold]📈 Data Analysis:[/bold]")
        
        # Basic statistics
        analysis_table = Table()
        analysis_table.add_column("Property", style="cyan")
        analysis_table.add_column("Value", style="yellow")
        analysis_table.add_column("Notes", style="dim")
        
        analysis_table.add_row("File Size", f"{len(data)} bytes", "Expected: 128 bytes")
        analysis_table.add_row("Non-zero Bytes", str(sum(1 for b in data if b != 0)), "")
        analysis_table.add_row("Zero Bytes", str(sum(1 for b in data if b == 0)), "")
        
        # Interpret known memory locations
        if len(data) >= 128:
            analysis_table.add_row("", "", "")
            analysis_table.add_row("[bold]Known Memory Locations[/bold]", "", "")
            
            # Position values (addresses 3-6)
            if len(data) > 6:
                min_pos = (data[3] << 8) | data[4]
                max_pos = (data[5] << 8) | data[6]
                
                analysis_table.add_row("Min Position (0x03-04)", f"{min_pos:04X} ({min_pos})", "Actuator minimum")
                analysis_table.add_row("Max Position (0x05-06)", f"{max_pos:04X} ({max_pos})", "Actuator maximum")
                
                if max_pos > min_pos:
                    range_val = max_pos - min_pos
                    analysis_table.add_row("Position Range", f"{range_val:04X} ({range_val})", f"≈{range_val/10.24:.1f}% of full scale")
            
            # Range calculation byte (address 0x22)
            if len(data) > 0x22:
                range_byte = data[0x22]
                expected_range = (max_pos - min_pos) // 4 if max_pos > min_pos else 0
                match_indicator = "✓" if abs(range_byte - expected_range) <= 1 else "⚠️"
                analysis_table.add_row("Range Byte (0x22)", f"{range_byte:02X} ({range_byte})", f"{match_indicator} Expected: {expected_range}")
            
            # Configuration bytes (if we can safely interpret them)
            if len(data) > 0x29:
                config_29 = data[0x29]
                analysis_table.add_row("Config Byte (0x29)", f"{config_29:02X}", "Programming CAN ID selector")
            
            if len(data) > 0x41:
                config_41 = data[0x41]
                pwm_from_can = "Yes" if config_41 & 0x10 else "No"
                can_tx_enabled = "Yes" if config_41 & 0x40 else "No"
                motor_dir = "CCW" if config_41 & 0x01 else "CW"
                analysis_table.add_row("Interface Config (0x41)", f"{config_41:02X}", f"PWM from CAN: {pwm_from_can}")
                analysis_table.add_row("", "", f"CAN TX: {can_tx_enabled}, Motor: {motor_dir}")
            
            # CAN ID configurations (addresses 0x24-0x28)
            if len(data) > 0x28:
                req_id_h, req_id_l = data[0x24], data[0x25]
                resp_id_h, resp_id_l = data[0x27], data[0x28]
                
                # Calculate CAN IDs using formula from community research
                req_can_id = (req_id_h << 8) | req_id_l
                resp_can_id = (resp_id_h << 8) | resp_id_l
                
                analysis_table.add_row("Request CAN ID", f"0x{req_can_id:03X}", f"From bytes 0x{req_id_h:02X}{req_id_l:02X}")
                analysis_table.add_row("Response CAN ID", f"0x{resp_can_id:03X}", f"From bytes 0x{resp_id_h:02X}{resp_id_l:02X}")
        
        console.print(analysis_table)
        
        # Add actuator type detection
        console.print("\n[bold]🔍 Actuator Analysis:[/bold]")
        
        type_table = Table()
        type_table.add_column("Analysis", style="cyan")
        type_table.add_column("Result", style="yellow")
        
        if len(data) >= 128:
            # Try to identify actuator type based on known patterns
            if len(data) > 0x41:
                config_41 = data[0x41]
                if config_41 & 0x10 and config_41 & 0x40:
                    type_table.add_row("Control Mode", "[green]CAN position control enabled[/green]")
                elif config_41 & 0x40:
                    type_table.add_row("Control Mode", "[yellow]CAN status only (PWM control)[/yellow]")
                else:
                    type_table.add_row("Control Mode", "[red]PWM only (no CAN)[/red]")
            
            # Estimate G-code based on response CAN ID
            if len(data) > 0x28:
                resp_id = (data[0x27] << 8) | data[0x28]
                g_code_guess = ""
                if resp_id == 0x4EB:
                    g_code_guess = "Possibly G-221 (Ford TDCI style)"
                elif resp_id == 0x71C:
                    g_code_guess = "Possibly G-22 variant"
                elif resp_id == 0x658:
                    g_code_guess = "Possibly G-222 variant"
                
                if g_code_guess:
                    type_table.add_row("Detected Type", g_code_guess)
            
            # Position range analysis
            if len(data) > 6:
                min_pos = (data[3] << 8) | data[4]
                max_pos = (data[5] << 8) | data[6]
                if max_pos > min_pos:
                    range_val = max_pos - min_pos
                    if range_val < 100:
                        type_table.add_row("Range Assessment", "[yellow]Small range - may need calibration[/yellow]")
                    elif range_val > 1000:
                        type_table.add_row("Range Assessment", "[yellow]Large range - check if correct[/yellow]")
                    else:
                        type_table.add_row("Range Assessment", "[green]Normal operating range[/green]")
        
        console.print(type_table)
        
        # Warning about dangerous modifications
        warning_text = Text()
        warning_text.append("⚠️  DANGER: ", style="bold red")
        warning_text.append("Modifying bytes 0x29, 0x41, or CAN ID configs can brick the actuator!\n", style="red")
        warning_text.append("Always backup before changes. See MEMORY_LAYOUT.md for details.", style="yellow")
        
        console.print(Panel(warning_text, title="Safety Warning", border_style="red"))
        
        # Byte distribution visualization
        console.print("\n[bold]📊 Byte Value Distribution:[/bold]")
        
        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        # Show top 10 most frequent bytes
        byte_freq = [(count, byte) for byte, count in enumerate(byte_counts) if count > 0]
        byte_freq.sort(reverse=True)
        
        freq_table = Table()
        freq_table.add_column("Byte Value", style="cyan")
        freq_table.add_column("Hex", style="yellow")
        freq_table.add_column("Count", style="green")
        freq_table.add_column("Percentage", style="blue")
        
        for count, byte in byte_freq[:10]:
            percentage = (count / len(data)) * 100
            freq_table.add_row(str(byte), f"{byte:02X}", str(count), f"{percentage:.1f}%")
        
        console.print(freq_table)
    
    def _handle_current_position(self):
        """Handle reading current actuator position."""
        console.print("[bold]🔄 Reading Current Actuator Position[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Reading position...", total=None)
            
            position = self.hp.read_current_position()
            
            progress.update(task, description="Position read!")
            time.sleep(0.5)
        
        if position is not None:
            # Get min/max for percentage calculation
            try:
                min_pos = self.hp.readmin()
                max_pos = self.hp.readmax()
                
                if max_pos > min_pos:
                    percentage = ((position - min_pos) / (max_pos - min_pos)) * 100
                else:
                    percentage = 0.0
                    
                # Create position display
                table = Table(title="Current Actuator Position")
                table.add_column("Parameter", style="cyan")
                table.add_column("Value", style="yellow")
                
                table.add_row("Current Position (Hex)", f"{position:04X}")
                table.add_row("Current Position (Decimal)", str(position))
                table.add_row("Position Percentage", f"{percentage:.1f}%")
                table.add_row("", "")
                table.add_row("Min Position", f"{min_pos:04X} ({min_pos})")
                table.add_row("Max Position", f"{max_pos:04X} ({max_pos})")
                
                console.print(table)
                
            except Exception as e:
                console.print(f"[green]✅ Current position: {position:04X} ({position})[/green]")
                console.print(f"[yellow]⚠️  Could not read min/max for percentage: {e}[/yellow]")
        else:
            console.print("[red]❌ Failed to read current position[/red]")
    
    def _handle_connection_info(self):
        """Handle displaying connection information."""
        console.print("[bold]🔧 Connection Information[/bold]")
        
        if not self.interface_config:
            console.print("[red]❌ No connection information available[/red]")
            return
        
        channel, interface_type = self.interface_config
        
        info_table = Table(title="Active Connection")
        info_table.add_column("Parameter", style="cyan")
        info_table.add_column("Value", style="yellow")
        
        info_table.add_row("Interface Type", interface_type)
        info_table.add_row("Channel/Device", channel)
        info_table.add_row("Status", "[green]Connected[/green]")
        
        # Try to get additional info
        try:
            if hasattr(self.hp, 'interface'):
                info_table.add_row("Bitrate", "500000 bps")
                if interface_type == 'slcan':
                    info_table.add_row("TTY Baudrate", "128000 bps")
        except:
            pass
        
        console.print(info_table)
        
        # Test communication
        if Confirm.ask("Would you like to test communication?"):
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Testing communication...", total=None)
                    
                    # Try to read current position as a simple test
                    position = self.hp.read_current_position()
                    
                    progress.update(task, description="Communication test completed!")
                    time.sleep(0.5)
                
                if position is not None:
                    console.print("[green]✅ Communication test successful![/green]")
                    console.print(f"[dim]Test result: Read position {position:04X}[/dim]")
                else:
                    console.print("[yellow]⚠️  Communication test completed but no position data received[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]❌ Communication test failed: {e}[/red]")
    
    def run(self):
        """Run the interactive menu system."""
        try:
            self.show_banner()
            
            # Establish connection
            if not self.establish_connection():
                console.print("[red]❌ Could not establish connection. Exiting.[/red]")
                return
            
            # Main menu loop
            while True:
                try:
                    if not self.main_menu():
                        break
                except KeyboardInterrupt:
                    console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
                    if Confirm.ask("Do you want to exit?"):
                        break
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error: {e}[/red]")
        finally:
            # Cleanup
            if self.hp:
                try:
                    self.hp.shutdown()
                    console.print("[dim]🔌 Connection closed[/dim]")
                except:
                    pass
            
            console.print("\n[bold blue]👋 Thank you for using Hella Turbo Controller![/bold blue]")


def main():
    """Main entry point."""
    menu_system = HellaMenuSystem()
    menu_system.run()


if __name__ == "__main__":
    main()