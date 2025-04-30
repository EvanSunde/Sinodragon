import json
import os
import logging

# Make sure we have a logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self.config_file = "keyboard_config.json"
        self.current_config = None
        self.default_config = self._create_default_config()
        logger.debug(f"ConfigManager initialized with config file: {self.config_file}")
        
    def _create_default_config(self):
        """Create a default configuration with all keys set to green"""
        # Total keys based on keyboard layout
        total_keys = 126  # This is the total number of keys in the layout
        logger.debug(f"Creating default config with {total_keys} green keys")
        return {
            "name": "Default Green",
            "colors": [(0, 255, 0) for _ in range(total_keys)]
        }
    
    def load_config(self, config_name=None):
        """Load a configuration by name or the last used one"""
        logger.info(f"Loading configuration, requested name: {config_name}")
        
        if os.path.exists(self.config_file):
            try:
                logger.debug(f"Reading config file: {self.config_file}")
                with open(self.config_file, 'r') as f:
                    configs = json.load(f)
                
                if config_name and config_name in configs:
                    logger.info(f"Loading requested config: {config_name}")
                    self.current_config = configs[config_name]
                elif "last_used" in configs and configs["last_used"] in configs:
                    last_config = configs["last_used"]
                    logger.info(f"Loading last used config: {last_config}")
                    self.current_config = configs[last_config]
                else:
                    # Use default if no valid config found
                    logger.info("No valid config found, using default")
                    self.current_config = self.default_config
                
                return self.current_config
            except Exception as e:
                logger.error(f"Error loading configuration: {e}", exc_info=True)
        else:
            logger.info(f"Config file {self.config_file} does not exist, using default")
        
        # Return default config if loading fails
        self.current_config = self.default_config
        return self.current_config
    
    def save_config(self, config_name, colors):
        """Save a configuration"""
        logger.info(f"Saving configuration with name: {config_name}")
        
        configs = {}
        if os.path.exists(self.config_file):
            try:
                logger.debug(f"Reading existing config file: {self.config_file}")
                with open(self.config_file, 'r') as f:
                    configs = json.load(f)
            except Exception as e:
                logger.warning(f"Could not read existing config file: {e}")
        
        # Convert tuples to lists for JSON serialization
        color_list = [list(color) for color in colors]
        logger.debug(f"Saving configuration with {len(colors)} colors")
        
        configs[config_name] = {
            "name": config_name,
            "colors": color_list
        }
        configs["last_used"] = config_name
        
        try:
            logger.debug(f"Writing config to file: {self.config_file}")
            with open(self.config_file, 'w') as f:
                json.dump(configs, f, indent=2)
            logger.info(f"Successfully saved configuration '{config_name}'")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}", exc_info=True)
            return False
    
    def get_config_list(self):
        """Get a list of all saved configurations"""
        logger.debug("Getting list of saved configurations")
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    configs = json.load(f)
                config_list = [name for name in configs.keys() if name != "last_used"]
                logger.debug(f"Found {len(config_list)} saved configurations")
                return config_list
            except Exception as e:
                logger.error(f"Error reading config file: {e}")
        else:
            logger.info(f"Config file {self.config_file} does not exist")
            
        logger.debug("Returning default config list")
        return ["Default Green"] 