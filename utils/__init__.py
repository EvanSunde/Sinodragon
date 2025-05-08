"""
Utility functions for the keyboard application.
"""

import logging

# Configure application-wide logging
def setup_logging(filename=None, console_level=logging.INFO, file_level=logging.INFO):
    """Set up logging configuration for the application"""
    # Configure base logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all logs at the root level
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
    
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(console_formatter)
    root_logger.addHandler(console)
    
    # Add file handler if filename is provided
    if filename:
        file_handler = logging.FileHandler(filename, mode='a')
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
    return root_logger 