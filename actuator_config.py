#!/usr/bin/env python3
"""
Actuator Configuration Management

Manages actuator part numbers, gearbox numbers, and organized dump storage.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Optional, List

class ActuatorConfig:
    """Manages actuator configuration and dump organization."""
    
    def __init__(self, config_file: str = "actuator_configs.json"):
        self.config_file = config_file
        self.configs = self._load_configs()
    
    def _load_configs(self) -> Dict:
        """Load existing configurations from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_configs(self) -> None:
        """Save configurations to JSON file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.configs, f, indent=2, sort_keys=True)
    
    def add_actuator(self, electronic_part_number: str, gearbox_number: str, 
                    description: str = "", observed_can_id: str = "") -> str:
        """
        Add a new actuator configuration.
        
        Args:
            electronic_part_number: Electronic part number (e.g., "6NW-008-412")
            gearbox_number: Gearbox number (e.g., "G-222")
            description: Optional description
            observed_can_id: Observed CAN ID (e.g., "0x658")
            
        Returns:
            Configuration ID for this actuator
        """
        config_id = f"{electronic_part_number}_{gearbox_number}"
        
        self.configs[config_id] = {
            "electronic_part_number": electronic_part_number,
            "gearbox_number": gearbox_number,
            "description": description,
            "observed_can_id": observed_can_id,
            "created_date": datetime.datetime.now().isoformat(),
            "dumps": []
        }
        
        # Create directory structure
        dump_dir = self.get_dump_directory(electronic_part_number, gearbox_number)
        dump_dir.mkdir(parents=True, exist_ok=True)
        
        self._save_configs()
        return config_id
    
    def get_dump_directory(self, electronic_part_number: str, gearbox_number: str) -> Path:
        """Get the dump directory path for an actuator."""
        return Path("dumps") / electronic_part_number / gearbox_number
    
    def add_dump(self, config_id: str, dump_filename: str, notes: str = "") -> str:
        """
        Add a dump file to an actuator configuration.
        
        Args:
            config_id: Configuration ID
            dump_filename: Name of the dump file
            notes: Optional notes about this dump
            
        Returns:
            Full path to the dump file
        """
        if config_id not in self.configs:
            raise ValueError(f"Configuration {config_id} not found")
        
        config = self.configs[config_id]
        dump_dir = self.get_dump_directory(
            config["electronic_part_number"], 
            config["gearbox_number"]
        )
        
        # Generate timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_path = dump_dir / f"{timestamp}_{dump_filename}"
        
        # Add to configuration
        dump_info = {
            "filename": str(dump_path),
            "original_name": dump_filename,
            "timestamp": timestamp,
            "notes": notes,
            "created_date": datetime.datetime.now().isoformat()
        }
        
        self.configs[config_id]["dumps"].append(dump_info)
        self._save_configs()
        
        return str(dump_path)
    
    def list_actuators(self) -> List[Dict]:
        """List all configured actuators."""
        return [
            {
                "config_id": config_id,
                **config_data
            }
            for config_id, config_data in self.configs.items()
        ]
    
    def get_actuator(self, config_id: str) -> Optional[Dict]:
        """Get configuration for a specific actuator."""
        return self.configs.get(config_id)
    
    def list_dumps_for_actuator(self, config_id: str) -> List[Dict]:
        """List all dumps for a specific actuator."""
        if config_id not in self.configs:
            return []
        return self.configs[config_id]["dumps"]
    
    def find_all_dumps(self) -> List[Dict]:
        """Find all dump files across all actuators."""
        all_dumps = []
        for config_id, config in self.configs.items():
            for dump in config["dumps"]:
                all_dumps.append({
                    "config_id": config_id,
                    "electronic_part_number": config["electronic_part_number"],
                    "gearbox_number": config["gearbox_number"],
                    **dump
                })
        return all_dumps
    
    def update_actuator_can_id(self, config_id: str, can_id: str) -> None:
        """Update the observed CAN ID for an actuator."""
        if config_id in self.configs:
            self.configs[config_id]["observed_can_id"] = can_id
            self._save_configs()

def main():
    """Example usage of ActuatorConfig."""
    config = ActuatorConfig()
    
    # Add the G-222 configuration
    config_id = config.add_actuator(
        electronic_part_number="6NW-008-412",
        gearbox_number="G-222", 
        description="Primary test actuator - verified working",
        observed_can_id="0x658"
    )
    
    print(f"Added actuator configuration: {config_id}")
    print(f"Dump directory: {config.get_dump_directory('6NW-008-412', 'G-222')}")
    
    # List all actuators
    print("\nConfigured actuators:")
    for actuator in config.list_actuators():
        print(f"  {actuator['config_id']}: {actuator['description']}")

if __name__ == "__main__":
    main()