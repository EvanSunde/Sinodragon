import json
import os
import logging
import struct
import io

# Change logging level to INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        # Define possible config paths
        home_dir = os.path.expanduser("~")
        self.global_config_dir = os.path.join(home_dir, ".config", "sinodragon")
        self.local_config_dir = "./config"
        
        # Ensure config directory exists
        self._ensure_config_dir()
        
        # Binary config format uses .kbc extension (Keyboard Config)
        self.config_dir_bin = os.path.join(self.config_dir, "configs")
        os.makedirs(self.config_dir_bin, exist_ok=True)
        
        # Keep list of configs in a small index file
        self.config_index = os.path.join(self.config_dir, "config_index.bin")
        self.config_list = []
        self.last_used = None
        self.default_config_name = None  # Store the name of the default configuration
        
        # Load the config index
        self._load_config_index()
        
        self.current_config = None
        self.default_config = self._create_default_config()
        
        # Magic number for binary files
        self.MAGIC = b'KBCF'  # Keyboard Config Format
        self.VERSION = 1
        
    def _ensure_config_dir(self):
        """Ensure that configuration directory exists"""
        # Try global config directory first
        try:
            os.makedirs(self.global_config_dir, exist_ok=True)
            self.config_dir = self.global_config_dir
            logger.info(f"Using global config dir: {self.global_config_dir}")
        except (PermissionError, OSError):
            # Fall back to local config if global fails
            try:
                os.makedirs(self.local_config_dir, exist_ok=True)
                self.config_dir = self.local_config_dir
                logger.info(f"Using local config dir: {self.local_config_dir}")
            except (PermissionError, OSError) as e:
                logger.error(f"Failed to create config dir: {e}")
                self.config_dir = "."  # Fallback to current directory
                
    def _load_config_index(self):
        """Load or initialize the config index"""
        if os.path.exists(self.config_index):
            try:
                with open(self.config_index, 'rb') as f:
                    # Format: [count][last_used_len][last_used][default_len][default][name1_len][name1]...
                    count = struct.unpack('B', f.read(1))[0]
                    
                    # Read last used config name
                    last_used_len = struct.unpack('B', f.read(1))[0]
                    self.last_used = f.read(last_used_len).decode('utf-8')
                    
                    # Read default config name
                    default_len = struct.unpack('B', f.read(1))[0]
                    if default_len > 0:
                        self.default_config_name = f.read(default_len).decode('utf-8')
                    else:
                        self.default_config_name = None
                        
                    # Read config names
                    self.config_list = []
                    for _ in range(count):
                        name_len = struct.unpack('B', f.read(1))[0]
                        name = f.read(name_len).decode('utf-8')
                        self.config_list.append(name)
            except Exception as e:
                logger.error(f"Error loading config index: {e}")
                self._initialize_config_index()
        else:
            self._initialize_config_index()
    
    def _initialize_config_index(self):
        """Create initial config index with default config"""
        self.config_list = ["Default Green"]
        self.last_used = "Default Green"
        self.default_config_name = "Default Green"
        self._save_config_index()
    
    def _save_config_index(self):
        """Save the config index"""
        try:
            with open(self.config_index, 'wb') as f:
                # Write number of configs
                f.write(struct.pack('B', len(self.config_list)))
                
                # Write last used config name
                last_used = self.last_used or "Default Green"
                f.write(struct.pack('B', len(last_used)))
                f.write(last_used.encode('utf-8'))
                
                # Write default config name
                default_name = self.default_config_name or ""
                f.write(struct.pack('B', len(default_name)))
                if default_name:
                    f.write(default_name.encode('utf-8'))
                
                # Write config names
                for name in self.config_list:
                    f.write(struct.pack('B', len(name)))
                    f.write(name.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Error saving config index: {e}")
            return False
    
    def _get_config_path(self, config_name):
        """Get the path to a config file"""
        if not config_name:
            config_name = "Default Green"
        
        # Remove any illegal characters
        safe_name = "".join(c for c in config_name if c.isalnum() or c in " -_")
        return os.path.join(self.config_dir_bin, f"{safe_name}.kbc")
    
    def _create_default_config(self):
        """Create default configuration with all keys set to green"""
        total_keys = 126  # Total number of keys in the layout
        default_color = (0, 255, 0)  # Green
        
        # Create with binary format in mind - dict with default color and specific keys
        return {
            "name": "Default Green",
            "default_color": default_color,
            "keys": {i: default_color for i in range(total_keys)}
        }
    
    def load_config(self, config_name=None):
        """Load a configuration by name, the last used one, or the default"""
        # If no name specified, use last used or default
        if not config_name:
            config_name = self.last_used or self.default_config_name or "Default Green"
        
        # Config path
        config_path = self._get_config_path(config_name)
        
        # Check if binary format exists
        if os.path.exists(config_path):
            try:
                with open(config_path, 'rb') as f:
                    # Read and verify header
                    magic = f.read(4)
                    if magic != self.MAGIC:
                        raise ValueError(f"Invalid file format for {config_path}")
                    
                    version = struct.unpack('B', f.read(1))[0]
                    if version != self.VERSION:
                        raise ValueError(f"Unsupported version {version}")
                    
                    # Read name length and name
                    name_len = struct.unpack('B', f.read(1))[0]
                    name = f.read(name_len).decode('utf-8')
                    
                    # Read default color
                    dr, dg, db = struct.unpack('BBB', f.read(3))
                    default_color = (dr, dg, db)
                    
                    # Read key count
                    key_count = struct.unpack('<H', f.read(2))[0]
                    
                    # Create config with default color
                    config = {
                        "name": name,
                        "default_color": default_color,
                        "keys": {}
                    }
                    
                    # Apply default color to all keys
                    for i in range(126):
                        config["keys"][i] = default_color
                    
                    # Read key-color pairs
                    for _ in range(key_count):
                        key_idx = struct.unpack('<H', f.read(2))[0]
                        r, g, b = struct.unpack('BBB', f.read(3))
                        config["keys"][key_idx] = (r, g, b)
                    
                    self.current_config = config
                    self.last_used = name
                    self._save_config_index()
                    return self._convert_to_legacy_format(config)
            
            except Exception as e:
                logger.error(f"Error loading binary config: {e}")
                # Fall back to default config if specified
                if self.default_config_name and config_name != self.default_config_name:
                    logger.info(f"Falling back to default config: {self.default_config_name}")
                    return self.load_config(self.default_config_name)
        
        # Try loading JSON format (legacy)
        try:
            return self._load_legacy_config(config_name)
        except Exception as e:
            logger.error(f"Error loading legacy config: {e}")
        
        # If all fails, use default
        self.current_config = self.default_config
        return self._convert_to_legacy_format(self.default_config)
    
    def _load_legacy_config(self, config_name):
        """Load a configuration from the legacy JSON format"""
        legacy_path = os.path.join(self.config_dir, "keyboard_config.json")
        
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, 'r') as f:
                    configs = json.load(f)
                
                if config_name and config_name in configs:
                    legacy_config = configs[config_name]
                    return legacy_config
                elif "last_used" in configs and configs["last_used"] in configs:
                    last_config = configs["last_used"]
                    return configs[last_config]
            except Exception as e:
                logger.error(f"Error loading legacy config: {e}")
        
        return self._convert_to_legacy_format(self.default_config)
    
    def _convert_to_legacy_format(self, efficient_config):
        """Convert efficient format to legacy format for backward compatibility"""
        legacy_config = {
            "name": efficient_config["name"],
            "colors": []
        }
        
        # Convert efficient format to array format
        for i in range(126):
            if i in efficient_config["keys"]:
                legacy_config["colors"].append(list(efficient_config["keys"][i]))
        else:
                legacy_config["colors"].append(list(efficient_config["default_color"]))
        
        return legacy_config
    
    def save_config(self, config_name, colors):
        """Save a configuration in efficient binary format"""
        if not config_name:
            return False
        
        # Convert from legacy array format to efficient format
        default_color = (0, 0, 0)  # Default to black
        keys = {}
        
        # Find most common color to use as default (usually black)
        color_counts = {}
        for i, color in enumerate(colors):
            color_tuple = tuple(color) if isinstance(color, list) else color
            if color_tuple not in color_counts:
                color_counts[color_tuple] = 0
            color_counts[color_tuple] += 1
        
        # Find most common color
        most_common = max(color_counts.items(), key=lambda x: x[1])
        default_color = most_common[0]
        
        # Only store non-default colors
        for i, color in enumerate(colors):
            color_tuple = tuple(color) if isinstance(color, list) else color
            if color_tuple != default_color:
                keys[i] = color_tuple
        
        # Create efficient config
        efficient_config = {
            "name": config_name,
            "default_color": default_color,
            "keys": keys
        }
        
        # Save in binary format
        config_path = self._get_config_path(config_name)
        try:
            with open(config_path, 'wb') as f:
                # Write header
                f.write(self.MAGIC)  # Magic number
                f.write(struct.pack('B', self.VERSION))  # Version
                
                # Write name
                f.write(struct.pack('B', len(config_name)))  # Name length
                f.write(config_name.encode('utf-8'))  # Name
                
                # Write default color
                f.write(struct.pack('BBB', *default_color))  # Default RGB
                
                # Write key count
                f.write(struct.pack('<H', len(keys)))  # 2-byte count for up to 65,535 keys
                
                # Write key-color pairs
                for key_idx, color in keys.items():
                    f.write(struct.pack('<H', key_idx))  # 2-byte key index
                    f.write(struct.pack('BBB', *color))  # RGB values
            
            # Update config index
            if config_name not in self.config_list:
                self.config_list.append(config_name)
            self.last_used = config_name
            self._save_config_index()
            
            # Also save in legacy format for backward compatibility
            self._save_legacy_config(config_name, colors)
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving binary config: {e}")
            return False
    
    def _save_legacy_config(self, config_name, colors):
        """Save in legacy JSON format for backward compatibility"""
        legacy_path = os.path.join(self.config_dir, "keyboard_config.json")
        
        configs = {}
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, 'r') as f:
                    configs = json.load(f)
            except Exception:
                pass
        
        # Convert tuples to lists for JSON
        color_list = [list(color) if isinstance(color, tuple) else color for color in colors]
        
        configs[config_name] = {
            "name": config_name,
            "colors": color_list
        }
        configs["last_used"] = config_name
        
        try:
            with open(legacy_path, 'w') as f:
                json.dump(configs, f)
            return True
        except Exception as e:
            logger.error(f"Error saving legacy config: {e}")
            return False
    
    def get_config_list(self):
        """Get a list of all saved configurations"""
        return self.config_list

    def get_config_in_memory_map(self, config_name=None):
        """Get a config as a memory-mapped array for direct access"""
        config = self.load_config(config_name)
        
        # Create a byte array in memory
        buffer = bytearray(126 * 3)  # 126 keys × 3 bytes (RGB)
        
        # Fill the buffer with color values
        for i, color in enumerate(config["colors"]):
            if i < 126:
                # Fix: Ensure RGB values are valid integers between 0-255
                r = max(0, min(255, int(color[0])))
                g = max(0, min(255, int(color[1])))
                b = max(0, min(255, int(color[2])))
                
                buffer[i*3] = r     # R
                buffer[i*3+1] = g   # G
                buffer[i*3+2] = b   # B
        
        return memoryview(buffer)

    def set_default_config(self, config_name):
        """Set a configuration as the default"""
        if config_name not in self.config_list:
            logger.error(f"Cannot set {config_name} as default: configuration does not exist")
            return False
        
        self.default_config_name = config_name
        logger.info(f"Set {config_name} as default configuration")
        return self._save_config_index()

    def get_default_config_name(self):
        """Get the name of the default configuration"""
        return self.default_config_name

    def delete_config(self, config_name):
        """Delete a configuration"""
        if config_name not in self.config_list:
            logger.error(f"Cannot delete {config_name}: configuration does not exist")
            return False
        
        # Don't delete the last configuration
        if len(self.config_list) <= 1:
            logger.error("Cannot delete the only remaining configuration")
            return False
        
        # Remove from config list
        self.config_list.remove(config_name)
        
        # Update last_used if needed
        if self.last_used == config_name:
            self.last_used = self.config_list[0]
        
        # Update default if needed
        if self.default_config_name == config_name:
            self.default_config_name = self.config_list[0]
        
        # Delete the file
        config_path = self._get_config_path(config_name)
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            
            # Also remove from legacy format if it exists
            self._remove_from_legacy_config(config_name)
            
            # Save updated index
            self._save_config_index()
            
            logger.info(f"Deleted configuration: {config_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting configuration {config_name}: {e}")
            return False

    def _remove_from_legacy_config(self, config_name):
        """Remove a configuration from the legacy JSON format"""
        legacy_path = os.path.join(self.config_dir, "keyboard_config.json")
        
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, 'r') as f:
                    configs = json.load(f)
                
                if config_name in configs:
                    del configs[config_name]
                    
                    # Update last_used if needed
                    if configs.get("last_used") == config_name:
                        # Find another config to use
                        for key in configs:
                            if key != "last_used":
                                configs["last_used"] = key
                                break
                
                with open(legacy_path, 'w') as f:
                    json.dump(configs, f)
                
            except Exception as e:
                logger.error(f"Error removing from legacy config: {e}") 