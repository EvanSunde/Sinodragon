#! /usr/bin/python3
import sys
import logging
import argparse
from PyQt5.QtWidgets import QApplication

# Import the main app class from ui package
from ui.keyboard_app import KeyboardConfigApp
from features.cli import CommandLineInterface

# Configure logging with INFO level instead of DEBUG
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='keyboard_app.log',  # Also save to file
    filemode='a'  # Append to existing log
)

# Add console handler to show logs in console as well
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    # Parse specific arguments for the main app
    parser = argparse.ArgumentParser(description="Keyboard LED Configuration")
    parser.add_argument('--background', '-b', action='store_true', help='Start application in background mode')
    parser.add_argument('--no-connect', action='store_true', help='Do not automatically connect to keyboard on startup')
    
    # Only parse known args to allow CLI module to handle its own args
    args, _ = parser.parse_known_args()
    
    # Handle command line interface
    result = CommandLineInterface.handle_command_line(KeyboardConfigApp)
    
    # If command line handling requested GUI launch (returns None), launch the GUI
    if result is None:
        # Normal GUI mode
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Create the keyboard app
        keyboard_app = KeyboardConfigApp()
        
        # Set auto-connect preference
        if args.no_connect:
            keyboard_app.auto_connect = False
        
        # Show window unless background mode is requested
        if not args.background:
            keyboard_app.show()
        
        sys.exit(app.exec_())
    
    # Add explicit exit for CLI operations
    else:
        sys.exit(0)  # Exit after CLI operations complete

if __name__ == "__main__":
    logger.info("Starting Keyboard LED Configuration Application")
    main()
    logger.info("Application GUI initialized and shown") 