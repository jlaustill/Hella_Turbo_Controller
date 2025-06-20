#!/usr/bin/python3
"""
Hella Turbo Controller Programming Interface

This module provides a Python interface for programming the Hella Universal
turbo actuator I using CAN bus communication.
"""

import can
import time
import datetime
import sys
import logging
from typing import Optional, List, Tuple

# CAN Message IDs
REQUEST_ID = 0x3F0
MEMORY_RESPONSE_ID = 0x3E8
POSITION_RESPONSE_ID = 0x658
ACK_RESPONSE_ID = 0x3EB

# Message constants
REQUEST_MSG = bytearray([0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
MEMORY_SIZE = 128
DEFAULT_TIMEOUT = 1.0
MESSAGE_DELAY = 0.02

# Position calculation constants
HARDCODED_Z_VALUE = 99  # TODO: Implement proper calculation

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HellaProgError(Exception):
    """Custom exception for Hella programming errors."""
    pass


class HellaProg:
    """Interface for programming Hella Universal turbo actuator I."""
    
    def __init__(self, channel: str, interface: str, bitrate: int = 500000, tty_baudrate: int = 128000):
        """
        Initialize the Hella programmer.
        
        Args:
            channel: CAN channel (e.g., 'can0', '/dev/ttyACM0')
            interface: CAN interface type ('socketcan', 'slcan')
            bitrate: CAN bus bitrate (default: 500000)
            tty_baudrate: TTY baudrate for SLCAN (default: 128000)
        """
        try:
            self.interface = can.interface.Bus(
                channel=channel,
                interface=interface,
                bitrate=bitrate,
                ttyBaudrate=tty_baudrate
            )
            self.msg_req = can.Message(
                is_extended_id=False,
                arbitration_id=REQUEST_ID,
                data=REQUEST_MSG
            )
            logger.info(f"Initialized CAN interface: {interface} on {channel}")
        except Exception as e:
            raise HellaProgError(f"Failed to initialize CAN interface: {e}")
    
    def _wait_for_ack(self, timeout: float = DEFAULT_TIMEOUT) -> Optional[can.Message]:
        """Wait for acknowledgment message."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            answer = self.interface.recv(0.1)
            if answer is not None and answer.arbitration_id == ACK_RESPONSE_ID:
                if len(answer.data) >= 8 and answer.data[7] == 0x53:
                    return answer
        return None
    
    def _send_request_and_wait(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Send request message and wait for acknowledgment."""
        self.interface.send(self.msg_req)
        if not self._wait_for_ack(timeout):
            raise HellaProgError("No acknowledgment received for request")
    
    def readmemory(self, filename: Optional[str] = None) -> str:
        """
        Read the complete memory from the actuator and save to a binary file.
        
        Args:
            filename: Optional filename for the binary dump. If None, generates timestamp-based name.
            
        Returns:
            The filename of the saved binary dump.
            
        Raises:
            HellaProgError: If memory reading fails.
        """
        if filename is None:
            timestamp = datetime.datetime.now()
            filename = timestamp.strftime('%Y%m%d-%H%M%S.bin')
        
        logger.info(f"Reading memory to file: {filename}")
        
        try:
            self._send_request_and_wait()
            
            with open(filename, 'wb') as fn:
                for n in range(MEMORY_SIZE):
                    # Send memory read command for address n
                    msg = can.Message(
                        is_extended_id=False,
                        arbitration_id=REQUEST_ID,
                        data=bytearray([0x31, 0x0C, n, 0x00, 0x00, 0x00, 0x00, 0x00])
                    )
                    self.interface.send(msg)
                    
                    # Wait for memory response
                    start_time = time.time()
                    while time.time() - start_time < DEFAULT_TIMEOUT:
                        answer = self.interface.recv(0.1)
                        if answer is not None and answer.arbitration_id == MEMORY_RESPONSE_ID:
                            if len(answer.data) > 0:
                                logger.debug(f'Memory[{n:02X}]: {answer.data[0]:02X}')
                                fn.write(bytes([answer.data[0]]))
                                break
                        elif answer is not None:
                            # Consume other messages
                            continue
                    else:
                        raise HellaProgError(f"No memory response for address {n:02X}")
            
            logger.info(f"Memory dump completed: {filename}")
            return filename
            
        except Exception as e:
            raise HellaProgError(f"Memory read failed: {e}")
    
    def _read_position_value(self, addresses: List[int]) -> int:
        """
        Read position values from specified memory addresses.
        
        Args:
            addresses: List of memory addresses to read (typically 2 bytes for 16-bit value)
            
        Returns:
            Combined 16-bit position value
        """
        self._send_request_and_wait()
        
        values = []
        for addr in addresses:
            msg = can.Message(
                is_extended_id=False,
                arbitration_id=REQUEST_ID,
                data=bytearray([0x31, 0x0C, addr, 0x00, 0x00, 0x00, 0x00, 0x00])
            )
            self.interface.send(msg)
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < DEFAULT_TIMEOUT:
                answer = self.interface.recv(0.1)
                if answer is not None and answer.arbitration_id == MEMORY_RESPONSE_ID:
                    if len(answer.data) > 0:
                        values.append(answer.data[0])
                        break
            else:
                raise HellaProgError(f"No response for address {addr:02X}")
        
        # Combine bytes into 16-bit value (big-endian)
        if len(values) >= 2:
            return (values[0] << 8) | values[1]
        return values[0] if values else 0
    
    def readmax(self) -> int:
        """
        Read the maximum position value from the actuator.
        
        Returns:
            Maximum position value (16-bit)
            
        Raises:
            HellaProgError: If reading fails.
        """
        logger.info("Reading maximum position")
        try:
            return self._read_position_value([5, 6])
        except Exception as e:
            raise HellaProgError(f"Failed to read max position: {e}")

    def readmin(self) -> int:
        """
        Read the minimum position value from the actuator.
        
        Returns:
            Minimum position value (16-bit)
            
        Raises:
            HellaProgError: If reading fails.
        """
        logger.info("Reading minimum position")
        try:
            return self._read_position_value([3, 4])
        except Exception as e:
            raise HellaProgError(f"Failed to read min position: {e}")

    def readminmax(self) -> Tuple[int, int]:
        """
        Read both minimum and maximum position values from the actuator.
        
        Returns:
            Tuple of (min_position, max_position)
            
        Raises:
            HellaProgError: If reading fails.
        """
        logger.info("Reading min/max positions")
        try:
            self._send_request_and_wait()
            
            # Read min (addresses 3,4), max (addresses 5,6), and range (address 0x22)
            addresses = [3, 4, 5, 6, 0x22]
            values = []
            
            for addr in addresses:
                msg = can.Message(
                    is_extended_id=False,
                    arbitration_id=REQUEST_ID,
                    data=bytearray([0x31, 0x0C, addr, 0x00, 0x00, 0x00, 0x00, 0x00])
                )
                self.interface.send(msg)
                
                # Wait for response
                start_time = time.time()
                while time.time() - start_time < DEFAULT_TIMEOUT:
                    answer = self.interface.recv(0.1)
                    if answer is not None and answer.arbitration_id == MEMORY_RESPONSE_ID:
                        if len(answer.data) > 0:
                            values.append(answer.data[0])
                            break
                else:
                    raise HellaProgError(f"No response for address {addr:02X}")
            
            if len(values) >= 5:
                min_pos = (values[0] << 8) | values[1]
                max_pos = (values[2] << 8) | values[3]
                # Alternative calculation using range: max_pos = min_pos + (values[4] * 4)
                return (min_pos, max_pos)
            else:
                raise HellaProgError("Insufficient data received")
                
        except Exception as e:
            raise HellaProgError(f"Failed to read min/max positions: {e}")

    def recv(self, timeout: float = DEFAULT_TIMEOUT) -> Optional[can.Message]:
        """
        Receive a CAN message with optional logging.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Received CAN message or None if timeout
        """
        answer = self.interface.recv(timeout)
        if answer is not None:
            logger.debug(f"Received message ID: {answer.arbitration_id:03X}")
        return answer

    def set_max(self, pos):
        x = (int(pos)>>8)&0xFF
        y = (int(pos)&0xFF)
        z = 99#255 - int((int(pos)/1024)*255)
        print(('%X ')*3%(x,y,z))
        
        msg = can.Message(extended_id=False,arbitration_id=0x3F0,data=bytearray([0x31,0x0C,0x00,0x00,0x00,0x00,0x00,0x00]))
        msgs = [
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, x, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, y, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x22, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, z, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x23, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ]
        for item in msgs:
            msg.data = item
            self.interface.send(msg)
            time.sleep(0.02)
        answer = self.interface.recv(1)
        while answer is not None:
            answer = self.interface.recv(1)
    
    def set_min(self, pos):
        x = (int(pos)>>8)&0xFF
        y = (int(pos)&0xFF)
        z = 99#255 - int((int(pos)/1024)*255)
        msg = can.Message(extended_id=False,arbitration_id=0x3F0,data=bytearray([0x31,0x0C,0x00,0x00,0x00,0x00,0x00,0x00]))
        msgs = [
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, x, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, y, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x22, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, z, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x23, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ]
        for item in msgs:
            msg.data = item
            self.interface.send(msg)
            time.sleep(0.02)
        answer = self.interface.recv(1)
        while answer is not None:
            answer = self.interface.recv(1)
    
    def set_minmax(self, minpos, maxpos):
        x = (int(minpos)>>8)&0xFF
        y = (int(minpos)&0xFF)
        z = int((maxpos-minpos)/4)
        msg = can.Message(extended_id=False,arbitration_id=0x3F0,data=bytearray([0x31,0x0C,0x00,0x00,0x00,0x00,0x00,0x00]))
        msgs = [
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, x, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, y, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x22, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, z, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x0C, 0x23, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x57, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
            bytearray([0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ]
        for item in msgs:
            msg.data = item
            self.interface.send(msg)
            time.sleep(0.02)
        answer = self.interface.recv(1)
        while answer is not None:
            answer = self.interface.recv(1)

    def find_end_positions(self):
        msg = can.Message(extended_id=False,arbitration_id=0x3F0,data=bytearray([0x31,0x0C,0x00,0x00,0x00,0x00,0x00,0x00]))
        msgs1 = [
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,1,93,0,0,0,0,0]),
            bytearray([87,0,0,5,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,1,99,0,0,0,0,0]),
            bytearray([87,0,0,40,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,128,0,0,0,0,0]),
            bytearray([87,0,0,1,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,1,97,0,0,0,0,0]),
            bytearray([87,0,0,1,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([68,0,0,0,0,0,0,0]),
            ]
        msgs2 = [
            bytearray([49,1,97,0,0,0,0,0]),
            bytearray([87,0,0,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,128,0,0,0,0,0]),
            bytearray([87,0,0,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,1,97,0,0,0,0,0]),
            bytearray([87,0,0,1,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([68,0,0,0,0,0,0,0]),
            ]
        msgs3 = [
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,1,97,0,0,0,0,0]),
            bytearray([87,0,0,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([49,1,93,0,0,0,0,0]),
            bytearray([87,0,0,2,0,0,0,0]),
            bytearray([49,0,148,0,0,0,0,0]),
            bytearray([68,0,0,0,0,0,0,0]),
            ]
        self.interface.send(self.msg_req)
        time.sleep(1)
        for item in msgs1:
            msg.data = item
            self.interface.send(msg)
            time.sleep(0.02)
        time.sleep(2)
        self.interface.send(self.msg_req)
        answer = self.interface.recv(1)
        while answer is not None:
            if answer.arbitration_id == POSITION_RESPONSE_ID:
                print('%02X%02X'%(answer.data[5],answer.data[6]))
            answer = self.interface.recv(1)
        for item in msgs2:
            msg.data = item
            self.interface.send(msg)
            time.sleep(0.02)
        time.sleep(2)
        self.interface.send(self.msg_req)
        answer = self.interface.recv(1)
        while answer is not None:
            if answer.arbitration_id == POSITION_RESPONSE_ID:
                print('%02X%02X'%(answer.data[5],answer.data[6]))
            answer = self.interface.recv(1)
        for item in msgs3:
            msg.data = item
            self.interface.send(msg)
            time.sleep(0.02)
        self.interface.send(self.msg_req)
        time.sleep(1)
    
    def readCurrentPosition(self):
        """
        Read the current actuator position using correct G-222 format.
        
        Based on reverse engineering:
        - Position: bytes 2-3 (big endian)
        - Range: 688 (0% open) to 212 (100% open) - inverted scale
        
        Returns:
            Current position value (16-bit) or None if no response
        """
        # Just listen for existing position messages (actuator sends them automatically)
        start_time = time.time()
        while time.time() - start_time < DEFAULT_TIMEOUT:
            answer = self.interface.recv(0.1)
            if answer is not None and answer.arbitration_id == POSITION_RESPONSE_ID:
                if len(answer.data) >= 4:
                    # CORRECT format: position is in bytes 2-3
                    position = (answer.data[2] << 8) | answer.data[3]
                    status = answer.data[0] if len(answer.data) > 0 else 0
                    temp = answer.data[5] if len(answer.data) > 5 else 0
                    motor_load = ((answer.data[6] << 8) | answer.data[7]) if len(answer.data) >= 8 else 0
                    
                    # Convert to percentage (688=0%, 212=100%)
                    if position <= 688 and position >= 212:
                        percentage = ((688 - position) * 100) // (688 - 212)
                    else:
                        percentage = -1  # Out of range
                    
                    print(f'Pos: {position:04X} ({percentage}%) Status: {status:02X} Temp: {temp}°C Load: {motor_load}')
                    return position
        return None
    
    def write_memory_byte(self, address: int, value: int) -> None:
        """
        Write a single byte to actuator memory.
        
        ⚠️ DANGER: Writing to wrong addresses can permanently brick your actuator!
        Always backup memory before making changes.
        
        Args:
            address: Memory address (0x00 to 0x7F)
            value: Byte value to write (0x00 to 0xFF)
            
        Raises:
            HellaProgError: If writing fails or parameters are invalid
        """
        # Validate inputs
        if not (0 <= address <= 0x7F):
            raise HellaProgError(f"Invalid address 0x{address:02X}. Must be 0x00-0x7F")
        if not (0 <= value <= 0xFF):
            raise HellaProgError(f"Invalid value 0x{value:02X}. Must be 0x00-0xFF")
        
        # Define dangerous addresses that should never be modified
        DANGEROUS_ADDRESSES = {
            0x09, 0x0A,  # Command CAN ID
            0x24, 0x25,  # Request CAN ID  
            0x27, 0x28,  # Response CAN ID
            0x29,        # Control Mode Config
            0x41,        # Interface Config
            0x10,        # Unknown critical function
        }
        
        if address in DANGEROUS_ADDRESSES:
            logger.warning(f"⚠️  Address 0x{address:02X} is dangerous to modify!")
            logger.warning("This could permanently brick your actuator.")
        
        logger.info(f"Writing 0x{value:02X} to address 0x{address:02X}")
        
        try:
            # Send initial request
            self._send_request_and_wait()
            
            # Memory write sequence based on set_max() pattern
            msg = can.Message(
                extended_id=False,
                arbitration_id=REQUEST_ID,
                data=bytearray([0x31, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            )
            
            # Write sequence: setup, target address, write value, commit
            msgs = [
                # Setup sequence
                bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x57, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x57, 0x00, 0x00, 0x2D, 0x00, 0x00, 0x00, 0x00]),
                
                # Set target address  
                bytearray([0x31, 0x0C, address, 0x00, 0x00, 0x00, 0x00, 0x00]),
                
                # Write value
                bytearray([0x57, 0x00, 0x00, value, 0x00, 0x00, 0x00, 0x00]),
                
                # Commit sequence
                bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x57, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x57, 0x00, 0x00, 0x8D, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x31, 0x01, 0x5D, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x57, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x31, 0x00, 0x94, 0x00, 0x00, 0x00, 0x00, 0x00]),
                bytearray([0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            ]
            
            # Send all messages with delays
            for item in msgs:
                msg.data = item
                self.interface.send(msg)
                time.sleep(MESSAGE_DELAY)
            
            # Wait for acknowledgment and clear buffer
            answer = self.interface.recv(DEFAULT_TIMEOUT)
            while answer is not None:
                answer = self.interface.recv(0.1)
                
            logger.info(f"Successfully wrote 0x{value:02X} to address 0x{address:02X}")
            
        except Exception as e:
            raise HellaProgError(f"Failed to write memory at 0x{address:02X}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown()
    
    def shutdown(self) -> None:
        """
        Properly shutdown the CAN interface.
        """
        try:
            if hasattr(self, 'interface') and self.interface:
                self.interface.shutdown()
                logger.info("CAN interface shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """
    Example usage of the HellaProg class.
    """
    try:
        # Use context manager for proper cleanup
        with HellaProg('can0', 'socketcan') as hp:
            logger.info("Connected to Hella actuator")
            
            # Example operations (uncomment as needed)
            
            # Read memory dump
            filename = hp.readmemory()
            logger.info(f"Memory dumped to: {filename}")
            
            # Read current positions
            try:
                min_pos = hp.readmin()
                max_pos = hp.readmax()
                logger.info(f"Current min/max: {min_pos:04X}/{max_pos:04X}")
            except HellaProgError as e:
                logger.error(f"Failed to read positions: {e}")
            
            # Example position setting (uncomment to use)
            # hp.set_max(0x0220)
            # hp.set_min(0x0113)
            
            # Automatic calibration (uncomment to use)
            # try:
            #     min_pos, max_pos = hp.find_end_positions()
            #     logger.info(f"Calibrated positions: {min_pos:04X}-{max_pos:04X}")
            # except HellaProgError as e:
            #     logger.error(f"Calibration failed: {e}")
            
    except HellaProgError as e:
        logger.error(f"Hella programming error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# vim: et:sw=4:ts=4:smarttab:foldmethod=indent:si
