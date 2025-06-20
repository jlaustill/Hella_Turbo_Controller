#!/usr/bin/env python3
"""
CAN Interface Management

Handles automatic CAN interface setup, including checking status and 
bringing interfaces up with proper sudo handling.
"""

import subprocess
import os
import re
from typing import Optional, Tuple, List
import getpass

class CANInterfaceManager:
    """Manages CAN interface setup and status checking."""
    
    @staticmethod
    def get_can_interfaces() -> List[str]:
        """Get list of available CAN interfaces."""
        try:
            result = subprocess.run(['ip', 'link', 'show'], 
                                  capture_output=True, text=True, check=True)
            
            # Find CAN interfaces (look for "can" in the output)
            interfaces = []
            for line in result.stdout.split('\n'):
                # Look for lines like: "11: can0: <NOARP,ECHO> mtu 16"
                match = re.search(r'\d+:\s+(can\d+):', line)
                if match:
                    interfaces.append(match.group(1))
                    
            return interfaces
        except subprocess.CalledProcessError:
            return []
    
    @staticmethod
    def get_interface_status(interface: str) -> Tuple[bool, str, Optional[int]]:
        """
        Get CAN interface status.
        
        Returns:
            (is_up, state_description, bitrate)
        """
        try:
            result = subprocess.run(['ip', 'link', 'show', interface], 
                                  capture_output=True, text=True, check=True)
            
            output = result.stdout.lower()
            
            # Check if interface is UP
            is_up = 'state up' in output
            
            # Extract state
            if 'state up' in output:
                state = "UP"
            elif 'state down' in output:
                state = "DOWN"
            else:
                state = "UNKNOWN"
            
            # Try to get bitrate if interface is up
            bitrate = None
            if is_up:
                try:
                    can_result = subprocess.run(['ip', '-details', 'link', 'show', interface],
                                              capture_output=True, text=True, check=True)
                    # Look for bitrate in output
                    bitrate_match = re.search(r'bitrate\s+(\d+)', can_result.stdout)
                    if bitrate_match:
                        bitrate = int(bitrate_match.group(1))
                except:
                    pass
            
            return is_up, state, bitrate
            
        except subprocess.CalledProcessError:
            return False, "NOT_FOUND", None
    
    @staticmethod
    def bring_interface_up(interface: str, bitrate: int = 500000) -> Tuple[bool, str]:
        """
        Bring CAN interface up with specified bitrate.
        
        Args:
            interface: CAN interface name (e.g., 'can0')
            bitrate: CAN bitrate (default: 500000)
            
        Returns:
            (success, message)
        """
        try:
            # First, try without sudo (in case user has permissions)
            cmd = ['ip', 'link', 'set', interface, 'up', 'type', 'can', 'bitrate', str(bitrate)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, f"Interface {interface} brought up successfully"
            
            # If that failed, we need sudo
            if 'operation not permitted' in result.stderr.lower() or result.returncode != 0:
                return CANInterfaceManager._bring_interface_up_with_sudo(interface, bitrate)
            
            return False, f"Failed to bring up {interface}: {result.stderr}"
            
        except Exception as e:
            return False, f"Error bringing up interface: {e}"
    
    @staticmethod
    def _bring_interface_up_with_sudo(interface: str, bitrate: int) -> Tuple[bool, str]:
        """Bring interface up using sudo with password prompt."""
        try:
            print(f"\n🔐 Administrator access required to configure CAN interface {interface}")
            print(f"   Command: sudo ip link set {interface} up type can bitrate {bitrate}")
            
            # Try using sudo with current credentials first
            cmd = ['sudo', '-n', 'ip', 'link', 'set', interface, 'up', 'type', 'can', 'bitrate', str(bitrate)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, f"Interface {interface} brought up successfully with sudo"
            
            # If that failed, we need password
            print("Please enter your password to configure the CAN interface:")
            
            # Use sudo with password prompt
            cmd = ['sudo', 'ip', 'link', 'set', interface, 'up', 'type', 'can', 'bitrate', str(bitrate)]
            result = subprocess.run(cmd, check=False)
            
            if result.returncode == 0:
                return True, f"Interface {interface} brought up successfully"
            else:
                return False, f"Failed to bring up {interface} - check permissions and interface name"
                
        except KeyboardInterrupt:
            return False, "Operation cancelled by user"
        except Exception as e:
            return False, f"Error with sudo: {e}"
    
    @staticmethod
    def bring_interface_down(interface: str) -> Tuple[bool, str]:
        """
        Bring CAN interface down.
        
        Args:
            interface: CAN interface name (e.g., 'can0')
            
        Returns:
            (success, message)
        """
        try:
            # Try without sudo first
            cmd = ['ip', 'link', 'set', interface, 'down']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True, f"Interface {interface} brought down successfully"
            
            # If that failed, try with sudo
            if 'operation not permitted' in result.stderr.lower():
                cmd = ['sudo', 'ip', 'link', 'set', interface, 'down']
                result = subprocess.run(cmd, check=False)
                
                if result.returncode == 0:
                    return True, f"Interface {interface} brought down successfully"
            
            return False, f"Failed to bring down {interface}: {result.stderr}"
            
        except Exception as e:
            return False, f"Error bringing down interface: {e}"
    
    @staticmethod
    def auto_setup_interface(interface: str, bitrate: int = 500000) -> Tuple[bool, str]:
        """
        Automatically set up CAN interface if needed.
        
        Args:
            interface: CAN interface name
            bitrate: Desired bitrate
            
        Returns:
            (success, status_message)
        """
        # Check current status
        is_up, state, current_bitrate = CANInterfaceManager.get_interface_status(interface)
        
        if state == "NOT_FOUND":
            return False, f"CAN interface {interface} not found. Check if hardware is connected."
        
        if is_up and current_bitrate == bitrate:
            return True, f"Interface {interface} already up at {bitrate} bps"
        
        if is_up and current_bitrate != bitrate:
            # Need to bring down and reconfigure
            print(f"Interface {interface} is up at {current_bitrate} bps, need to reconfigure to {bitrate} bps")
            success, msg = CANInterfaceManager.bring_interface_down(interface)
            if not success:
                return False, f"Failed to reconfigure: {msg}"
        
        # Bring interface up with correct bitrate
        return CANInterfaceManager.bring_interface_up(interface, bitrate)

def main():
    """Test the CAN interface manager."""
    manager = CANInterfaceManager()
    
    print("CAN Interface Manager Test")
    print("=" * 30)
    
    # List interfaces
    interfaces = manager.get_can_interfaces()
    print(f"Available CAN interfaces: {interfaces}")
    
    if interfaces:
        interface = interfaces[0]
        print(f"\nTesting with interface: {interface}")
        
        # Check status
        is_up, state, bitrate = manager.get_interface_status(interface)
        print(f"Status: {state}, Bitrate: {bitrate}")
        
        # Auto setup
        success, message = manager.auto_setup_interface(interface, 500000)
        print(f"Auto setup: {'Success' if success else 'Failed'} - {message}")

if __name__ == "__main__":
    main()